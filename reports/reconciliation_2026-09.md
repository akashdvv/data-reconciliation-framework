# Month-end reconciliation - September 2026

**Release gate: FAIL - hold reports**

- missing_in_billing: 18 blocking exception(s)
- duplicate_claim: 15 blocking exception(s)
- status_conflict: 9 blocking exception(s)
- CARD billing total off by -0.64% (limit 0.5%)
- CARD finance total off by -0.54% (limit 0.5%)
- NEUR billing total off by -1.65% (limit 0.5%)

| Check | Severity | Owner | Exceptions | $ impact | Blocks release |
|---|---|---|---|---|---|
| missing_in_billing | critical | Charge capture | 18 | $37,481 | yes |
| key_format | warning | Data engineering | 12 | $0 |  |
| orphan_claim | critical | Billing | 0 | $0 |  |
| duplicate_claim | critical | Billing | 15 | $30,743 | yes |
| amount_mismatch | high | Charge capture | 20 | $23,350 |  |
| cutoff_timing | medium | Finance | 14 | $67,119 |  |
| dept_mapping | medium | Data engineering | 10 | $0 |  |
| status_conflict | critical | Billing | 9 | $26,847 | yes |
| cost_center | medium | Finance | 11 | $16,818 |  |

## Detection vs. injected ground truth

| Issue | Injected | Flagged | Caught | Recall | Precision |
|---|---|---|---|---|---|
| amount_mismatch | 20 | 20 | 20 | 100% | 100% |
| cost_center | 11 | 11 | 11 | 100% | 100% |
| cutoff_timing | 14 | 14 | 14 | 100% | 100% |
| dept_mapping | 10 | 10 | 10 | 100% | 100% |
| duplicate_claim | 15 | 15 | 15 | 100% | 100% |
| key_format | 12 | 12 | 12 | 100% | 100% |
| missing_in_billing | 18 | 18 | 18 | 100% | 100% |
| status_conflict | 9 | 9 | 9 | 100% | 100% |
