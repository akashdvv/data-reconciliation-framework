-- Aggregate tie-out: department totals across the three systems
with ehr_t as (
    select dept, count(*) as encounters, sum(charge_amount) as ehr_charges from ehr where status = 'COMPLETED' group by dept
),
bill_t as (
    select m.ehr_dept as dept, sum(b.billed_amount) as billed
    from billing b join mapping m on m.billing_dept_code = b.dept_code group by m.ehr_dept
),
fin_t as (
    select m.ehr_dept as dept, sum(f.billed_amount) as finance_billed
    from finance f join mapping m on m.cost_center = f.cost_center group by m.ehr_dept
)
select e.dept, e.encounters,
       round(e.ehr_charges, 2) as ehr_charges,
       round(b.billed, 2) as billed,
       round(f.finance_billed, 2) as finance_billed,
       round(100 * (b.billed - e.ehr_charges) / e.ehr_charges, 2) as billing_variance_pct,
       round(100 * (f.finance_billed - e.ehr_charges) / e.ehr_charges, 2) as finance_variance_pct
from ehr_t e left join bill_t b using (dept) left join fin_t f using (dept)
order by e.dept
