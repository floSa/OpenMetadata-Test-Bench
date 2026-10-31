#!/usr/bin/env python3
"""Chapitre 20 — la qualité dans le code : tester une table, valider un DataFrame.

    ./omlab py tp/20-qualite-avancee/04_qualite_en_code.py

TestRunner enregistre ses tests dans le catalogue, et exécute aussi ceux déjà déclarés.
DataFrameValidator contrôle des données avant leur chargement dans l'entrepôt.
"""

import sys

sys.path.insert(0, "/omlab")

import pandas as pd
from metadata.sdk import configure
from metadata.sdk.data_quality import (
    ColumnValuesToBeBetween,
    ColumnValuesToBeNotNull,
    ColumnValuesToBeUnique,
    TableRowCountToBeBetween,
    TestRunner,
)
from metadata.sdk.data_quality.dataframes.dataframe_validator import DataFrameValidator

from lib.om import HOST, TOKEN, fqn

configure(host=f"{HOST}/api", jwt_token=TOKEN)

print("--- TestRunner sur raw.customers ---")
runner = TestRunner.for_table(fqn("raw", "customers"))
runner.add_tests(
    TableRowCountToBeBetween(min_count=100, max_count=100_000),
    ColumnValuesToBeNotNull(column="country"),
)
for reponse in runner.run():
    print(f"  {reponse.testCase.name.root:<46} {reponse.testCaseResult.testCaseStatus.value}")

print("\n--- DataFrameValidator sur un lot à charger ---")
lot = pd.DataFrame({
    "order_id": [1, 2, 2, 4],
    "amount": [19.9, 54.0, 12.5, -3.0],
    "customer_id": [10, 11, None, 13],
})
validateur = DataFrameValidator()
validateur.add_tests(
    ColumnValuesToBeUnique(column="order_id"),
    ColumnValuesToBeNotNull(column="customer_id"),
    ColumnValuesToBeBetween(column="amount", min_value=0, max_value=10_000),
)
resultat = validateur.validate(lot)
print(f"  Chargement autorisé ? {resultat.success}")
# La validation s'arrête au premier échec : 3 tests déclarés, un seul verdict.
for cas, verdict in resultat.test_cases_and_results:
    print(f"  {cas.testDefinition.name:<26} {verdict.testCaseStatus.value:<8} {verdict.result}")
