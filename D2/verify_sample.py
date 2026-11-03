"""Check that transactions_train_sample10pct.csv = ALL rows of a customer subset of the full Kaggle file.
Usage: python -I verify_sample.py <raw_dir> <out_json>"""
import json, sys
from pathlib import Path
import pandas as pd
raw = Path(sys.argv[1])
s = pd.read_csv(raw / "transactions_train_sample10pct.csv", usecols=["customer_id"])
want = s.customer_id.value_counts()
ids = set(want.index)
got, total, full_cust = {}, 0, set()
for ch in pd.read_csv(raw / "transactions_train.csv", usecols=["customer_id"], chunksize=3_000_000):
    total += len(ch)
    full_cust.update(ch.customer_id.unique())
    m = ch[ch.customer_id.isin(ids)].customer_id.value_counts()
    for k, v in m.items(): got[k] = got.get(k, 0) + int(v)
g = pd.Series(got)
res = dict(full_rows=total, full_buying_customers=len(full_cust), sample_rows=int(len(s)),
           sample_customers=len(want), sample_share_of_buying_customers=len(want) / len(full_cust),
           full_rows_for_sample_customers=int(g.sum()),
           customers_with_row_count_mismatch=int((g.reindex(want.index).fillna(0) != want).sum()))
Path(sys.argv[2]).write_text(json.dumps(res, indent=1)); print(res)
