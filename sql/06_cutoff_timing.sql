-- Discharged inside the period but billed after period end
select e.encounter_id,
       'discharged ' || e.discharge_date || ', claim dated ' || b.claim_date as detail,
       b.billed_amount as amount_impact
from ehr e
join billing b on b.key_norm = e.encounter_id
where e.discharge_date between date '{period_start}' and date '{period_end}'
  and b.claim_date > date '{period_end}'
