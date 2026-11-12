"""D4 experiments. Every model run appends one row to experiment_log.csv.

  python -I run_experiments.py --stage tune  [--data ../D2/data-v1.0]   # validation week only
  python -I run_experiments.py --stage test  [--data ../D2/data-v1.0]   # once, frozen configs
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import time
from itertools import product
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I drops the script folder from sys.path
import d4_lib as L  # noqa: E402
OUT = HERE / "outputs"
LOG = HERE / "experiment_log.csv"
COLS = ["run_id", "timestamp_utc", "stage", "eval_week_start", "model", "data_version", "features",
        "params", "seed", "map12", "recall12", "cand_recall", "n_users", "runtime_s", "design_sha", "code_sha", "notes"]
DESIGN_SHA = L.sha256(HERE / "validation_design.json")[:12]
CODE_SHA = L.sha256(HERE / "d4_lib.py")[:6] + L.sha256(Path(__file__))[:6]
LR_FEATS = [f for f in L.FEATS if f not in L.CATS]
LOG1P = ["pop7", "pop28", "rep_cnt", "user_units", "user_days", "item_days_first", "rep_days",
         "cf_rank", "pop7_rank", "trend", "user_recency"]


def log_run(stage, start, model, version, feats, params, seed, m, r, cr, n, secs, notes=""):
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
        n_prev = 0 if new else sum(1 for _ in open(LOG)) - 1
        w.writerow([f"R{n_prev + 1:03d}", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), stage,
                    start.date(), model, version, feats, json.dumps(params, sort_keys=True), seed,
                    round(m, 6), round(r, 6), "" if cr is None else round(cr, 4), n, round(secs, 1),
                    DESIGN_SHA, CODE_SHA, notes])
    print(f"{stage:5s} {model:28s} MAP@12={m:.5f} R@12={r:.4f} {params}", flush=True)


# ---------- baselines ----------
def b0_popular(ctx, users):
    top = list(ctx.top[:L.K])
    return {u: top for u in users}


def b1_repurchase(ctx, users, days=28):
    s = ctx.start
    h = ctx.h[(ctx.h.customer_key.isin(users)) & (ctx.h.t_dat >= s - pd.Timedelta(days=days))]
    g = h.groupby(["customer_key", "art"]).agg(last=("t_dat", "max"), cnt=("qty", "sum")).reset_index()
    g["score"] = -(s - g["last"]).dt.days * 1000 + g.cnt
    return L.rank_lists(g, "score", ctx.top, users)


# ---------- M1: co-purchase scorer ----------
def m1_score(x, w_cf, w_pop, hl):
    mx = max(x.pop7.max(), 1)
    return x.rep_cnt * np.exp(-x.rep_days / hl) + w_cf * x.cf_score + w_pop * x.pop7 / mx


# ---------- learned rankers ----------
def week_frame(t, a, c, start):
    gt = L.truth(t, start)
    ctx = L.Context(t, a, c, start)
    x = ctx.features(ctx.candidates(list(gt)))
    x = L.label(x, gt)
    x["week"] = start.date().isoformat()
    return x, gt, ctx


def train_frame(t, a, c, eval_start, n_weeks=4):
    parts = []
    for k in range(n_weeks, 0, -1):
        x, _, _ = week_frame(t, a, c, eval_start - k * L.WEEK)
        has_pos = x.groupby("customer_key").y.transform("max") > 0
        parts.append(x[has_pos])
    return pd.concat(parts, ignore_index=True).sort_values(["week", "customer_key"], kind="stable")


def lr_fit(tr, C, seed=42, neg_frac=0.2):
    rng = np.random.default_rng(seed)
    keep = (tr.y == 1) | (rng.random(len(tr)) < neg_frac)
    d = tr.loc[keep, LR_FEATS].copy()
    d[LOG1P] = np.log1p(d[LOG1P].clip(lower=0))
    med = d.median()
    sc = StandardScaler().fit(d.fillna(med))
    m = LogisticRegression(C=C, max_iter=1000).fit(sc.transform(d.fillna(med)), tr.y[keep])
    return m, sc, med


def lr_score(model, x):
    m, sc, med = model
    d = x[LR_FEATS].copy()
    d[LOG1P] = np.log1p(d[LOG1P].clip(lower=0))
    return m.predict_proba(sc.transform(d.fillna(med)))[:, 1]


def lgb_fit(tr, p, seed):
    grp = tr.groupby(["week", "customer_key"], sort=False).size().to_numpy()
    m = lgb.LGBMRanker(objective="lambdarank", eval_at=[12], n_jobs=-1, verbose=-1, random_state=seed,
                       bagging_freq=1 if p["subsample"] < 1 else 0, **p)
    m.fit(tr[L.FEATS], tr.y, group=grp, categorical_feature=L.CATS)
    return m


def sample_lgb(rng):
    return dict(num_leaves=int(rng.choice([15, 31, 63, 127])),
                learning_rate=float(np.round(np.exp(rng.uniform(np.log(0.02), np.log(0.2))), 4)),
                n_estimators=int(rng.choice([100, 200, 400])),
                min_child_samples=int(rng.choice([20, 50, 100, 200])),
                colsample_bytree=float(rng.choice([0.6, 0.8, 1.0])),
                subsample=float(rng.choice([0.7, 1.0])))


def evaluate(stage, start, model, version, feats, params, seed, ctx, x, score_col, gt, t0, notes=""):
    pred = L.rank_lists(x, score_col, ctx.top, list(gt))
    m, r = L.map_at_k(gt, pred)
    log_run(stage, start, model, version, feats, params, seed, m, r, L.cand_recall(x, gt), len(gt), time.time() - t0, notes)
    return m, pred


# ---------- stages ----------
def tune(t, a, c, version):
    S = L.VALID_START
    gt = L.truth(t, S)
    best = {}
    t0 = time.time()
    ctx = L.Context(t, a, c, S)
    users = list(gt)
    for name, fn, p in [("B0 popularity-7d", b0_popular, {"window_days": 7}),
                        ("B1 repurchase-28d + popularity", b1_repurchase, {"window_days": 28})]:
        t0 = time.time()
        m, r = L.map_at_k(gt, fn(ctx, users))
        log_run("valid", S, name, version, "rule", p, "n/a", m, r, None, len(gt), time.time() - t0)

    # M1 grid
    m1 = []
    for pw in (4, 8, 12):
        cx = ctx if pw == L.CAND["pair_weeks"] else L.Context(t, a, c, S, pair_weeks=pw)
        x = cx.features(cx.candidates(users))
        for w_cf, w_pop in product((0.5, 1.0, 2.0), (0.1, 0.3, 1.0)):
            t0 = time.time()
            p = dict(pair_weeks=pw, w_cf=w_cf, w_pop=w_pop, hl=L.CAND["hl"], w_rep=1.0)
            x["s"] = m1_score(x, w_cf, w_pop, L.CAND["hl"])
            m, _ = evaluate("valid", S, "M1 co-purchase scorer", version, "rep_cnt,rep_days,cf_score,pop7", p, "n/a", cx, x, "s", gt, t0)
            m1.append((m, -pw, p))
    best["M1"] = max(m1, key=lambda z: (z[0], z[1]))[2]

    # learned rankers share one training frame
    tr = train_frame(t, a, c, S)
    va = L.label(ctx.features(ctx.candidates(users)), gt)
    print("train rows", len(tr), "positives", int(tr.y.sum()), "valid rows", len(va), flush=True)

    lr_res = []
    for C in (0.01, 0.1, 1.0):
        t0 = time.time()
        mod = lr_fit(tr, C)
        va["s"] = lr_score(mod, va)
        m, _ = evaluate("valid", S, "M2 logistic-regression ranker", version, ",".join(LR_FEATS),
                        dict(C=C, neg_frac=0.2), 42, ctx, va, "s", gt, t0)
        lr_res.append((m, -C, dict(C=C, neg_frac=0.2)))
    best["M2"] = max(lr_res, key=lambda z: (z[0], z[1]))[2]

    rng = np.random.default_rng(42)
    trials = []
    for i in range(12):
        p = sample_lgb(rng)
        t0 = time.time()
        mod = lgb_fit(tr, p, 42)
        va["s"] = mod.predict(va[L.FEATS])
        m, _ = evaluate("valid", S, "M3 LightGBM LambdaRank", version, ",".join(L.FEATS), p, 42, ctx, va, "s", gt, t0,
                        f"random-search trial {i + 1}/12")
        trials.append((m, p))
    bp = max(trials, key=lambda z: z[0])[1]
    best["M3"] = bp
    for seed in (1, 2, 3):
        t0 = time.time()
        mod = lgb_fit(tr, bp, seed)
        va["s"] = mod.predict(va[L.FEATS])
        evaluate("valid", S, "M3 LightGBM LambdaRank", version, ",".join(L.FEATS), bp, seed, ctx, va, "s", gt, t0,
                 "seed-variance rerun of best trial")
    OUT.mkdir(exist_ok=True)
    (OUT / "selected_configs.json").write_text(json.dumps(
        {"selected_on": "validation week 2020-09-09..15", "design_sha": DESIGN_SHA, **best}, indent=2))


def test(t, a, c, version, force):
    lock = OUT / "test_lock.json"
    if lock.exists() and not force:
        raise SystemExit("Test week already scored (outputs/test_lock.json). Use --force only with a logged reason.")
    sel = json.loads((OUT / "selected_configs.json").read_text())
    note = "FORCED RERUN" if lock.exists() else "single test evaluation, frozen config"
    S = L.TEST_START
    gt = L.truth(t, S)
    users = list(gt)
    ctx = L.Context(t, a, c, S)
    preds = {}
    for name, fn, p in [("B0 popularity-7d", b0_popular, {"window_days": 7}),
                        ("B1 repurchase-28d + popularity", b1_repurchase, {"window_days": 28})]:
        t0 = time.time()
        preds[name] = fn(ctx, users)
        m, r = L.map_at_k(gt, preds[name])
        log_run("test", S, name, version, "rule", p, "n/a", m, r, None, len(gt), time.time() - t0, note)

    p = sel["M1"]
    t0 = time.time()
    cx = ctx if p["pair_weeks"] == L.CAND["pair_weeks"] else L.Context(t, a, c, S, pair_weeks=p["pair_weeks"])
    x = cx.features(cx.candidates(users))
    x["s"] = m1_score(x, p["w_cf"], p["w_pop"], p["hl"])
    _, preds["M1 co-purchase scorer"] = evaluate("test", S, "M1 co-purchase scorer", version,
                                                 "rep_cnt,rep_days,cf_score,pop7", p, "n/a", cx, x, "s", gt, t0, note)

    tr = train_frame(t, a, c, S)
    te = ctx.features(ctx.candidates(users))
    t0 = time.time()
    mod = lr_fit(tr, sel["M2"]["C"])
    te["s"] = lr_score(mod, te)
    _, preds["M2 logistic-regression ranker"] = evaluate("test", S, "M2 logistic-regression ranker", version,
                                                         ",".join(LR_FEATS), sel["M2"], 42, ctx, te, "s", gt, t0, note)
    t0 = time.time()
    mod = lgb_fit(tr, sel["M3"], 42)
    te["s"] = mod.predict(te[L.FEATS])
    _, preds["M3 LightGBM LambdaRank"] = evaluate("test", S, "M3 LightGBM LambdaRank", version,
                                                  ",".join(L.FEATS), sel["M3"], 42, ctx, te, "s", gt, t0, note)
    imp = pd.Series(mod.booster_.feature_importance("gain"), index=L.FEATS).sort_values(ascending=False)
    (imp / imp.sum()).round(4).to_csv(OUT / "m3_feature_importance_gain.csv", header=["share_of_gain"])

    # segment breakdown (I6 activity tiers, I7 age bands)
    seg = pd.DataFrame(index=pd.Index(users, name="customer_key"))
    seg["visit_days_before"] = ctx.users.user_days.reindex(seg.index).fillna(0)
    seg["tier"] = pd.cut(seg.visit_days_before, [-1, 0, 2, 9, 1e9], labels=["0 (cold)", "1-2", "3-9", "10+"])
    seg = seg.join(c.set_index("customer_key").age_band)
    for name, pr in preds.items():
        seg[name] = L.map_per_user(gt, pr).reindex(seg.index)
    rows = []
    for col in ("tier", "age_band"):
        g = seg.groupby(col, observed=True)
        tab = g[list(preds)].mean()
        tab.insert(0, "n_users", g.size())
        tab.insert(0, "group", tab.index.astype(str))
        tab.insert(0, "segment", col)
        rows.append(tab)
    pd.concat(rows).round(5).to_csv(OUT / "test_breakdown.csv", index=False)
    # paired bootstrap over customers (reporting only; added after tuning, before the test run)
    rng = np.random.default_rng(7)
    ap = seg[list(preds)].to_numpy()
    idx = rng.integers(0, len(ap), size=(2000, len(ap)))
    names = list(preds)
    boot = {"resamples": 2000, "seed": 7, "n_users": len(ap), "mean": dict(zip(names, ap.mean(0).round(6)))}
    for a_, b_ in [("M3 LightGBM LambdaRank", "B1 repurchase-28d + popularity"),
                   ("M3 LightGBM LambdaRank", "M2 logistic-regression ranker"),
                   ("M3 LightGBM LambdaRank", "M1 co-purchase scorer"),
                   ("M1 co-purchase scorer", "B1 repurchase-28d + popularity")]:
        d = ap[:, names.index(a_)] - ap[:, names.index(b_)]
        bd = d[idx].mean(1)
        boot[f"{a_[:2]} - {b_[:2]}"] = {"diff": round(float(d.mean()), 6), "ci95": [round(float(q), 6) for q in np.percentile(bd, [2.5, 97.5])]}
    (OUT / "test_bootstrap.json").write_text(json.dumps(boot, indent=2))
    lock.write_text(json.dumps({"scored_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                "design_sha": DESIGN_SHA, "code_sha": CODE_SHA, "note": note}, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["tune", "test"], required=True)
    ap.add_argument("--data", default=str(HERE.parent / "D2" / "data-v1.0"))
    ap.add_argument("--force", action="store_true")
    a_ = ap.parse_args()
    t, a, c, version = L.load(a_.data)
    print(version, len(t), "rows", flush=True)
    tune(t, a, c, version) if a_.stage == "tune" else test(t, a, c, version, a_.force)
