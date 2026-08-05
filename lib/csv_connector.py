"""Chapitre 15 — un connecteur maison, en une centaine de lignes.

OpenMetadata sait parler à une centaine de systèmes. Il en restera toujours
un qui manque : un entrepôt interne, un vieux mainframe, un dépôt de fichiers
avec ses conventions maison. Le « Custom Database Connector » est la porte
de sortie : vous écrivez une classe Python, OpenMetadata l'exécute comme
n'importe quel connecteur officiel.

Celui-ci catalogue un dossier de fichiers CSV :
    dossier/           -> une base de données
      ventes/          -> un schéma
        exports.csv    -> une table, dont les colonnes viennent de l'en-tête

Un connecteur est un générateur. Sa seule obligation est de produire, dans
l'ordre, des requêtes de création d'entités — le reste de la chaîne
(déduplication, appels API, gestion d'erreurs) est fourni par le framework.
L'ordre compte : on ne peut pas créer un schéma avant sa base.
"""

from __future__ import annotations

import csv
import traceback
from pathlib import Path
from typing import Any, Iterable, Optional

from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import (
    CreateDatabaseSchemaRequest,
)
from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.api.services.createDatabaseService import (
    CreateDatabaseServiceRequest,
)
from metadata.generated.schema.entity.data.table import Column, DataType
from metadata.generated.schema.entity.services.databaseService import (
    DatabaseService,
    DatabaseServiceType,
)
from metadata.generated.schema.entity.services.ingestionPipelines.status import (
    StackTraceError,
)
from metadata.generated.schema.metadataIngestion.workflow import (
    Source as WorkflowSource,
)
from metadata.ingestion.api.common import Entity
from metadata.ingestion.api.models import Either
from metadata.ingestion.api.steps import InvalidSourceException, Source
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.utils.logger import ingestion_logger

logger = ingestion_logger()

# Devine le type OpenMetadata à partir des valeurs lues. Volontairement
# rudimentaire : un vrai connecteur échantillonnerait plus de lignes et
# gérerait les dates. C'est l'exercice de fin de chapitre.
def deviner_type(valeurs: list[str]) -> DataType:
    echantillon = [v for v in valeurs if v not in ("", None)][:20]
    if not echantillon:
        return DataType.STRING
    if all(v.lstrip("-").isdigit() for v in echantillon):
        return DataType.INT
    try:
        for v in echantillon:
            float(v)
        return DataType.DOUBLE
    except ValueError:
        return DataType.STRING


class CsvFolderSource(Source):
    """Catalogue un dossier de CSV comme s'il s'agissait d'une base."""

    def __init__(self, config: WorkflowSource, metadata: OpenMetadata):
        super().__init__()
        self.config = config
        self.metadata = metadata
        self.service_name = config.serviceName

        # Les paramètres libres passent par connectionOptions dans le YAML.
        options = config.serviceConnection.root.config.connectionOptions
        options = options.root if options else {}
        self.racine = Path(str(options.get("directory", "/omlab/donnees_csv")))
        self.nom_base = str(options.get("databaseName", "fichiers"))

    @classmethod
    def create(
        cls,
        config_dict: dict,
        metadata: OpenMetadata,
        pipeline_name: Optional[str] = None,
    ) -> "CsvFolderSource":
        # Le framework nous passe le YAML brut : on le revalide en objet typé.
        config: WorkflowSource = WorkflowSource.model_validate(config_dict)
        connection = config.serviceConnection.root.config
        if not hasattr(connection, "sourcePythonClass"):
            raise InvalidSourceException(
                "Ce connecteur attend une serviceConnection de type CustomDatabase."
            )
        return cls(config, metadata)

    def prepare(self) -> None:
        if not self.racine.is_dir():
            raise InvalidSourceException(f"Dossier introuvable : {self.racine}")

        # Les connecteurs officiels s'appuient sur une mécanique interne qui
        # crée le service à leur place. Un connecteur maison n'en bénéficie
        # PAS : sans ces quelques lignes, le workflow échoue à la toute fin
        # sur « databaseService instance for ... not found », alors même que
        # le résumé affiche 100 % de succès. Symptôme déroutant, cause banale.
        service = self.metadata.get_by_name(
            entity=DatabaseService, fqn=self.service_name
        )
        if service is None:
            self.metadata.create_or_update(
                CreateDatabaseServiceRequest(
                    name=self.service_name,
                    serviceType=DatabaseServiceType.CustomDatabase,
                    connection=self.config.serviceConnection.root,
                )
            )
            logger.info(f"Service {self.service_name} créé.")

    def test_connection(self) -> None:
        # Appelé par le bouton « Test Connection » de l'UI. Ici, il suffit
        # de vérifier qu'on sait lire le dossier.
        self.prepare()

    def _iter(self, *args: Any, **kwargs: Any) -> Iterable[Either[Entity]]:
        # 1. La base
        yield Either(
            right=CreateDatabaseRequest(
                name=self.nom_base,
                service=self.service_name,
                description=f"Fichiers CSV du dossier {self.racine}",
            )
        )

        database_fqn = f"{self.service_name}.{self.nom_base}"

        # 2. Un schéma par sous-dossier
        for dossier in sorted(p for p in self.racine.iterdir() if p.is_dir()):
            yield Either(
                right=CreateDatabaseSchemaRequest(
                    name=dossier.name,
                    database=database_fqn,
                )
            )
            schema_fqn = f"{database_fqn}.{dossier.name}"

            # 3. Une table par fichier
            for fichier in sorted(dossier.glob("*.csv")):
                try:
                    yield Either(right=self._table(fichier, schema_fqn))
                except Exception as exc:  # on isole les fichiers illisibles
                    # Either(left=...) signale une erreur SANS arrêter le
                    # workflow : les autres fichiers seront traités.
                    yield Either(
                        left=StackTraceError(
                            name=fichier.name,
                            error=f"Lecture impossible de {fichier}: {exc}",
                            stackTrace=traceback.format_exc(),
                        )
                    )

    def _table(self, fichier: Path, schema_fqn: str) -> CreateTableRequest:
        with fichier.open(newline="", encoding="utf-8") as handle:
            lecteur = csv.reader(handle)
            entetes = next(lecteur)
            lignes = [row for _, row in zip(range(50), lecteur)]

        colonnes = [
            Column(
                name=entete.strip(),
                dataType=deviner_type([row[i] for row in lignes if i < len(row)]),
            )
            for i, entete in enumerate(entetes)
        ]

        return CreateTableRequest(
            name=fichier.stem,
            databaseSchema=schema_fqn,
            columns=colonnes,
            description=f"Importé depuis {fichier.name} ({len(lignes)} lignes lues).",
        )

    def close(self) -> None:
        """Rien à fermer ici. Sur une vraie source : connexions, sessions, fichiers."""
