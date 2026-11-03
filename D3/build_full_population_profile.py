"""One-off scan of the FULL H&M transactions file (31.8M rows) to build a small
reference profile used by the D3 notebook's representativeness checks.

Output: reference/full_population_profile.json  (a few KB)
The notebook loads this file; it does not need the 3.5 GB file to run.

Usage: python -I build_full_population_profile.py <H&M folder> <out folder>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

raw = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

art = pd.read_csv(raw / "articles.csv", dtype={"article_id": str},
                  usecols=["article_id", "index_group_name", "product_group_name"])
grp = art.set_index("article_id")["index_group_name"]
pgrp = art.set_index("article_id")["product_group_name"]

month_grp = {}       # (month, index_group) -> rows
channel = {}         # channel -> rows
prod_grp = {}        # product_group -> rows
cust_rows = {}       # customer_id -> rows
basket_size = {}     # items per customer-day -> n baskets
carry = None
total = 0

reader = pd.read_csv(raw / "transactions_train.csv", chunksize=2_000_000,
                     dtype={"article_id": str, "sales_channel_id": "int8"},
                     usecols=["t_dat", "customer_id", "article_id", "sales_channel_id"])


def tally(df):
    """Accumulate everything that does not depend on chunk boundaries."""
    global total
    total += len(df)
    m = df["t_dat"].str.slice(0, 7)
    g = df["article_id"].map(grp)
    for (mm, gg), n in df.groupby([m, g], observed=True).size().items():
        month_grp[(mm, gg)] = month_grp.get((mm, gg), 0) + int(n)
    for k, n in df["sales_channel_id"].value_counts().items():
        channel[int(k)] = channel.get(int(k), 0) + int(n)
    for k, n in df["article_id"].map(pgrp).value_counts().items():
        prod_grp[k] = prod_grp.get(k, 0) + int(n)
    for k, n in df["customer_id"].value_counts().items():
        cust_rows[k] = cust_rows.get(k, 0) + int(n)


def baskets(df):
    sizes = df.groupby(["customer_id", "t_dat"]).size().value_counts()
    for k, n in sizes.items():
        basket_size[int(k)] = basket_size.get(int(k), 0) + int(n)


for chunk in reader:
    # file is sorted by date, so only the last date of a chunk can continue in the next
    tally(chunk)
    if carry is not None:
        chunk = pd.concat([carry, chunk], ignore_index=True)
    last = chunk["t_dat"].max()
    carry = chunk[chunk["t_dat"] == last]
    baskets(chunk[chunk["t_dat"] != last])
    print("rows", total, flush=True)
baskets(carry)

cr = pd.Series(cust_rows)
profile = {
    "rows": total,
    "customers_with_purchases": int(len(cr)),
    "rows_per_customer_quantiles": {str(q): float(cr.quantile(q)) for q in [.1, .25, .5, .75, .9, .99]},
    "rows_per_customer_mean": float(cr.mean()),
    "month_index_group": [[m, g, n] for (m, g), n in sorted(month_grp.items())],
    "sales_channel": channel,
    "product_group": prod_grp,
    "basket_size_hist": {str(k): v for k, v in sorted(basket_size.items())},
}
(out / "full_population_profile.json").write_text(json.dumps(profile))
print("done", total, "baskets", sum(basket_size.values()))
