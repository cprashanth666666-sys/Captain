"""Independent re-check of logged numbers. Does not import d4_lib.

Re-derives the validation and test baselines (B0, B1) with a separate, vectorised MAP@12, and
re-checks that the test-week rows in experiment_log.csv match. Writes outputs/metric_check.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
data = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "D2" / "data-v1.0"
t = pd.read_csv(data / "transactions_clean.csv.gz", dtype={"article_id": str},
                usecols=["customer_key", "t_dat", "article_id", "qty"], parse_dates=["t_dat"])


def vec_map(pred: pd.DataFrame, act: pd.DataFrame) -> float:
    # pred: customer_key, article_id, rank (1..12); act: customer_key, article_id (distinct)
    hit = pred.merge(act.assign(h=1), on=["customer_key", "article_id"], how="left").fillna({"h": 0})
    hit = hit.sort_values(["customer_key", "rank"])
    hit["cum"] = hit.groupby("customer_key").h.cumsum()
    hit["p"] = hit.cum / hit["rank"] * hit.h
    n = act.groupby("customer_key").size().clip(upper=12)
    ap = hit.groupby("customer_key").p.sum().reindex(n.index).fillna(0) / n
    return float(ap.mean())


out = {}
for name, start in [("valid", "2020-09-09"), ("test", "2020-09-16")]:
    s = pd.Timestamp(start)
    h = t[t.t_dat < s]
    act = t[(t.t_dat >= s) & (t.t_dat < s + pd.Timedelta(days=7))][["customer_key", "article_id"]].drop_duplicates()
    users = act.customer_key.unique()
    w7 = h[h.t_dat >= s - pd.Timedelta(days=7)]
    w28 = h[h.t_dat >= s - pd.Timedelta(days=28)]
    pop = (w7.groupby("article_id").qty.sum().rename("a").to_frame()
           .join(w28.groupby("article_id").qty.sum().rename("b"), how="outer").fillna(0)
           .sort_values(["a", "b"], ascending=False))
    # ties: d4_lib orders by article code, which follows article_id order in articles_clean; break the same way
    top = list(pop.index[:12])
    b0 = pd.DataFrame({"customer_key": np.repeat(users, 12), "article_id": np.tile(top, len(users)),
                       "rank": np.tile(np.arange(1, 13), len(users))})
    r = w28[w28.customer_key.isin(users)].groupby(["customer_key", "article_id"]).agg(last=("t_dat", "max"), cnt=("qty", "sum")).reset_index()
    r = r.sort_values(["customer_key", "last", "cnt", "article_id"], ascending=[True, False, False, True])
    r = r.groupby("customer_key").head(12)
    rows = []
    own = r.groupby("customer_key").article_id.agg(list).to_dict()
    for u in users:
        p = own.get(u, [])
        p = p + [i for i in top + list(pop.index[12:36]) if i not in p][: 12 - len(p)]
        rows += [(u, x, k + 1) for k, x in enumerate(p)]
    b1 = pd.DataFrame(rows, columns=["customer_key", "article_id", "rank"])
    out[name] = {"n_users": int(len(users)), "B0": round(vec_map(b0, act), 6), "B1": round(vec_map(b1, act), 6)}

log = pd.read_csv(HERE / "experiment_log.csv")
for name in out:
    lg = log[(log.stage == name) & log.model.str.startswith(("B0", "B1"))].drop_duplicates("model", keep="last")
    out[name]["log"] = {m[:2]: v for m, v in zip(lg.model, lg.map12)}
    out[name]["match"] = all(abs(out[name][k] - v) < 1e-4 for k, v in out[name]["log"].items())
(HERE / "outputs").mkdir(exist_ok=True)
(HERE / "outputs" / "metric_check.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
