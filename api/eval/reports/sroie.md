# Extraction accuracy: sroie

80 receipts from `api/eval/data/sroie/labels.csv`, model `claude-sonnet-5-5`, prompt version `7dd5bbaede29`, run 2026-10-30.

| Field | Correct | Accuracy | 95% interval |
|---|---|---|---|
| Merchant, exact name | 58/80 | 72.5% | 61.9% to 81.1% |
| Merchant, business identified | 78/80 | 97.5% | 91.3% to 99.3% |
| Date | 80/80 | 100.0% | 95.4% to 100.0% |
| Total | 78/80 | 97.5% | 91.3% to 99.3% |
| Category | not labeled | | |
| **All labeled fields, strict** | **216/240** | **90.0%** | 85.6% to 93.2% |
| **All labeled fields, merchant as business identified** | **236/240** | **98.3%** | 95.8% to 99.4% |

- Receipts with every labeled field correct: 56/80 (70.0%)
- Extraction failures (no result after 3 tries): 0
- Latency per receipt: median 4.4 s, 95th percentile 8.7 s
- Model cost: about $0.0102 per receipt (3195 input and 380 output tokens on average)

## Misses by field

### Merchant, exact name: 22 missed

| File | Expected | Got |
|---|---|---|
| 050.jpg | TIMELESS KITCHENETTE SDN BHD | Morganfield's (Timeless Kitchenette Sdn Bhd) |
| 091.jpg | TRI SHAAS SDN BHD | Mydin Mart Sri Muda (Tri Shaas Sdn Bhd) |
| 144.jpg | GERBANG ALAF RESTAURANTS SDN BHD | McDonald's Shell Mahkota Cheras DT (Gerbang Alaf Restaurants Sdn Bhd) |
| 145.jpg | GERBANG ALAF RESTAURANTS SDN BHD | McDonald's Shell Mahkota Cheras DT (Gerbang Alaf Restaurants Sdn Bhd) |
| 228.jpg | TONYMOLY VIVA CITY | Tonymoly Viva City (Tonymoly Shop 95874) |
| 229.jpg | ANZEL ADVERTISING (M) SDN BHD | EXPrint (Anzel Advertising (M) Sdn Bhd) |
| 321.jpg | HAXINCONE RESOURCES SDN BHD | FamilyMart (Maxincone Resources Sdn Bhd), The Sunnit USJ |
| 327.jpg | SUBANG HEALTHCARE SDN BHD | AA Pharmacy (Subang Healthcare Sdn Bhd) |
| 408.jpg | EDEN IMPRESSION SDN BHD | Sushi Q |
| 430.jpg | UNIHAKKA INTERNATIONAL SDN BHD | Unihakka International Sdn Bhd (Bar Wang Rice@Permas Jaya) |
| 432.jpg | UNIHAKKA INTERNATIONAL SDN BHD | Unihakka International Sdn Bhd (Bar Wang Rice@Permas Jaya) |
| 439.jpg | UNIHAKKA INTERNATIONAL SDN BHD | Unihakka International SDN BHD (Bar Wang Rice @ Permas Jaya) |
| 443.jpg | MR. D.I.Y. (M) SDN BHD | Mr. D.I.Y. (M) Sdn Bhd (IOI Puchong) |
| 451.jpg | MR. D.I.Y. (M) SDN BHD | MR. D.I.Y. (M) SDN BHD (IOI Puchong) |
| 460.jpg | DIMILIKI OLEH T PLUS F&B SDN. BHD. | AMPHAWA THAI TEA & CO. |
| 518.jpg | RAPID RAIL SDN BHD | Rapid Rail Sdn Bhd (MRT, operated by rapidKL) |
| 525.jpg | AEON CO. (M) BHD | AEON CO. (M) BHD, AEON Taman Maluri |
| 535.jpg | UNIHAKKA INTERNATIONAL SDN BHD | UNIHAKKA INTERNATIONAL SDN BHD (Bar Wang Rice@Permas Jaya) |
| 537.jpg | UNIHAKKA INTERNATIONAL SDN BHD | UNIHAKKA INTERNATIONAL SDN BHD (Bar Wang Rice @ Permas Jaya) |
| 550.jpg | GERBANG ALAF RESTAURANTS SDN BHD | McDonald's Shell Mahkota Cheras DT (Gerbang Alaf Restaurants Sdn Bhd) |
| 589.jpg | MYNEWS RETAIL SB | myNEWS (MYNEWS RETAIL SB), Oasis Village |
| 591.jpg | OGN GROUP SDN BHD | JIMART@SP3 (OGN Group Sdn Bhd) |

Of these, 2 also fail the business-identified rule:

- 408.jpg: expected EDEN IMPRESSION SDN BHD, got Sushi Q
- 460.jpg: expected DIMILIKI OLEH T PLUS F&B SDN. BHD., got AMPHAWA THAI TEA & CO.

### Total: 2 missed

| File | Expected | Got |
|---|---|---|
| 316.jpg | 1.38 | 1.40 |
| 561.jpg | 17.22 | 17.20 |

## How fields are scored

- Total: within one cent of the label.
- Date: same calendar day.
- Merchant, exact name: equal after ignoring case, punctuation and suffixes such as Inc or Sdn Bhd, or at least 85% similar character by character.
- Merchant, business identified: also counts when one name contains the other, for example "McDonald's (Gerbang Alaf Restaurants Sdn Bhd)" for the label "Gerbang Alaf Restaurants Sdn Bhd", allowing a misread character or two. Labels in some datasets use the legal company name while the model also gives the brand and branch, so both scores are shown.
- Category: exact match with the labeled Schedule C category.
- Blank labels are not scored. A failed extraction counts as wrong for every labeled field.
- Images are downscaled to 1600 px JPEG first, the same as the web app does before upload.
