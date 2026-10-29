-- Billed amount differs from the EHR charge by more than the tolerance (first claim per encounter)
with first_claim as (
    select *, row_number() over (partition by key_norm order by claim_id) as rn from billing
)
select e.encounter_id,
       'EHR ' || e.charge_amount || ' vs billed ' || round(b.billed_amount, 2) as detail,
       round(b.billed_amount - e.charge_amount, 2) as amount_impact
from ehr e
join first_claim b on b.key_norm = e.encounter_id and b.rn = 1
where abs(b.billed_amount - e.charge_amount) > {amount_abs}
