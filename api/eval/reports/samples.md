# Extraction accuracy: samples

3 receipts from `api/eval/sets/samples/labels.csv`, model `claude-sonnet-5-5`, prompt version `7dd5bbaede29`, run 2026-10-30.

| Field | Correct | Accuracy | 95% interval |
|---|---|---|---|
| Merchant | 3/3 | 100.0% | 43.8% to 100.0% |
| Date | 3/3 | 100.0% | 43.8% to 100.0% |
| Total | 3/3 | 100.0% | 43.8% to 100.0% |
| Category | 3/3 | 100.0% | 43.8% to 100.0% |
| **All labeled fields** | **12/12** | **100.0%** | 75.7% to 100.0% |

- Receipts with every labeled field correct: 3/3 (100.0%)
- Extraction failures (no result after 3 tries): 0
- Latency per receipt: median 5.3 s, 95th percentile 5.3 s
- Model cost: about $0.0077 per receipt (2779 input and 211 output tokens on average)

## Misses by field

None.
## How fields are scored

- Total: within one cent of the label.
- Date: same calendar day.
- Merchant: equal after ignoring case, punctuation and suffixes such as Inc or Sdn Bhd, or at least 85% similar character by character.
- Category: exact match with the labeled Schedule C category.
- Blank labels are not scored. A failed extraction counts as wrong for every labeled field.
- Images are downscaled to 1600 px JPEG first, the same as the web app does before upload.
