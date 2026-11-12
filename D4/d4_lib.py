"""D4 shared code: data loading, per-week feature context, candidate generation, metrics.

Every statistic for a target week that starts on day S is computed from rows with t_dat < S.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

VALID_START = pd.Timestamp("2020-09-09")
TEST_START = pd.Timestamp("2020-09-16")
WEEK = pd.Timedelta(days=7)
K = 12

FEATS = [
    "rep_cnt", "rep_days", "rep_flag", "cf_score", "cf_rank", "pop_flag",
    "pop7", "pop7_rank", "pop28", "trend", "item_days_first", "item_price",
    "user_price", "price_ratio", "user_days", "user_recency", "user_units",
    "user_age", "age_gap", "type_share",
    "product_type_no", "index_group_no", "garment_group_no",
]
CATS = ["product_type_no", "index_group_no", "garment_group_no"]

# Candidate settings for the learned rankers, fixed in advance (validation_design.json).
CAND = dict(rep_days=56, pair_weeks=12, nbrs=20, recent_src=10, cf_keep=40, pop_n=50, hl=14.0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(data_dir: str | Path):
    d = Path(data_dir)
    tx_path = d / "transactions_clean.csv.gz"
    expected = {ln.split()[1]: ln.split()[0] for ln in (d / "SHA256SUMS.txt").read_text().splitlines() if ln.strip()}
    got = sha256(tx_path)
    if got != expected["transactions_clean.csv.gz"]:
        raise SystemExit(f"transactions_clean.csv.gz checksum mismatch: {got}")
    t = pd.read_csv(tx_path, dtype={"article_id": str},
                    usecols=["customer_key", "t_dat", "article_id", "price", "qty", "split"])
    t["t_dat"] = pd.to_datetime(t["t_dat"])
    a = pd.read_csv(d / "articles_clean.csv.gz", dtype={"article_id": str},
                    usecols=["article_id", "product_type_no", "index_group_no", "garment_group_no"])
    a = a[a.article_id.isin(t.article_id.unique())].reset_index(drop=True)
    code = pd.Series(np.arange(len(a), dtype=np.int32), index=a.article_id)
    t["art"] = code.loc[t.article_id].to_numpy()
    a["art"] = np.arange(len(a), dtype=np.int32)
    c = pd.read_csv(d / "customers_clean.csv.gz", usecols=["customer_key", "age", "age_band"])
    t = t.drop(columns="article_id")
    version = f"data-v1.0 (tx sha256 {got[:12]})"
    return t, a, c, version


def truth(t: pd.DataFrame, start: pd.Timestamp) -> dict[int, set]:
    w = t[(t.t_dat >= start) & (t.t_dat < start + WEEK)]
    return w.groupby("customer_key")["art"].agg(set).to_dict()


def map_at_k(gt: dict, pred: dict, k: int = K) -> tuple[float, float]:
    aps, recs = [], []
    for u, act in gt.items():
        p = pred.get(u, [])[:k]
        hits, s = 0, 0.0
        for i, x in enumerate(p):
            if x in act:
                hits += 1
                s += hits / (i + 1)
        aps.append(s / min(len(act), k))
        recs.append(hits / len(act))
    return float(np.mean(aps)), float(np.mean(recs))


def map_per_user(gt: dict, pred: dict, k: int = K) -> pd.Series:
    out = {}
    for u, act in gt.items():
        p = pred.get(u, [])[:k]
        hits, s = 0, 0.0
        for i, x in enumerate(p):
            if x in act:
                hits += 1
                s += hits / (i + 1)
        out[u] = s / min(len(act), k)
    return pd.Series(out)


class Context:
    """Everything known on the morning of `start` (rows with t_dat < start)."""

    def __init__(self, t, a, c, start, pair_weeks=CAND["pair_weeks"], nbrs=CAND["nbrs"]):
        self.start = start
        h = t[t.t_dat < start]
        self.h = h
        days = lambda x: (start - x).dt.days
        last7 = h[h.t_dat >= start - WEEK]
        last28 = h[h.t_dat >= start - 4 * WEEK]
        pop7 = last7.groupby("art").qty.sum().rename("pop7")
        pop28 = last28.groupby("art").qty.sum().rename("pop28")
        it = a.set_index("art")[CATS].join(pop7).join(pop28)
        it[["pop7", "pop28"]] = it[["pop7", "pop28"]].fillna(0)
        it["pop7_rank"] = it.pop7.rank(ascending=False, method="first")
        it["trend"] = (it.pop7 + 1) / (it.pop28 / 4 + 1)
        first = h.groupby("art").t_dat.min()
        it = it.join(days(first).rename("item_days_first"), how="left")
        it = it.join(last28.groupby("art").price.mean().rename("item_price"))
        l28a = last28.merge(c[["customer_key", "age"]], on="customer_key", how="left")
        it = it.join(l28a.groupby("art").age.mean().rename("item_age"))
        self.items = it
        self.top = it.sort_values(["pop7", "pop28"], ascending=False).index.to_numpy()

        us = h.groupby("customer_key").agg(user_days=("t_dat", "nunique"), last=("t_dat", "max"),
                                            user_units=("qty", "sum"), user_price=("price", "mean"))
        us["user_recency"] = days(us.pop("last"))
        us = us.join(c.set_index("customer_key")["age"].rename("user_age"))
        self.users = us
        ht = h[["customer_key", "art", "qty"]].merge(a[["art", "product_type_no"]], on="art")
        ts = ht.groupby(["customer_key", "product_type_no"]).qty.sum()
        self.type_share = (ts / ts.groupby(level=0).transform("sum")).rename("type_share").reset_index()

        # Item-to-item co-purchase neighbours from same-customer same-day baskets.
        b = h[h.t_dat >= start - pair_weeks * WEEK][["customer_key", "t_dat", "art"]].drop_duplicates()
        b["bid"] = b.groupby(["customer_key", "t_dat"]).ngroup()
        size = b.groupby("bid").art.transform("size")
        b = b[(size > 1) & (size <= 30)][["bid", "art"]]
        n = b.groupby("art").size()
        p = b.merge(b, on="bid")
        p = p[p.art_x != p.art_y]
        co = p.groupby(["art_x", "art_y"]).size().rename("co").reset_index()
        co["sim"] = co.co / np.sqrt(n.loc[co.art_x].to_numpy() * n.loc[co.art_y].to_numpy())
        co = co.sort_values(["art_x", "sim", "co"], ascending=[True, False, False])
        self.nbr = co.groupby("art_x").head(nbrs).rename(columns={"art_x": "src", "art_y": "art"})[["src", "art", "sim"]]

    def candidates(self, users, rep_days=CAND["rep_days"], recent_src=CAND["recent_src"],
                   cf_keep=CAND["cf_keep"], pop_n=CAND["pop_n"], hl=CAND["hl"]):
        s = self.start
        hu = self.h[self.h.customer_key.isin(users)]
        r = hu[hu.t_dat >= s - pd.Timedelta(days=rep_days)]
        rep = r.groupby(["customer_key", "art"]).agg(rep_cnt=("qty", "sum"), last=("t_dat", "max")).reset_index()
        rep["rep_days"] = (s - rep.pop("last")).dt.days
        rep["rep_flag"] = 1

        src = hu.groupby(["customer_key", "art"]).t_dat.max().reset_index()
        src = src.sort_values(["customer_key", "t_dat"], ascending=[True, False]).groupby("customer_key").head(recent_src)
        src["w"] = np.exp(-((s - src.t_dat).dt.days) / hl)
        cf = src.rename(columns={"art": "src"}).merge(self.nbr, on="src")
        cf["cf_score"] = cf.w * cf.sim
        cf = cf.groupby(["customer_key", "art"]).cf_score.sum().reset_index()
        cf = cf.sort_values(["customer_key", "cf_score"], ascending=[True, False])
        cf["cf_rank"] = cf.groupby("customer_key").cumcount() + 1
        cf = cf[cf.cf_rank <= cf_keep]

        top = self.top[:pop_n]
        pop = pd.DataFrame({"customer_key": np.repeat(np.asarray(list(users)), len(top)),
                            "art": np.tile(top, len(users)), "pop_flag": 1})
        x = pop.merge(rep, on=["customer_key", "art"], how="outer").merge(cf, on=["customer_key", "art"], how="outer")
        x[["rep_cnt", "rep_flag", "pop_flag", "cf_score"]] = x[["rep_cnt", "rep_flag", "pop_flag", "cf_score"]].fillna(0)
        x["rep_days"] = x.rep_days.fillna(999)
        x["cf_rank"] = x.cf_rank.fillna(999)
        return x

    def features(self, x):
        x = x.merge(self.items, left_on="art", right_index=True, how="left")
        x = x.merge(self.users, left_on="customer_key", right_index=True, how="left")
        x = x.merge(self.type_share, on=["customer_key", "product_type_no"], how="left")
        x[["pop7", "pop28"]] = x[["pop7", "pop28"]].fillna(0)
        x["pop7_rank"] = x.pop7_rank.fillna(len(self.items) + 1)
        x["type_share"] = x.type_share.fillna(0)
        x["user_days"] = x.user_days.fillna(0)
        x["user_units"] = x.user_units.fillna(0)
        x["price_ratio"] = x.item_price / x.user_price
        x["age_gap"] = (x.user_age - x.item_age).abs()
        return x


def rank_lists(x: pd.DataFrame, score: str, fallback: np.ndarray, users) -> dict:
    """Top-12 per user by `score`, topped up with the popularity list."""
    x = x.sort_values(["customer_key", score, "art"], ascending=[True, False, True])
    top = x.groupby("customer_key").head(K).groupby("customer_key")["art"].agg(list).to_dict()
    fb = list(fallback[:K * 3])
    out = {}
    for u in users:
        p = top.get(u, [])
        if len(p) < K:
            seen = set(p)
            p = p + [i for i in fb if i not in seen][: K - len(p)]
        out[u] = p
    return out


def cand_recall(x: pd.DataFrame, gt: dict) -> float:
    have = x.groupby("customer_key")["art"].agg(set).to_dict()
    tot = sum(len(v) for v in gt.values())
    hit = sum(len(v & have.get(u, set())) for u, v in gt.items())
    return hit / tot


def label(x: pd.DataFrame, gt: dict) -> pd.DataFrame:
    pos = pd.DataFrame([(u, i) for u, s in gt.items() for i in s], columns=["customer_key", "art"])
    pos["y"] = 1
    x = x.merge(pos, on=["customer_key", "art"], how="left")
    x["y"] = x.y.fillna(0).astype(np.int8)
    return x
