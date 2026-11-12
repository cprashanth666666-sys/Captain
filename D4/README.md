# ANCP D4: baselines, candidate models, experiment log

| Item | File |
|---|---|
| Report (max 5 pages) | `ANCP_TM_D4_v1.pdf` |
| Validation design, fixed before any model run | `validation_design.json` (its SHA-256 prefix is stamped on every log row) |
| Experiment log, one row per run | `experiment_log.csv` |
| Shared code (data, features, candidates, metric) | `d4_lib.py` |
| All runs (tune on validation, then test once) | `run_experiments.py` |
| Independent metric re-check (does not import `d4_lib`) | `validate_metrics.py` → `outputs/metric_check.json` |
| Frozen configurations, test lock, segment table, feature importance | `outputs/` |
| Report builder | `build_report.py` |
| Environment | `environment.yml`, `requirements.txt` |

## Problem and models
Top-12 next-week article recommendation per customer, scored with MAP@12 on customers who bought in the target week.
Split by date (from `data-v1.0`): train to 2020-09-08, validation 2020-09-09..15, test 2020-09-16..22.

* **B0** last-7-day best-sellers (naive). **B1** customer's own items from the last 28 days, newest first, then B0 (rule).
* **M1** item-to-item co-purchase scorer: repurchase + co-purchase neighbours + popularity, 27-setting grid.
* **M2** logistic-regression ranker on 20 numeric features (linear), C grid.
* **M3** LightGBM LambdaRank on 23 features, 12-trial random search, best trial re-run with 3 seeds.

## Reproduce
The cleaned data is not in this repository (Kaggle terms). Put `data-v1.0/` from D2 at `../D2/data-v1.0`, or pass `--data`.
The loader checks `transactions_clean.csv.gz` against `SHA256SUMS.txt` and stops on a mismatch.

```bash
conda env create -f environment.yml && conda activate ancp-d4
python -I run_experiments.py --stage tune     # validation week only; writes outputs/selected_configs.json
python -I run_experiments.py --stage test     # test week, once; writes outputs/test_lock.json
python -I validate_metrics.py                 # re-derives B0/B1 with separate code, compares with the log
python -I build_report.py                     # figures + ANCP_TM_D4_v1.pdf
```
Runtime on a 16-thread laptop: tune under 3 min, test under 1 min. Seeds are fixed (sampler 42; model 42, plus 1-3 for the variance rerun).
The `--stage test` command refuses to run twice; `--force` reruns are labelled `FORCED RERUN` in the log.
