-- Completed encounters in the period with no claim (keys compared after normalisation)
select e.encounter_id, 'no matching claim' as detail, e.charge_amount as amount_impact
from ehr e
where e.status = 'COMPLETED'
  and not exists (select 1 from billing b where b.key_norm = e.encounter_id)
