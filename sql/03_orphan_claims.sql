-- Claims that match no encounter even after normalisation
select b.encounter_ref as encounter_id, 'claim ' || b.claim_id || ' has no encounter' as detail, b.billed_amount as amount_impact
from billing b
where not exists (select 1 from ehr e where e.encounter_id = b.key_norm)
