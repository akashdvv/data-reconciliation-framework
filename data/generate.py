"""
Generate one month of hospital revenue-cycle data from three systems, with known discrepancies.

    EHR        encounters.csv  - what care was delivered and its charge
    Billing    claims.csv      - what was billed to payers
    Finance    payments.csv    - what was posted to the general ledger

Clean data agrees across all three. We then inject 8 kinds of real-world discrepancy and record
each one in ground_truth.csv, so the reconciliation engine's detection rate can be measured.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SEED = 11
MONTH_START, MONTH_END = date(2026, 9, 1), date(2026, 9, 30)
DEPTS = {"CARD": ("CARDIO", "CC-410"), "ORTH": ("ORTHO", "CC-420"), "ONC": ("ONCOL", "CC-430"),
         "EMER": ("EMERG", "CC-440"), "PEDS": ("PEDIA", "CC-450"), "NEUR": ("NEURO", "CC-460")}
N = 4000


def main(out: Path = ROOT, inject: bool = True) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    enc, clm, pay, truth = [], [], [], []
    for i in range(1, N + 1):
        eid = f"E{i:06d}"
        dept = rng.choice(list(DEPTS))
        admit = MONTH_START + timedelta(days=rng.randint(0, 27))
        discharge = admit + timedelta(days=rng.choice([0, 0, 1, 2, 3, 5]))
        discharge = min(discharge, MONTH_END)
        charge = round(rng.lognormvariate(7.6, 0.8), 2)
        enc.append({"encounter_id": eid, "patient_id": f"P{rng.randint(1, 3200):05d}", "dept": dept,
                    "admit_date": admit, "discharge_date": discharge, "status": "COMPLETED", "charge_amount": charge})
        claim_date = discharge + timedelta(days=rng.randint(0, 3))
        claim_date = min(claim_date, MONTH_END)
        clm.append({"claim_id": f"C{i:07d}", "encounter_ref": eid, "dept_code": DEPTS[dept][0],
                    "claim_date": claim_date, "billed_amount": charge, "claim_status": "SUBMITTED"})
        paid = round(charge * rng.uniform(0.55, 0.85), 2)
        pay.append({"payment_id": f"PAY{i:07d}", "encounter_ref": eid, "cost_center": DEPTS[dept][1],
                    "posting_date": claim_date, "billed_amount": charge, "paid_amount": paid})

    enc_df, clm_df, pay_df = pd.DataFrame(enc), pd.DataFrame(clm), pd.DataFrame(pay)
    if not inject:
        ids = []
    else:
        ids = list(enc_df.encounter_id)
    rng.shuffle(ids)
    pick = iter(ids)

    def take(n):
        return [next(pick) for _ in range(n)]

    if inject:
        # 1. Unbilled encounters: care delivered, no claim
        for e in take(18):
            clm_df = clm_df[clm_df.encounter_ref != e]
            pay_df = pay_df[pay_df.encounter_ref != e]
            truth.append((e, "missing_in_billing", "Unbilled encounter (charge capture gap)"))
        # 2. Key format drift: billing drops leading zeros (E000123 -> E123) - looks orphaned unless normalised
        for e in take(12):
            clm_df.loc[clm_df.encounter_ref == e, "encounter_ref"] = "E" + str(int(e[1:]))
            truth.append((e, "key_format", "Key format mismatch (leading zeros dropped)"))
        # 3. Duplicate claims (resubmitted without voiding the original)
        for e in take(15):
            dup = clm_df[clm_df.encounter_ref == e].copy()
            dup["claim_id"] = dup["claim_id"].str.replace("C", "D", regex=False)
            clm_df = pd.concat([clm_df, dup])
            truth.append((e, "duplicate_claim", "Duplicate claim submission"))
        # 4a. Rounding differences inside tolerance (should NOT be flagged)
        for e in take(25):
            clm_df.loc[clm_df.encounter_ref == e, "billed_amount"] += rng.choice([-0.01, 0.01, 0.02])
        # 4b. Real amount mismatches (charge corrected in EHR after billing)
        for e in take(20):
            clm_df.loc[clm_df.encounter_ref == e, "billed_amount"] = (clm_df.loc[clm_df.encounter_ref == e, "billed_amount"]
                                                                       * rng.choice([0.5, 0.8, 1.25, 2.0])).round(2)
            truth.append((e, "amount_mismatch", "Charge changed after billing"))
        # 5. Cut-off timing: discharged at month end, claim dated next month
        late = enc_df[enc_df.discharge_date >= date(2026, 9, 28)].encounter_id.tolist()
        rng.shuffle(late)
        for e in late[:14]:
            if e in {t[0] for t in truth}:
                continue
            clm_df.loc[clm_df.encounter_ref == e, "claim_date"] = date(2026, 10, rng.randint(1, 3))
            pay_df.loc[pay_df.encounter_ref == e, "posting_date"] = date(2026, 10, rng.randint(1, 3))
            truth.append((e, "cutoff_timing", "Period cut-off (claim dated next month)"))
        # 6. Department mapping gap: new billing dept code not in the mapping table
        for e in take(10):
            clm_df.loc[clm_df.encounter_ref == e, "dept_code"] = "CARDIO-IP"
            truth.append((e, "dept_mapping", "Department code missing from mapping table"))
        # 7. Status conflict: encounter cancelled in EHR but claim still submitted
        for e in take(9):
            enc_df.loc[enc_df.encounter_id == e, "status"] = "CANCELLED"
            truth.append((e, "status_conflict", "Cancelled encounter was billed"))
        # 8. Payment posted to wrong cost center
        for e in take(11):
            pay_df.loc[pay_df.encounter_ref == e, "cost_center"] = "CC-999"
            truth.append((e, "cost_center", "Payment posted to wrong cost center"))


    enc_df.to_csv(out / "ehr_encounters.csv", index=False)
    clm_df.sample(frac=1, random_state=SEED).to_csv(out / "billing_claims.csv", index=False)
    pay_df.to_csv(out / "finance_payments.csv", index=False)
    pd.DataFrame(truth or [], columns=["encounter_id", "issue_type", "description"]).to_csv(out / "ground_truth.csv", index=False)
    pd.DataFrame([{"ehr_dept": k, "billing_dept_code": v[0], "cost_center": v[1]} for k, v in DEPTS.items()]
                 ).to_csv(out / "dept_mapping.csv", index=False)
    print(f"EHR {len(enc_df)} | billing {len(clm_df)} | finance {len(pay_df)} | injected issues {len(truth)} "
          f"(+25 rounding differences that must NOT be flagged)")


if __name__ == "__main__":
    main()
