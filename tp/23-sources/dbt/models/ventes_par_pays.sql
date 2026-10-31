{{ config(tags=['ventes']) }}

select
    c.country,
    count(*)      as nb_commandes,
    sum(o.amount) as total
from {{ source('raw', 'orders') }} o
join {{ source('raw', 'customers') }} c using (customer_id)
where o.status = 'completed'
group by c.country
