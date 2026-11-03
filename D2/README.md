# ANCP D2: data audit, data-v1.0

| Item | File |
|---|---|
| Audit report (5 pages) + datasheet (3 pages) | `ANCP_TM_D2_v1.pdf` |
| Cleaned data, version `data-v1.0` | held privately (not in repo); checksums below let anyone verify a copy or rebuild it |
| Data dictionary | `data-v1.0/data_dictionary.csv` |
| Checksums | `data-v1.0/SHA256SUMS.txt` (`cd data-v1.0 && sha256sum -c SHA256SUMS.txt`) |
| Cleaning script (raw -> cleaned) | `clean_data.py` |
| Sample-vs-full-file check | `verify_sample.py` -> `sample_integrity.json` |
| Every number in the report | `audit_metrics.json` |
| Figures / PDF builders | `make_figures.py`, `make_report.py` |

## Reproduce
Raw inputs (not in this repository; Kaggle H&M competition files): `articles.csv`, `customers.csv`,
`transactions_train_sample10pct.csv`. Input SHA-256 values are in `audit_metrics.json` under `inputs_sha256`.

```bash
python -I clean_data.py <raw_dir> .          # writes data-v1.0/ and audit_metrics.json (~70 s)
python -I make_figures.py && python -I make_report.py
```
Needs Python 3.13, pandas 2.2, numpy 2.1, matplotlib, reportlab, pypdf (checks only). Output is deterministic: a second run gives identical checksums.

## Terms
The data derives from the Kaggle "H&M Personalized Fashion Recommendations" competition (non-commercial, academic use; no
redistribution). The cleaned data tables (`data-v1.0/*.csv.gz`) are **not in this public repository**; they are shared privately with the course team and assessor. Delete them after assessment. This repository holds the code, dictionary, checksums and report.
