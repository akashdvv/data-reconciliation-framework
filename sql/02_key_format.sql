-- Claims that only match an encounter AFTER key normalisation (format drift, not a missing record)
select b.key_norm as encounter_id, 'billing key ' || b.encounter_ref || ' vs EHR ' || b.key_norm as detail, 0.0 as amount_impact
from billing b
where b.encounter_ref <> b.key_norm
  and exists (select 1 from ehr e where e.encounter_id = b.key_norm)
