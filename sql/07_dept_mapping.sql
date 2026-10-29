-- Billing department codes that are not in the mapping table
select b.key_norm as encounter_id, 'unmapped billing dept code ' || b.dept_code as detail, 0.0 as amount_impact
from billing b
where b.dept_code not in (select billing_dept_code from mapping)
