-- Payment cost center differs from the cost center mapped to the encounter's department
select e.encounter_id, 'posted to ' || f.cost_center || ', expected ' || m.cost_center as detail, f.paid_amount as amount_impact
from ehr e
join finance f on f.key_norm = e.encounter_id
join mapping m on m.ehr_dept = e.dept
where f.cost_center <> m.cost_center
