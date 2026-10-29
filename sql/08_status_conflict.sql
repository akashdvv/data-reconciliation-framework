-- Encounters cancelled in the EHR that still have a claim
select e.encounter_id, 'EHR status CANCELLED but claim ' || b.claim_id || ' submitted' as detail, b.billed_amount as amount_impact
from ehr e
join billing b on b.key_norm = e.encounter_id
where e.status = 'CANCELLED'
