"""Independent validation of the D3 EDA headline numbers.

Method: recompute each number from the D2 cleaned tables (data-v1.0) with fresh code (no D3 notebook code reused,
different Gini formula, visits rebuilt from basket_units), then compare with D3/outputs/key_numbers.json.
Also re-evaluates the pre-registered hypothesis rules (thresholds copied from the notebook) against D3's own numbers.

Usage: python -I validate_eda.py <data-v1.0 dir> <D3 outputs dir> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA, OUTD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
K = json.loads((OUTD / "key_numbers.json").read_text())
tx = pd.read_csv(DATA / "transactions_clean.csv.gz", dtype={"article_id": str},
                 usecols=["customer_key", "t_dat", "article_id", "sales_channel_id", "qty", "week_start", "month", "basket_units"])
cu = pd.read_csv(DATA / "customers_clean.csv.gz", usecols=["customer_key", "age", "age_band"])
ar = pd.read_csv(DATA / "articles_clean.csv.gz", dtype={"article_id": str},
                 usecols=["article_id", "index_group_name", "perceived_colour_master_name", "product_group_name"])
tx = tx.merge(ar, on="article_id", how="left")

res = []   # (metric, D3 value, independent value, tolerance, note)


def add(name, d3, mine, tol, note=""):
    res.append(dict(metric=name, d3=float(d3), independent=float(mine), abs_diff=float(abs(d3 - mine)), tol=tol,
                    ok=bool(abs(d3 - mine) <= tol), note=note))


units = tx.qty.sum()
add("units in scope", K["units_in_scope"], units, 0)
add("customers in scope", K["n_customers_in_scope"], tx.customer_key.nunique(), 0)

# visits = distinct customer-days
v = tx.groupby(["customer_key", "t_dat"], sort=False).agg(units=("qty", "sum"), ch=("sales_channel_id", "first")).reset_index()
add("mean units per visit", K["mean_units_visit"], v.units.mean(), 0.005)
add("single-unit visit share", K["p_single"], (v.units == 1).mean(), 0.002)
c = v.groupby("customer_key").agg(visits=("units", "size"), u=("units", "sum"))
add("customers with one visit", K["one_visit_cust"], (c.visits == 1).mean(), 0.002)
add("median visits per customer", K["median_visits"], c.visits.median(), 0)

x = np.sort(c.u.to_numpy().astype(float)); n = len(x)
gini = ((2 * np.arange(1, n + 1) - n - 1) * x).sum() / (n * x.sum())          # mean-difference formula
add("Gini of units per customer", K["gini"], gini, 0.002, "different formula from D3's trapezoid version")
add("top 10% customers' share of units", K["top10_units"], x[int(n * .9):].sum() / x.sum(), 0.002)
add("top 1% customers' share of units", K["top1_units"], x[int(n * .99):].sum() / x.sum(), 0.002)
add("bottom 50% customers' share of units", K["bottom50_units"], x[:int(n * .5)].sum() / x.sum(), 0.002)
add("median age (known ages)", K["median_age"], cu.age.dropna().median(), 0)
add("menswear share of units", K["menswear_share_units"], tx.loc[tx.index_group_name == "Menswear", "qty"].sum() / units, 0.0005)

known = tx[tx.perceived_colour_master_name.notna() & (tx.perceived_colour_master_name != "Unknown")]
top3 = known.groupby("perceived_colour_master_name").qty.sum().nlargest(3)
add("top-3 colour share of known-colour units", K["top3_colour"], top3.sum() / known.qty.sum(), 0.003, ", ".join(top3.index))

wk = tx.groupby("week_start").qty.sum()
wk.index = pd.to_datetime(wk.index)
pre = wk[(wk.index >= "2019-03-01") & (wk.index < "2019-09-01")].mean()
post = wk[(wk.index >= "2020-03-01") & (wk.index < "2020-09-01")].mean()
add("weekly units Mar-Aug 2020 vs 2019", K["vol_2020_vs_2019"], post / pre - 1, 0.002)
m = tx.groupby(["month", "sales_channel_id"]).qty.sum().unstack().fillna(0)
sh = (m[2] / m.sum(axis=1)); sh.index = pd.to_datetime(sh.index + "-01")
add("channel-2 share Mar-Aug 2019", K["ch2_pre"], sh[(sh.index >= "2019-03-01") & (sh.index < "2019-09-01")].mean(), 0.002)
add("channel-2 share Mar-Aug 2020", K["ch2_post"], sh[(sh.index >= "2020-03-01") & (sh.index < "2020-09-01")].mean(), 0.002)

vv = v.merge(cu[["customer_key", "age_band"]], on="customer_key")
for band in ["18-24", "65+"]:
    add(f"single-unit share, age {band}", K["seg_age"][band]["single"], (vv[vv.age_band == band].units == 1).mean(), 0.004)
for ch in (1, 2):
    add(f"single-unit share, channel {ch}", K["seg_ch"][str(ch)], (v[v.ch == ch].units == 1).mean(), 0.01,
        "channel taken from first line of the visit; D3 does the same on a different row order")

# garment-visit completeness, approximated from product groups (D3 uses a product-type role map)
g = tx[tx.product_group_name.isin(["Garment Upper body", "Garment Lower body", "Garment Full body"])]
f = g.groupby(["customer_key", "t_dat"]).product_group_name.agg(lambda s: set(s))
top = f.map(lambda s: "Garment Upper body" in s); bot = f.map(lambda s: "Garment Lower body" in s); full = f.map(lambda s: "Garment Full body" in s)
complete = ((top & bot) | full).mean()
add("garment visits that are complete outfits", K["complete"], complete, 0.03, "approximation: product groups instead of D3's role map")

# demand-churn numbers (H4): weeks Mon 2018-10-01 .. 2020-09-14 are the complete weeks in D3
aw = tx.groupby(["week_start", "article_id"]).qty.sum().reset_index()
aw = aw[(aw.week_start >= "2018-10-01") & (aw.week_start <= "2020-09-14")]
weeks = sorted(aw.week_start.unique())
byw = {w: g.set_index("article_id").qty for w, g in aw.groupby("week_start")}
jac, cov12 = [], []
for a_, b_ in zip(weeks[:-1], weeks[1:]):
    A = set(byw[a_].nlargest(100).index); B = set(byw[b_].nlargest(100).index)
    jac.append(len(A & B) / len(A | B))
    top12 = byw[a_].nlargest(12).index
    cov12.append(byw[b_].reindex(top12).fillna(0).sum() / byw[b_].sum())
add("top-100 overlap (Jaccard), 1-week gap", K["jac1"], np.mean(jac), 0.01, "mean over consecutive complete weeks")
add("next-week coverage of last week's top 12", K["cov12"], np.mean(cov12), 0.005)
au = tx.groupby("article_id").qty.sum().sort_values(ascending=False)
add("articles sold in scope", K["n_art"], len(au), 0)
add("top 1% of articles' share of units", K["top1_art"], au.iloc[:int(len(au) * .01)].sum() / au.sum(), 0.005)

# pre-registered hypothesis rules re-evaluated from D3's reported numbers (thresholds from the notebook)
rules = {
    "H1": (K["p_single"] >= .50 and K["p_pair"] <= .15),
    "H2": (K["hist"]["Product type"]["ratio"] >= 1.5 and K["hist"]["Colour (master)"]["ratio"] >= 1.5),
    "H3": (K["lift_tb_median"] >= 1.2),
    "H4": (K["top1_art"] < .25 and K["jac1"] < .50),
    "H5": (K["cramer"] >= .15 and K["single_gap"] >= .05),
    "H6": (K["top10_units"] >= .40),
    "H7": (K["top3_colour"] >= .50 and (K["light_summer"] - K["light_winter"]) >= .05),
}
verd = {h: ("Supported" if ok else "Not supported") for h, ok in rules.items()}
hyp = {h: dict(d3=K["verdicts"][h], rule_recomputed=verd[h], agree=K["verdicts"][h] == verd[h]) for h in rules}

# self-consistency: figures quoted in the insight log vs key_numbers
log = pd.read_csv(OUTD / "insight_log.csv", encoding="utf-8-sig")
text = " ".join(log.astype(str).agg(" ".join, axis=1))
checks = {f"{int(K['complete']*100)}% complete": f"{K['complete']:.0%}" in text, "mean 3.5 units": f"{K['mean_units_visit']:.1f}" in text,
          "Gini 0.64": f"{K['gini']:.2f}" in text, "top10 48%": f"{K['top10_units']:.0%}" in text,
          "-13% 2020": f"{K['vol_2020_vs_2019']*100:+.0f}%" in text, "19x repeat": f"{K['hist']['Exact article (repeat purchase)']['ratio']:.0f}x" in text}
out = dict(metrics=res, hypotheses=hyp, insight_log_text_matches=checks,
           n_metrics=len(res), n_ok=sum(r["ok"] for r in res), n_hyp_agree=sum(h["agree"] for h in hyp.values()))
OUT.write_text(json.dumps(out, indent=1))
for r in res:
    print(f"{'OK ' if r['ok'] else 'BAD'} {r['metric']:48s} D3 {r['d3']:.4f}  mine {r['independent']:.4f}  diff {r['abs_diff']:.4f}")
print({h: v_["agree"] for h, v_ in hyp.items()}, checks)
print(out["n_ok"], "/", out["n_metrics"])
