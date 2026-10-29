-- More than one claim for the same encounter
select key_norm as encounter_id,
       count(*) || ' claims: ' || string_agg(claim_id, ', ' order by claim_id) as detail,
       sum(billed_amount) - min(billed_amount) as amount_impact
from billing
group by key_norm
having count(*) > 1
