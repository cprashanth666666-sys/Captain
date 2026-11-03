"""ANCP D2 - reproducible cleaning pipeline for the H&M purchase sample (data-v1.0).

Usage:  python -I clean_data.py <raw_dir> <out_dir>
  raw_dir must hold articles.csv, customers.csv, transactions_train_sample10pct.csv (unmodified Kaggle files).
  out_dir receives data-v1.0/ (cleaned tables, data dictionary, checksums) and audit_metrics.json.

Deterministic: no randomness; customer keys are assigned in order of first appearance.
Every number quoted in the D2 report comes from audit_metrics.json written here.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "data-v1.0"
RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
DATA = OUT / VERSION
DATA.mkdir(parents=True, exist_ok=True)

NON_APPAREL = ["Unknown", "Cosmetic", "Items", "Furniture", "Garment and Shoe care",
               "Stationery", "Interior textile", "Fun"]
MIN_AGE, MAX_PLAUSIBLE_AGE = 18, 90
VALID_END = pd.Timestamp("2020-09-08")      # last day of the training window
TEST_START = pd.Timestamp("2020-09-16")     # final 7 days = held-out test week
M = {}                                      # metrics for the report

# ---------------------------------------------------------------- load
art = pd.read_csv(RAW / "articles.csv", dtype={"article_id": str})
cus = pd.read_csv(RAW / "customers.csv")
tx = pd.read_csv(RAW / "transactions_train_sample10pct.csv", dtype={"article_id": str, "sales_channel_id": "int8"},
                 parse_dates=["t_dat"])

M["raw"] = dict(articles=len(art), customers_all=len(cus), tx_rows=len(tx),
                tx_customers=int(tx.customer_id.nunique()), tx_articles=int(tx.article_id.nunique()),
                date_min=str(tx.t_dat.min().date()), date_max=str(tx.t_dat.max().date()))

# ---------------------------------------------------------------- audit: missing
miss = lambda df: {c: [int(df[c].isna().sum()), float(df[c].isna().mean())] for c in df.columns if df[c].isna().any()}
sc = cus[cus.customer_id.isin(tx.customer_id.unique())]
M["missing"] = dict(articles=miss(art), customers_all=miss(cus), customers_sample=miss(sc), transactions=miss(tx))
M["raw"]["customers_sample"] = len(sc)
M["raw"]["fashion_news_values"] = cus.fashion_news_frequency.value_counts(dropna=False).rename(str).to_dict()
M["raw"]["age_gt90_sample"] = int((sc.age > MAX_PLAUSIBLE_AGE).sum())
M["raw"]["age_lt18_sample"] = int((sc.age < MIN_AGE).sum())
M["raw"]["age_min"], M["raw"]["age_max"] = float(sc.age.min()), float(sc.age.max())
M["raw"]["age_missing_ids_not_in_customers"] = int((~tx.customer_id.isin(cus.customer_id)).sum())
M["raw"]["tx_unknown_article"] = int((~tx.article_id.isin(art.article_id)).sum())
M["raw"]["article_id_dupes"] = int(art.article_id.duplicated().sum())
M["raw"]["customer_id_dupes"] = int(cus.customer_id.duplicated().sum())

# ---------------------------------------------------------------- audit: duplicates
key = ["t_dat", "customer_id", "article_id", "price", "sales_channel_id"]
dup_extra = int(tx.duplicated(key).sum())
M["dups"] = dict(exact_extra_rows=dup_extra, share=dup_extra / len(tx),
                 distinct_rows_with_copies=int(tx.duplicated(key, keep=False).sum() - dup_extra))
# same customer, day, article but different price/channel (genuine separate lines, kept)
M["dups"]["same_cust_day_article_other_price"] = int(
    tx.drop_duplicates(key).duplicated(["t_dat", "customer_id", "article_id"]).sum())
# duplicate content in the catalogue: same product_code+colour listed under several article ids is normal; check desc dupes
M["dups"]["article_full_row_dupes"] = int(art.duplicated().sum())

# ---------------------------------------------------------------- audit: outliers (price, volume, age)
p = tx.price
q1, q3 = p.quantile([.25, .75])
M["price"] = dict(min=float(p.min()), p50=float(p.median()), p99=float(p.quantile(.99)), max=float(p.max()),
                  iqr_upper_fence=float(q3 + 1.5 * (q3 - q1)),
                  n_above_fence=int((p > q3 + 1.5 * (q3 - q1)).sum()))
art_med = tx.groupby("article_id").price.transform("median")
rel = p / art_med
M["price"]["rel_gt3_rows"] = int((rel > 3).sum())
M["price"]["rel_lt_third_rows"] = int((rel < 1 / 3).sum())
per_c = tx.groupby("customer_id").size()
M["volume"] = dict(rows_per_customer_p50=float(per_c.median()), p99=float(per_c.quantile(.99)),
                   p999=float(per_c.quantile(.999)), max=int(per_c.max()),
                   n_gt_p999=int((per_c > per_c.quantile(.999)).sum()),
                   iqr_fence=float(per_c.quantile(.75) + 1.5 * (per_c.quantile(.75) - per_c.quantile(.25))),
                   n_above_iqr_fence=int((per_c > per_c.quantile(.75) + 1.5 * (per_c.quantile(.75) - per_c.quantile(.25))).sum()))
basket_raw = tx.groupby(["customer_id", "t_dat"]).size()
M["volume"]["basket_max_rows"] = int(basket_raw.max())
M["volume"]["basket_gt50"] = int((basket_raw > 50).sum())

# ---------------------------------------------------------------- clean: articles
art["detail_desc_missing"] = art.detail_desc.isna().astype("int8")
art["detail_desc"] = art.detail_desc.fillna("")
art["in_scope"] = (~art.index_group_name.eq("Baby/Children") & ~art.product_group_name.isin(NON_APPAREL)).astype("int8")
M["articles"] = dict(in_scope=int(art.in_scope.sum()), baby=int(art.index_group_name.eq("Baby/Children").sum()),
                     non_apparel=int(art.product_group_name.isin(NON_APPAREL).sum()),
                     detail_desc_missing=int(art.detail_desc_missing.sum()))

# ---------------------------------------------------------------- clean: transactions -> qty lines
tx["article_in_scope"] = tx.article_id.map(art.set_index("article_id").in_scope)
t = tx.groupby(key, sort=False).size().rename("qty").reset_index()          # collapse exact duplicates, keep units
M["clean"] = dict(units_raw=len(tx), lines_after_collapse=len(t))
t = t.merge(art[["article_id", "in_scope", "index_group_name"]], on="article_id", how="left")
M["clean"]["units_out_of_scope_baby"] = int(t.loc[t.index_group_name.eq("Baby/Children"), "qty"].sum())
M["clean"]["units_out_of_scope_non_apparel"] = int(t.loc[t.in_scope.eq(0) & ~t.index_group_name.eq("Baby/Children"), "qty"].sum())
t = t[t.in_scope.eq(1)].drop(columns=["in_scope", "index_group_name"])
M["clean"]["units_after_scope"] = int(t.qty.sum())

# customers: sample buyers only, postal_code dropped, age rules, flag codes
c = sc.drop(columns="postal_code").copy()
c["age_raw_missing"] = c.age.isna().astype("int8")
c["age_gt90_set_missing"] = (c.age > MAX_PLAUSIBLE_AGE).astype("int8")
under = c.age < MIN_AGE
M["clean"]["customers_under18_removed"] = int(under.sum())
M["clean"]["age_gt90_set_missing"] = int(c.age_gt90_set_missing.sum())
c = c[~under].copy()
c.loc[c.age > MAX_PLAUSIBLE_AGE, "age"] = np.nan
c["FN"] = c.FN.fillna(0).astype("int8")
c["Active"] = c.Active.fillna(0).astype("int8")
c["club_member_status"] = c.club_member_status.fillna("UNKNOWN")
c["fashion_news_frequency"] = c.fashion_news_frequency.fillna("UNKNOWN").str.upper()
c["age_band"] = pd.cut(c.age, [17, 24, 34, 44, 54, 64, 200], labels=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]).astype(object)
c["age_band"] = c.age_band.fillna("unknown")
t = t[t.customer_id.isin(c.customer_id)].copy()
c = c[c.customer_id.isin(t.customer_id)].copy()          # customers whose every purchase was out of scope drop out
M["clean"]["customers_in_scope"] = len(c)
M["clean"]["lines_final"] = len(t)
M["clean"]["units_final"] = int(t.qty.sum())

# stable pseudonymous key (order of first appearance); the 64-char hash is not shipped
order = pd.Index(t.customer_id.unique())
cust_key = pd.Series(np.arange(len(order), dtype="int32"), index=order)
t["customer_key"] = t.customer_id.map(cust_key).astype("int32")
c["customer_key"] = c.customer_id.map(cust_key).astype("int32")

# ---------------------------------------------------------------- features (see feature log in the report)
t = t.sort_values(["t_dat", "customer_key", "article_id"], kind="stable").reset_index(drop=True)
t["split"] = np.where(t.t_dat >= TEST_START, "test", np.where(t.t_dat > VALID_END, "valid", "train"))
t["week_start"] = (t.t_dat - pd.to_timedelta(t.t_dat.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
t["month"] = t.t_dat.dt.strftime("%Y-%m")
b = t.groupby(["customer_key", "t_dat"]).qty.transform("sum")
t["basket_units"] = b.astype("int16")                                   # F3: contains same-day purchases (no future days)
tr = t[t.split == "train"]
ref = tr.groupby("article_id").price.median().rename("art_ref_price")  # F4: train window only
t = t.merge(ref, on="article_id", how="left")
t["price_rel"] = (t.price / t.art_ref_price).astype("float32")          # NaN for articles unseen in train
t["price_rel_flag"] = np.select([t.price_rel > 3, t.price_rel < 1 / 3], ["high", "low"], "ok")
t = t.drop(columns="art_ref_price")
M["features"] = dict(price_rel_nan=int(t.price_rel.isna().sum()), price_rel_high=int((t.price_rel_flag == "high").sum()),
                     price_rel_low=int((t.price_rel_flag == "low").sum()),
                     split_rows=t.groupby("split").qty.sum().to_dict())
trc = t[t.split == "train"].groupby("customer_key")
agg = pd.DataFrame({"units_train": trc.qty.sum(), "visits_train": trc.t_dat.nunique(),
                    "first_purchase_train": trc.t_dat.min().dt.strftime("%Y-%m-%d"),
                    "last_purchase_train": trc.t_dat.max().dt.strftime("%Y-%m-%d")})
c = c.merge(agg, left_on="customer_key", right_index=True, how="left")
c["has_train_history"] = c.units_train.notna().astype("int8")
c[["units_train", "visits_train"]] = c[["units_train", "visits_train"]].fillna(0).astype("int32")
c["heavy_buyer_flag"] = (c.units_train > c.units_train.quantile(.999)).astype("int8")   # F8 flag only, never removed
M["features"]["customers_no_train_history"] = int((c.has_train_history == 0).sum())
M["features"]["heavy_buyer_cut"] = float(c.units_train.quantile(.999))
M["features"]["heavy_buyers"] = int(c.heavy_buyer_flag.sum())

tx_out = t[["customer_key", "t_dat", "article_id", "price", "sales_channel_id", "qty", "split", "week_start", "month",
            "basket_units", "price_rel", "price_rel_flag"]].copy()
tx_out["t_dat"] = tx_out.t_dat.dt.strftime("%Y-%m-%d")
cu_out = c[["customer_key", "FN", "Active", "club_member_status", "fashion_news_frequency", "age", "age_band",
            "age_raw_missing", "age_gt90_set_missing", "units_train", "visits_train", "first_purchase_train",
            "last_purchase_train", "has_train_history", "heavy_buyer_flag"]].sort_values("customer_key")
ar_out = art.drop(columns=["detail_desc"]).assign(detail_desc=art.detail_desc)

# representativeness numbers (raw sample vs all customers, cleaned vs raw)
def smd(a, b):
    s = np.sqrt((a.var() + b.var()) / 2)
    return float((a.mean() - b.mean()) / s) if s else 0.0
others = cus[~cus.customer_id.isin(sc.customer_id)]
M["rep"] = dict(
    age_mean_sample=float(sc.age.mean()), age_mean_rest=float(others.age.mean()), age_smd=smd(sc.age.dropna(), others.age.dropna()),
    age_missing_sample=float(sc.age.isna().mean()), age_missing_rest=float(others.age.isna().mean()),
    club_sample=sc.club_member_status.value_counts(normalize=True, dropna=False).rename(str).to_dict(),
    club_rest=others.club_member_status.value_counts(normalize=True, dropna=False).rename(str).to_dict(),
    fn_sample=float(sc.FN.fillna(0).mean()), fn_rest=float(others.FN.fillna(0).mean()),
    active_sample=float(sc.Active.fillna(0).mean()), active_rest=float(others.Active.fillna(0).mean()),
    news_sample=sc.fashion_news_frequency.fillna("UNKNOWN").str.upper().value_counts(normalize=True).to_dict(),
    news_rest=others.fashion_news_frequency.fillna("UNKNOWN").str.upper().value_counts(normalize=True).to_dict(),
    sample_share_of_customers=len(sc) / len(cus),
    age_band_sample=c.age_band.value_counts(normalize=True).to_dict(),
    age_band_rest=pd.cut(others.age, [15, 17, 24, 34, 44, 54, 64, 200]).value_counts(normalize=True).rename(str).to_dict(),
)
ai = art.set_index("article_id")
tt = t.merge(ai[["index_group_name", "product_group_name", "product_type_name", "perceived_colour_master_name"]],
             left_on="article_id", right_index=True)
M["rep"]["units_by_index_group"] = (tt.groupby("index_group_name").qty.sum() / tt.qty.sum()).to_dict()
M["rep"]["units_by_product_group"] = (tt.groupby("product_group_name").qty.sum() / tt.qty.sum()).to_dict()
M["rep"]["units_by_channel"] = (tt.groupby("sales_channel_id").qty.sum() / tt.qty.sum()).rename(str).to_dict()
M["rep"]["units_by_month"] = (tt.groupby("month").qty.sum()).to_dict()
M["rep"]["catalogue_share_by_index_group"] = art.index_group_name.value_counts(normalize=True).to_dict()
M["rep"]["catalogue_in_scope_never_sold"] = int((art.in_scope.eq(1) & ~art.article_id.isin(t.article_id)).sum())
M["rep"]["colour_master_share"] = (tt.groupby("perceived_colour_master_name").qty.sum() / tt.qty.sum()).sort_values(ascending=False).head(12).to_dict()
M["rep"]["buyers_by_index_group"] = (tt.groupby("index_group_name").customer_key.nunique()).to_dict()
M["rep"]["units_per_customer_age_band"] = (tt.merge(c[["customer_key", "age_band"]], on="customer_key")
                                           .groupby("age_band").qty.sum() / len(tt)).to_dict()
M["rep"]["customers_by_age_band"] = c.age_band.value_counts().to_dict()
M["rep"]["units_by_age_band"] = tt.merge(c[["customer_key", "age_band"]], on="customer_key").groupby("age_band").qty.sum().to_dict()
M["rep"]["covid_units_2019_vs_2020_jan_aug"] = [int(tt[tt.month.between("2019-03", "2019-08")].qty.sum()),
                                                int(tt[tt.month.between("2020-03", "2020-08")].qty.sum())]

# ---------------------------------------------------------------- write
GZ = {"method": "gzip", "mtime": 0}     # fixed gzip header and LF line ends: identical bytes on any OS
tx_out.to_csv(DATA / "transactions_clean.csv.gz", index=False, compression=GZ, lineterminator="\n")
cu_out.to_csv(DATA / "customers_clean.csv.gz", index=False, compression=GZ, lineterminator="\n")
ar_out.to_csv(DATA / "articles_clean.csv.gz", index=False, compression=GZ, lineterminator="\n")

dd = [
 ("transactions_clean", "customer_key", "int32", "Pseudonymous customer id, order of first appearance. Replaces the 64-char hash.", "clean_data.py", "no", "key"),
 ("transactions_clean", "t_dat", "date YYYY-MM-DD", "Purchase date, 2018-09-20 to 2020-09-22.", "raw", "no", ""),
 ("transactions_clean", "article_id", "str(10)", "Article code, keep leading zero. Joins to articles_clean.", "raw", "no", "key"),
 ("transactions_clean", "price", "float", "Normalised price, relative scale (not a currency). Use as relative only.", "raw", "no", ""),
 ("transactions_clean", "sales_channel_id", "int", "Anonymous channel code, 1 or 2. Not labelled store/online by source.", "raw", "no", ""),
 ("transactions_clean", "qty", "int", "Units on the line: count of identical raw rows collapsed.", "derived F1", "no", ""),
 ("transactions_clean", "split", "train|valid|test", "By date: train to 2020-09-08, valid 09-09..09-15, test 09-16..09-22.", "derived F2", "no (it is the guard)", ""),
 ("transactions_clean", "week_start", "date", "Monday of the purchase week.", "derived F5", "no", ""),
 ("transactions_clean", "month", "YYYY-MM", "Calendar month.", "derived F5", "no", ""),
 ("transactions_clean", "basket_units", "int", "Units the same customer bought on the same day.", "derived F3", "yes if target is same-visit items", ""),
 ("transactions_clean", "price_rel", "float", "price / article median price in the train window. Empty if article unseen in train.", "derived F4", "no (train-only reference)", ""),
 ("transactions_clean", "price_rel_flag", "high|low|ok", "high if price_rel>3, low if <1/3. Flag only, rows kept.", "derived F4", "no", ""),
 ("customers_clean", "customer_key", "int32", "Matches transactions_clean.", "clean_data.py", "no", "key"),
 ("customers_clean", "FN", "0|1", "Fashion News flag. Missing in source = 0.", "raw, imputed", "no", ""),
 ("customers_clean", "Active", "0|1", "Active for communication flag. Missing = 0.", "raw, imputed", "no", ""),
 ("customers_clean", "club_member_status", "str", "ACTIVE, PRE-CREATE, LEFT CLUB or UNKNOWN (was missing).", "raw", "no", ""),
 ("customers_clean", "fashion_news_frequency", "str", "NONE, REGULARLY, MONTHLY or UNKNOWN. Case normalised.", "raw", "no", ""),
 ("customers_clean", "age", "float", "Years. Empty if missing in source or >90 (set missing). Under-18s are removed.", "raw", "no", ""),
 ("customers_clean", "age_band", "str", "18-24, 25-34, 35-44, 45-54, 55-64, 65+, unknown.", "derived F6", "no", ""),
 ("customers_clean", "age_raw_missing", "0|1", "Age was missing in source.", "derived", "no", ""),
 ("customers_clean", "age_gt90_set_missing", "0|1", "Age >90 in source, blanked.", "derived", "no", ""),
 ("customers_clean", "units_train", "int", "Units bought in the train window only.", "derived F7", "no (train-only)", ""),
 ("customers_clean", "visits_train", "int", "Distinct purchase days in the train window.", "derived F7", "no (train-only)", ""),
 ("customers_clean", "first_purchase_train", "date", "First purchase date in train window.", "derived F7", "no", ""),
 ("customers_clean", "last_purchase_train", "date", "Last purchase date in train window.", "derived F7", "no", ""),
 ("customers_clean", "has_train_history", "0|1", "Customer bought at least once in train window (0 = cold start).", "derived F7", "no", ""),
 ("customers_clean", "heavy_buyer_flag", "0|1", "units_train above 99.9th percentile. Flag only.", "derived F8", "no", ""),
 ("articles_clean", "article_id ... garment_group_name", "mixed", "All source catalogue columns unchanged (see Kaggle data description).", "raw", "no", ""),
 ("articles_clean", "detail_desc", "str", "Free-text description, empty string if missing in source.", "raw", "no", ""),
 ("articles_clean", "detail_desc_missing", "0|1", "Description was missing in source.", "derived", "no", ""),
 ("articles_clean", "in_scope", "0|1", "0 = Baby/Children or non-apparel group; those articles are excluded from transactions_clean.", "derived", "no", ""),
]
pd.DataFrame(dd, columns=["table", "column", "type", "description", "origin", "leakage_risk", "role"]).to_csv(
    DATA / "data_dictionary.csv", index=False, lineterminator="\n")

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()

files = ["transactions_clean.csv.gz", "customers_clean.csv.gz", "articles_clean.csv.gz", "data_dictionary.csv"]
with open(DATA / "SHA256SUMS.txt", "w", newline="\n") as fh:
    fh.write("".join(f"{sha(DATA / f)}  {f}\n" for f in files))
M["outputs"] = {f: dict(bytes=(DATA / f).stat().st_size, sha256=sha(DATA / f)) for f in files}
M["outputs"]["rows"] = dict(transactions=len(tx_out), customers=len(cu_out), articles=len(ar_out))
M["inputs_sha256"] = {f: sha(RAW / f) for f in ["articles.csv", "customers.csv", "transactions_train_sample10pct.csv"]}
(OUT / "audit_metrics.json").write_text(json.dumps(M, indent=1, default=str))
print("ok", M["clean"])
