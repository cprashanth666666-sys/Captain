# Cells for sections 0-3 (framing, hypotheses, load, clean, representativeness)
from nb_helpers import md, code, cells

md('''# ANCP D3 — Exploratory Data Analysis: Westside Stylist Mirror

**Group M · Module M3 (Exploratory analysis) · Lead: C Prashanth · Linked outcomes: CO2, CO4**

This notebook explores the H&M purchase data (10% customer sample) that serves as our proxy for Westside's purchase history. It follows the D1 charter and the D2 data audit. The order is deliberate: business questions and hypotheses are written **before** any data is loaded, then data is loaded, cleaned and checked for bias, and only then explored.

**How to read it.** Every section ends with a short "so what". The insight log (section 9) collects the findings and the summary page (section 10) says how they shape modelling in M4. A two-page PDF summary is delivered separately.

**Reproducibility.** *Restart & Run All* works. The data folder is found automatically (set the `HM_DATA_DIR` environment variable to override). A small reference file, `reference/full_population_profile.json`, was built once from the full 31.8M-row transaction file by `build_full_population_profile.py`; the notebook uses it to test whether the 10% sample is representative.''')

md('''## 0. Setup''')
code(r'''
import os, json, warnings, math, time
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib as mpl, matplotlib.pyplot as plt
import matplotlib.ticker as mt
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats, sparse

warnings.filterwarnings("ignore")
pd.set_option("display.width", 170); pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
SEED = 42
rng = np.random.default_rng(SEED)
T0 = time.time()

HERE = Path.cwd()
FIG, OUT, REF = HERE / "figures", HERE / "outputs", HERE / "reference"
FIG.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)

def find_data_dir():
    for c in [os.environ.get("HM_DATA_DIR"), r"C:\Users\cpras\Downloads\H&M", str(HERE / "data"), str(HERE.parent / "data")]:
        if c and (Path(c) / "transactions_train_sample10pct.csv").exists():
            return Path(c)
    raise FileNotFoundError("Put the H&M csv files in ./data or set HM_DATA_DIR")
DATA = find_data_dir()

# Colour system: validated categorical order (blue, orange, aqua, yellow, magenta, green, violet, red);
# one-hue blue ramp for magnitude; blue/orange pair with a neutral midpoint for ratios around 1.
C = dict(blue="#2a78d6", orange="#eb6834", aqua="#1baf7a", yellow="#eda100", magenta="#e87ba4",
         green="#008300", violet="#6250d6", red="#e34948", ink="#0b0b0b", ink2="#52514e",
         muted="#898781", grid="#e1e0d9", mid="#f0efec")
SEQ = LinearSegmentedColormap.from_list("blue_seq", ["#e9f2fd", "#9ec5f4", "#3987e5", "#184f95", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("blue_orange", ["#256abf", "#9ec5f4", C["mid"], "#f3b79b", "#c8501f"])
DEPT_COL = {"Ladieswear": C["blue"], "Divided": C["orange"], "Menswear": C["aqua"], "Sport": C["violet"]}

mpl.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 200, "font.size": 10.5, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 10.5, "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"],
    "ytick.color": C["ink2"], "text.color": C["ink"], "axes.edgecolor": C["muted"], "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.7,
    "axes.axisbelow": True, "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.prop_cycle": mpl.cycler(color=[C[k] for k in ["blue", "orange", "aqua", "yellow", "magenta", "green", "violet", "red"]]),
})
KEY = {}   # headline numbers, written to outputs/key_numbers.json for the PDF summary

def save(fig, name):
    fig.text(0.005, -0.035, f"Figure {int(name[3:5])}", fontsize=9, color=C["muted"], ha="left")
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", facecolor="white")
    plt.show()
print("data folder:", DATA)
''')

md('''## 1. Business context, questions and hypotheses (stated before any analysis)

**Decision this EDA supports.** Whether, and how, a Westside "stylist mirror" that reads a member's purchase history and suggests complete outfits is worth building, and what the M4 models (best-seller baseline, recommender, outfit matcher, demand forecast) must handle. The charter's success metrics (MAP@12 against a best-seller baseline, items per bill, fairness across groups, forecast WAPE) are the yardsticks.

**Business questions (BQ)**

| ID | Business question | Why it matters for the decision |
|---|---|---|
| BQ1 | Is there headroom for outfit suggestions: do shoppers buy thin baskets? | Sets the size of the "items per bill" prize. |
| BQ2 | Does a shopper's purchase history carry signal beyond what everyone else is buying? | Decides whether personalisation can beat the best-seller baseline. |
| BQ3 | Can complementary items (top + bottom) be learned from what is bought together? | Decides whether the outfit matcher can start from transaction data. |
| BQ4 | Is demand stable enough to forecast and to make stock-aware suggestions? | Decides how fresh models must be and whether a static best-seller list works. |
| BQ5 | Do customer segments differ, and who are the target-group shoppers? | Sets fairness checks and who the mirror serves best or worst. |

**Hypotheses.** Each has a direction, a decision rule fixed *now* (thresholds are not changed after seeing results), and the business question it informs. "Visit" means one customer on one day. "Unit" is one item bought. The in-scope data is defined in section 3: adult customers, adult departments, apparel and accessories.

| ID | Hypothesis | Linked BQ | Decision rule (supported if…) | Charter metric it informs |
|---|---|---|---|---|
| H1 | Most visits are thin: shoppers rarely buy a top and a bottom together, so completing the outfit is open headroom. | BQ1 | ≥ 50% of visits contain a single unit **and** ≤ 15% of visits contain both a top and a bottom | Items per bill uplift |
| H2 | A shopper's past purchases predict what they buy next far better than chance: they re-buy the same product types and colours. | BQ2 | History hit rate for product type **and** colour is ≥ 1.5× a same-week random baseline | MAP@12 vs best-seller |
| H3 | Complementary pairs exist in the baskets: top–bottom product-type pairs co-occur more than expected after controlling for basket size and week. | BQ3 | Median adjusted lift of top×bottom type pairs ≥ 1.2 | Outfit-matching accuracy |
| H4 | Demand is long-tailed and churns quickly, so a static best-seller list goes stale. | BQ4 | Top 1% of articles hold < 25% of units **and** the week-to-week overlap (Jaccard) of the top-100 articles is < 0.50 | Best-seller baseline, WAPE |
| H5 | Segments differ: the department mix and basket behaviour change with age, so one policy will serve groups unequally. | BQ5 | Cramér's V of age band × department ≥ 0.15 **and** the single-unit share differs by ≥ 5 points between age bands (bands with ≥ 1,000 customers) | Fairness across groups |
| H6 | Purchases are concentrated in a minority of heavy buyers, who therefore dominate any training data. | BQ2, BQ5 | Top 10% of customers account for ≥ 40% of units | Validity (split by person), weighting |
| H7 | Colour choice is concentrated in a few neutrals and shifts with the season. | BQ3, BQ4 | Top 3 master colours ≥ 50% of units **and** the light/bright share differs by ≥ 5 points between summer and winter months | Colour advice, forecast seasonality |

**Open item, not testable here.** The charter's target group ("low-effort, low-confidence dressers") cannot be observed in transaction data. Section 8 builds a behavioural proxy and flags it as a proxy; the shopper survey planned for M3 must confirm it.''')

code(r'''
# Decision thresholds fixed BEFORE the data is loaded (single source of truth for the verdict table in section 8).
THR = dict(
    H1_single_min=0.50, H1_pair_max=0.15,
    H2_ratio_min=1.5,
    H3_lift_min=1.2,
    H4_top1pct_max=0.25, H4_jaccard_max=0.50,
    H5_cramer_min=0.15, H5_gap_min=0.05, H5_min_customers=1000,
    H6_top10_min=0.40,
    H7_top3_min=0.50, H7_season_min=0.05,
)
pd.Series(THR, name="threshold").to_frame()
''')

md('''## 2. Load the data

Three raw files are used: the 10% customer sample of transactions (all purchases of a random 10% of customers), the article catalogue, and the full customer table. Nothing is modified on disk.''')
code(r'''
t = time.time()
art = pd.read_csv(DATA / "articles.csv", dtype={"article_id": str}, usecols=[
    "article_id", "product_type_name", "product_group_name", "perceived_colour_master_name",
    "perceived_colour_value_name", "index_group_name", "garment_group_name"])
cust_all = pd.read_csv(DATA / "customers.csv", usecols=[
    "customer_id", "FN", "Active", "club_member_status", "fashion_news_frequency", "age"])
tx = pd.read_csv(DATA / "transactions_train_sample10pct.csv", parse_dates=["t_dat"],
                 dtype={"article_id": str, "sales_channel_id": "int8", "price": "float32"})
tx["cust"], cust_ids = pd.factorize(tx["customer_id"])
tx = tx.drop(columns="customer_id")
cust_s = pd.DataFrame({"customer_id": cust_ids}).merge(cust_all, on="customer_id", how="left")   # index == tx.cust code
print(f"articles {art.shape} | customers (all) {cust_all.shape} | sampled buyers {cust_s.shape} | transactions {tx.shape}")
print(f"date range {tx.t_dat.min().date()} to {tx.t_dat.max().date()} | loaded in {time.time()-t:.0f}s")
assert tx.article_id.isin(art.article_id).all(), "transactions with unknown article"
assert cust_s.age.notna().sum() > 0
tx.head()
''')

md('''### 2.1 Raw-data quality scan (before any cleaning)

D2 audited the same files; the checks that matter for EDA are repeated here so this notebook stands alone.''')
code(r'''
key_cols = ["t_dat", "cust", "article_id", "price", "sales_channel_id"]
n_raw = len(tx)
n_dup_extra = int(tx.duplicated(key_cols).sum())
raw_scan = pd.DataFrame({
    "check": ["transaction rows", "exact duplicate rows (beyond the first copy)", "missing values in transactions",
              "price min / max (normalised scale)", "customers missing age", "customers with age > 90",
              "customers with age < 18", "customers missing FN flag", "customers missing club status",
              "first / last transaction date"],
    "result": [f"{n_raw:,}", f"{n_dup_extra:,} ({n_dup_extra/n_raw:.1%})", int(tx.isna().sum().sum()),
               f"{tx.price.min():.5f} / {tx.price.max():.3f}",
               f"{cust_s.age.isna().sum():,} ({cust_s.age.isna().mean():.1%})", int((cust_s.age > 90).sum()),
               int((cust_s.age < 18).sum()), f"{cust_s.FN.isna().mean():.1%}",
               f"{cust_s.club_member_status.isna().mean():.1%}", f"{tx.t_dat.min().date()} / {tx.t_dat.max().date()}"],
})
raw_scan
''')

md('''**Cleaning decisions** (each is a judgement; the reason is the test of whether it is right)

| # | Issue found | Decision | Reason |
|---|---|---|---|
| 1 | Exact duplicate rows (same customer, day, article, price, channel) | **Keep, as quantity.** Collapse to one line with `qty` | The file has no quantity column. Identical rows are two units bought together, not a logging error, so dropping them would understate basket size. Units are preserved. |
| 2 | Baby/Children department | **Exclude** from the main frame | The buyer is dressing someone else. Outfit advice for the shopper cannot learn from these purchases. |
| 3 | Non-apparel product groups (cosmetics, furniture, stationery, "Unknown", etc.) | **Exclude** | Not part of an outfit. Under 0.1% of units; checked below. |
| 4 | Customers under 18 | **Exclude** | The charter rules out under-18s for the mirror. |
| 5 | Age > 90 (implausible) | Set age to missing | Likely default values. Customer is kept. |
| 6 | Missing age, FN, Active, club status, news frequency | Age: explicit "unknown" band. FN/Active: missing means 0 (not subscribed). Others: "UNKNOWN" | Imputing age would invent a signal; we test whether missingness itself is informative (section 3.3). |
| 7 | Price is on a normalised scale, not a currency | Use as **relative** price only | Absolute rupee or euro claims would be unfounded. |
| 8 | First and last weeks are partial | Drop partial weeks from **weekly** analyses only | Avoids false dips at the window edges. |
| 9 | `sales_channel_id` is an anonymous code (1 or 2) | Keep as code; do not label "store" or "online" | The data dictionary does not say which is which. The mirror is an in-store device, so this matters (see 3.3). |''')

md('''## 3. Cleaning, and representativeness checks on raw and cleaned data

### 3.1 Build the cleaned frame''')
code(r'''
ROLE = {"Garment Upper body": "Top", "Garment Lower body": "Bottom", "Garment Full body": "Full-body",
        "Accessories": "Accessory", "Bags": "Accessory", "Shoes": "Footwear", "Socks & Tights": "Hosiery",
        "Underwear": "Underwear", "Nightwear": "Nightwear", "Underwear/nightwear": "Nightwear", "Swimwear": "Swimwear"}
ADULT_DEPTS = ["Ladieswear", "Divided", "Menswear", "Sport"]
AGE_BINS = [0, 17, 24, 34, 44, 54, 64, 200]
AGE_LAB = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
BAND_ORDER = AGE_LAB + ["unknown"]

art["role"] = art.product_group_name.map(ROLE)
art_idx = art.set_index("article_id")

def add_age_band(c, age_col):
    return pd.cut(c[age_col], AGE_BINS, labels=AGE_LAB).astype(object).fillna("unknown")

def clean_customers(c):
    c = c.copy()
    c["age_clean"] = c.age.where(c.age <= 90)                  # decision 5
    c["age_band"] = add_age_band(c, "age_clean")
    c["FN"] = c.FN.fillna(0); c["Active"] = c.Active.fillna(0)  # decision 6
    c["club"] = c.club_member_status.fillna("UNKNOWN")
    c["news"] = c.fashion_news_frequency.replace({"None": "NONE"}).fillna("UNKNOWN")
    c["minor"] = c.age < 18                                      # decision 4
    return c

cust_all_c = clean_customers(cust_all)
cust_s_c = clean_customers(cust_s)

# Decision 1: collapse exact duplicates to quantity
lines = tx.groupby(key_cols, sort=False).size().reset_index(name="qty")
lines = lines.merge(art, on="article_id", how="left")

funnel = [("Raw rows (units)", int(n_raw))]
funnel.append(("After collapsing duplicates: lines", len(lines)))
units = lines.qty.sum();                       funnel.append(("Units, all departments", int(units)))
lines = lines[lines.index_group_name.isin(ADULT_DEPTS)];  funnel.append(("Drop Baby/Children (decision 2)", int(lines.qty.sum())))
lines = lines[lines.role.notna()];             funnel.append(("Drop non-apparel groups (decision 3)", int(lines.qty.sum())))
minor_codes = set(cust_s_c.index[cust_s_c.minor])
lines = lines[~lines.cust.isin(minor_codes)];  funnel.append(("Drop under-18 customers (decision 4)", int(lines.qty.sum())))
lines = lines.reset_index(drop=True)
for c_ in ["index_group_name", "product_type_name", "perceived_colour_master_name", "perceived_colour_value_name", "role"]:
    lines[c_] = lines[c_].astype("category")

# visit = one customer on one day; week starts Monday
lines["vid"] = lines.groupby(["cust", "t_dat"], sort=False).ngroup()
lines["week"] = lines.t_dat - pd.to_timedelta(lines.t_dat.dt.dayofweek, unit="D")
first_week = (tx.t_dat.min() + pd.Timedelta(days=6)).normalize()
first_week = first_week - pd.Timedelta(days=first_week.dayofweek)             # first Monday on/after start
last_week = (tx.t_dat.max() - pd.Timedelta(days=6) - pd.Timedelta(days=(tx.t_dat.max() - pd.Timedelta(days=6)).dayofweek))
lines["wk_ok"] = (lines.week >= first_week) & (lines.week <= last_week)
lines["spend"] = lines.price * lines.qty
for r_ in ["Top", "Bottom", "Full-body", "Accessory"]:
    lines["is_" + r_.lower().replace("-body", "")] = (lines.role == r_)

fun = pd.DataFrame(funnel, columns=["step", "units"])
fun["share of raw"] = fun.units / n_raw
display(fun)
print(f"complete weeks used for weekly analyses: {first_week.date()} to {last_week.date()} (week start dates)")
KEY.update(raw_rows=int(n_raw), dup_rows=n_dup_extra, units_in_scope=int(lines.qty.sum()),
           units_dropped_baby=int(funnel[2][1]-funnel[3][1]), n_customers_sample=int(len(cust_s)),
           n_customers_in_scope=int(lines.cust.nunique()))
''')

code(r'''
# Customer-level and visit-level tables
visits = lines.groupby("vid", sort=True).agg(
    cust=("cust", "first"), date=("t_dat", "first"), week=("week", "first"), units=("qty", "sum"),
    n_lines=("qty", "size"), spend=("spend", "sum"), has_top=("is_top", "max"), has_bottom=("is_bottom", "max"),
    has_full=("is_full", "max"), has_acc=("is_accessory", "max"), channel=("sales_channel_id", "first"),
    dept=("index_group_name", "first"), wk_ok=("wk_ok", "first"))
n_types = lines[["vid", "product_type_name"]].drop_duplicates().groupby("vid").size()
visits["n_types"] = n_types.reindex(visits.index).values
visits["single"] = visits.units == 1
visits["pair"] = visits.has_top & visits.has_bottom
visits = visits.join(cust_s_c[["age_band", "club", "news", "FN", "age_clean"]], on="cust")

cust = visits.groupby("cust").agg(n_visits=("units", "size"), units=("units", "sum"), single_share=("single", "mean"),
                                  spend=("spend", "sum"), first=("date", "min"), last=("date", "max"))
cust["n_types"] = lines[["cust", "product_type_name"]].drop_duplicates().groupby("cust").size().reindex(cust.index).values
cust = cust.join(cust_s_c[["age_band", "club", "news", "FN", "age_clean"]])
print(f"visits {len(visits):,} | customers {len(cust):,} | units {int(visits.units.sum()):,} | mean units/visit {visits.units.mean():.2f}")
''')

md('''### 3.2 Representativeness: is the 10% sample like the full population?

Two comparisons, each done on **raw** and on **cleaned** data:

* **Customers.** The 136k sampled buyers against all 1.37M customers in `customers.csv`, on age, club status and newsletter flags. The standardised mean difference (SMD) is used because with these sample sizes p-values flag everything; |SMD| < 0.1 is the usual "balanced" convention.
* **Transactions.** The sample against the full 31.8M-row file (`reference/full_population_profile.json`), on department mix, channel mix, monthly volume profile, purchases per customer and basket size.

Cleaning changes who and what is in scope, so the cleaned comparison is also a check on the **bias introduced by our own filters**.''')

code(r'''
def smd(p1, p2, binary=True, sd1=None, sd2=None):
    if binary:
        return (p1 - p2) / math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2 + 1e-12)
    return (p1 - p2) / math.sqrt((sd1 ** 2 + sd2 ** 2) / 2)

def cust_metrics(c, age_col, bands_col):
    known = c[age_col].notna()
    out = {"mean age (known)": (c[age_col].mean(), c[age_col].std())}
    for b in ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]:
        out[f"age band {b} (share of known age)"] = ((c.loc[known, bands_col] == b).mean(), None)
    out["age unknown"] = ((~known).mean(), None)
    out["club status ACTIVE"] = ((c.club_member_status == "ACTIVE").mean(), None)
    out["newsletter: Regularly"] = ((c.fashion_news_frequency == "Regularly").mean(), None)
    out["FN flag = 1"] = ((c.FN == 1).mean(), None)
    return out

def cust_rep_table(pop, samp, age_col, band_col, label):
    mp, ms = cust_metrics(pop, age_col, band_col), cust_metrics(samp, age_col, band_col)
    rows = []
    for k in mp:
        (a, sa), (b, sb) = mp[k], ms[k]
        s = smd(b, a, binary=sa is None, sd1=sb, sd2=sa)
        rows.append((k, a, b, s, "OK" if abs(s) < 0.1 else "CHECK"))
    return pd.DataFrame(rows, columns=["metric", f"population ({label})", f"sample ({label})", "SMD", "verdict"]).set_index("metric")

# RAW: untouched attributes
cust_all["age_band_raw"] = add_age_band(cust_all, "age"); cust_s["age_band_raw"] = add_age_band(cust_s, "age")
rep_c_raw = cust_rep_table(cust_all, cust_s, "age", "age_band_raw", "raw")

# CLEANED: cleaned attributes, adults only, and sample restricted to buyers still in scope
pop_c = cust_all_c[~cust_all_c.minor]
smp_c = cust_s_c.loc[cust_s_c.index.isin(lines.cust.unique()) & ~cust_s_c.minor]
rep_c_clean = cust_rep_table(pop_c, smp_c, "age_clean", "age_band", "clean")
rep_c = rep_c_raw.join(rep_c_clean, how="outer", lsuffix=" ", rsuffix="  ")
display(rep_c)
KEY["max_abs_smd_cust_raw"] = float(rep_c_raw.SMD.abs().max()); KEY["max_abs_smd_cust_clean"] = float(rep_c_clean.SMD.abs().max())
''')

code(r'''
full = json.loads((REF / "full_population_profile.json").read_text())
fm = pd.DataFrame(full["month_index_group"], columns=["month", "dept", "n"])

# --- department mix and monthly profile
def share(s): return s / s.sum()
# raw: all departments, units = raw rows
raw_dept = share(tx.article_id.map(art_idx.index_group_name).value_counts())
full_dept = share(fm.groupby("dept").n.sum())
# clean: adult departments, apparel only vs full population with Baby/Children removed (apparel filter not available in the reference)
clean_dept = share(lines.groupby("index_group_name").qty.sum())
full_dept_adult = share(fm[fm.dept.isin(ADULT_DEPTS)].groupby("dept").n.sum())
dept_tab = pd.DataFrame({"full (raw)": full_dept, "sample (raw)": raw_dept, "full (adult depts)": full_dept_adult, "sample (clean)": clean_dept}).fillna(0)
dept_tab["gap raw (pp)"] = (dept_tab["sample (raw)"] - dept_tab["full (raw)"]) * 100
dept_tab["gap clean (pp)"] = (dept_tab["sample (clean)"] - dept_tab["full (adult depts)"]) * 100

# --- channel mix (raw only: the reference has no channel-by-department split)
ch_full = share(pd.Series(full["sales_channel"]).rename(int).sort_index())
ch_full.index = ch_full.index.astype(int)
ch_samp = share(tx.sales_channel_id.value_counts()).sort_index()
ch_tab = pd.DataFrame({"full (raw)": ch_full, "sample (raw)": ch_samp}); ch_tab["gap (pp)"] = (ch_tab["sample (raw)"] - ch_tab["full (raw)"]) * 100

# --- monthly volume profile
m_full_raw = share(fm.groupby("month").n.sum())
m_samp_raw = share(tx.t_dat.dt.strftime("%Y-%m").value_counts().sort_index())
m_full_ad = share(fm[fm.dept.isin(ADULT_DEPTS)].groupby("month").n.sum())
m_samp_cl = share(lines.assign(m=lines.t_dat.dt.strftime("%Y-%m")).groupby("m").qty.sum())
mon = pd.DataFrame({"full raw": m_full_raw, "sample raw": m_samp_raw, "full adult": m_full_ad, "sample clean": m_samp_cl})
mon_stats = pd.DataFrame({
    "max monthly share gap (pp)": [(mon["sample raw"] - mon["full raw"]).abs().max() * 100, (mon["sample clean"] - mon["full adult"]).abs().max() * 100],
    "correlation of monthly profiles": [mon[["sample raw", "full raw"]].corr().iloc[0, 1], mon[["sample clean", "full adult"]].corr().iloc[0, 1]]},
    index=["raw", "clean"])

display(dept_tab.round(4)); display(ch_tab.round(4)); display(mon_stats)
''')

code(r'''
# --- purchases per customer and basket size (raw rows; clean uses units on the in-scope frame)
raw_rows_pc = tx.groupby("cust").size()
q = [.1, .25, .5, .75, .9, .99]
rpc = pd.DataFrame({"full (raw)": [full["rows_per_customer_quantiles"][str(x)] for x in q],
                    "sample (raw)": raw_rows_pc.quantile(q).values,
                    "sample (clean, units)": cust.units.quantile(q).values}, index=[f"p{int(x*100)}" for x in q])
rpc.loc["mean"] = [full["rows_per_customer_mean"], raw_rows_pc.mean(), cust.units.mean()]
rpc["gap raw (%)"] = (rpc["sample (raw)"] / rpc["full (raw)"] - 1) * 100

bs_full = pd.Series(full["basket_size_hist"]).astype(float); bs_full.index = bs_full.index.astype(int)
bs_full_share = bs_full / bs_full.sum()
raw_vis = tx.groupby(["cust", "t_dat"]).size()
bs_raw = raw_vis.value_counts().sort_index(); bs_raw_share = bs_raw / bs_raw.sum()
def cap(s, k=5):
    o = s.copy(); o.index = np.minimum(o.index, k); return o.groupby(level=0).sum()
bs_tab = pd.DataFrame({"full (raw)": cap(bs_full_share), "sample (raw)": cap(bs_raw_share),
                       "sample (clean, units)": cap(visits.units.value_counts(normalize=True).sort_index())})
bs_tab.index = [str(i) if i < 5 else "5+" for i in bs_tab.index]; bs_tab.index.name = "items per visit"
bs_tab.loc["mean items/visit"] = [(bs_full * bs_full.index).sum() / bs_full.sum(), raw_vis.mean(), visits.units.mean()]
display(rpc.round(2)); display(bs_tab.round(4))
KEY["single_raw_full"] = float(bs_full_share.loc[1]); KEY["single_raw_sample"] = float(bs_raw_share.loc[1])
KEY["rpc_mean_full"] = float(full["rows_per_customer_mean"]); KEY["rpc_mean_sample"] = float(raw_rows_pc.mean())
''')

code(r'''
# Summary scoreboard: raw vs cleaned, with a verdict per check (tolerance: |SMD|<0.1, share gap <1pp, mean-per-customer gap <5%)
def verdict(ok): return "OK" if ok else "CHECK"
score = pd.DataFrame([
    ("Customer attributes (max |SMD|)", rep_c_raw.SMD.abs().max(), rep_c_clean.SMD.abs().max(),
     verdict(rep_c_raw.SMD.abs().max() < 0.1), verdict(rep_c_clean.SMD.abs().max() < 0.1)),
    ("Department mix (max gap, pp)", dept_tab["gap raw (pp)"].abs().max(), dept_tab["gap clean (pp)"].abs().max(),
     verdict(dept_tab["gap raw (pp)"].abs().max() < 1), verdict(dept_tab["gap clean (pp)"].abs().max() < 1)),
    ("Channel mix (max gap, pp)", ch_tab["gap (pp)"].abs().max(), np.nan, verdict(ch_tab["gap (pp)"].abs().max() < 1), "n/a"),
    ("Monthly profile (max gap, pp)", mon_stats.iloc[0, 0], mon_stats.iloc[1, 0], verdict(mon_stats.iloc[0, 0] < 1), verdict(mon_stats.iloc[1, 0] < 1)),
    ("Purchases per customer, mean (gap %)", abs(rpc.loc["mean", "gap raw (%)"]), np.nan, verdict(abs(rpc.loc["mean", "gap raw (%)"]) < 5), "n/a"),
    ("Single-item visit share (gap, pp)", abs(bs_tab.loc["1", "sample (raw)"] - bs_tab.loc["1", "full (raw)"]) * 100, np.nan,
     verdict(abs(bs_tab.loc["1", "sample (raw)"] - bs_tab.loc["1", "full (raw)"]) * 100 < 1), "n/a"),
], columns=["check", "raw value", "cleaned value", "raw verdict", "cleaned verdict"]).set_index("check")
display(score)
KEY["rep_raw_pass"] = int((score["raw verdict"] == "OK").sum()); KEY["rep_checks"] = int(len(score))
''')

code(r'''
# Figure 1: representativeness at a glance (raw vs full population, and the shift caused by cleaning)
fig, ax = plt.subplots(1, 3, figsize=(15, 4.3), gridspec_kw={"width_ratios": [1.1, 1.3, 1.1]})
# (a) department mix
d = dept_tab[["full (raw)", "sample (raw)"]].copy()
d = d.reindex(["Ladieswear", "Baby/Children", "Divided", "Menswear", "Sport"])
x = np.arange(len(d)); w = 0.38
ax[0].bar(x - w/2, d["full (raw)"] * 100, w, color=C["muted"], label="Full population (31.8M rows)")
ax[0].bar(x + w/2, d["sample (raw)"] * 100, w, color=C["blue"], label="10% sample (3.2M rows)")
ax[0].set_xticks(x); ax[0].set_xticklabels(["Ladies-\nwear", "Baby/\nChildren", "Divided", "Mens-\nwear", "Sport"])
ax[0].set_ylabel("Share of units (%)"); ax[0].set_title("Department mix matches"); ax[0].legend(fontsize=8.5)
# (b) monthly profile
ax[1].plot(pd.to_datetime(mon.index), mon["full raw"] * 100, color=C["muted"], lw=2.2, label="Full population")
ax[1].plot(pd.to_datetime(mon.index), mon["sample raw"] * 100, color=C["blue"], lw=1.6, ls="--", label="10% sample")
ax[1].set_ylabel("Share of all units (%)"); ax[1].set_title("Monthly volume profile matches"); ax[1].legend(fontsize=8.5)
ax[1].xaxis.set_major_formatter(mpl.dates.DateFormatter("%b\n%y")); ax[1].xaxis.set_major_locator(mpl.dates.MonthLocator(interval=4))
# (c) basket size
b = bs_tab.iloc[:5]
x = np.arange(len(b))
ax[2].bar(x - w/2, b["full (raw)"] * 100, w, color=C["muted"], label="Full population")
ax[2].bar(x + w/2, b["sample (raw)"] * 100, w, color=C["blue"], label="10% sample")
ax[2].set_xticks(x); ax[2].set_xticklabels(b.index); ax[2].set_xlabel("Items per customer-day"); ax[2].set_ylabel("Share of visits (%)")
ax[2].set_title("Basket size matches"); ax[2].legend(fontsize=8.5)
fig.suptitle("The 10% customer sample reproduces the full H&M file on department, season and basket size (raw data)", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout(); save(fig, "fig01_representativeness")
''')

code(r'''
# Figure 2: what do OUR cleaning filters change? (who and what is dropped)
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
raw_age = cust_s_c.groupby("age_band").size().reindex(BAND_ORDER).fillna(0)
kept_age = cust.groupby("age_band").size().reindex(BAND_ORDER).fillna(0)
ret = (kept_age / raw_age * 100)
ax[0].bar(range(len(ret)), ret, color=[C["red"] if b == "<18" else C["blue"] for b in ret.index])
for i, v in enumerate(ret): ax[0].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9, color=C["ink2"])
ax[0].set_xticks(range(len(ret))); ax[0].set_xticklabels(ret.index); ax[0].set_ylim(0, 112)
ax[0].set_ylabel("Sampled buyers kept in clean frame (%)"); ax[0].set_xlabel("Age band"); ax[0].set_title("Customers retained, by age band")
# units dropped by department
dd = tx.article_id.map(art_idx.index_group_name).value_counts()
kept = lines.groupby("index_group_name").qty.sum()
dr = pd.DataFrame({"raw": dd, "kept": kept}).fillna(0); dr["share kept"] = dr.kept / dr.raw * 100
dr = dr.reindex(["Ladieswear", "Divided", "Menswear", "Sport", "Baby/Children"])
ax[1].barh(range(len(dr)), dr["share kept"], color=[C["blue"]] * 4 + [C["red"]])
for i, v in enumerate(dr["share kept"]): ax[1].text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9, color=C["ink2"])
ax[1].set_yticks(range(len(dr))); ax[1].set_yticklabels(dr.index); ax[1].invert_yaxis(); ax[1].set_xlim(0, 112)
ax[1].set_xlabel("Units kept in clean frame (%)"); ax[1].set_title("Units retained, by department")
fig.suptitle("Cleaning removes mostly Baby/Children units and the under-18s; adult departments are almost untouched", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.04)
fig.tight_layout(); save(fig, "fig02_cleaning_effect")
KEY["baby_units_share"] = float(dd["Baby/Children"] / dd.sum())
''')

md('''**Reading the checks.** The sample reproduces the full file closely on the dimensions the scoreboard tests, on both raw and cleaned data. The cleaned frame is a deliberate subset (adults, adult departments, apparel), so its shifts are the intended effect of scoping, not sampling error. The remaining bias checks (3.3) are about the population itself and about what the data cannot show.''')

md('''### 3.3 Other bias checks: who is missing, who dominates, what changed in time

These checks ask whether the data can be trusted to represent *Westside's* shoppers, not only whether the sample represents H&M. They are run on the cleaned frame.''')
code(r'''
# (a) Is missing demographic information informative? (missing age / FN flag / club status vs behaviour)
rows = []
def mw(a, b):
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    cles = u.statistic / (len(a) * len(b))      # P(random a > random b)
    return u.pvalue, cles
for label, mask in [("age unknown", cust.age_band == "unknown"), ("FN flag missing/0", cust.FN == 0), ("club status UNKNOWN/PRE-CREATE", cust.club.isin(["UNKNOWN", "PRE-CREATE"]))]:
    a, b = cust.loc[mask, "n_visits"], cust.loc[~mask, "n_visits"]
    p, cles = mw(a, b)
    rows.append((label, int(mask.sum()), mask.mean(), a.median(), b.median(), a.mean(), b.mean(), cles, p))
miss = pd.DataFrame(rows, columns=["group", "customers", "share", "median visits (group)", "median visits (others)",
                                   "mean visits (group)", "mean visits (others)", "P(group > other)", "p-value"]).set_index("group")
display(miss)

# (b) Customer concentration (Lorenz / Gini) on cleaned units, compared with the full file's purchases-per-customer
u = np.sort(cust.units.to_numpy()); cum = np.cumsum(u) / u.sum(); lor_x = np.arange(1, len(u) + 1) / len(u)
gini = 1 - 2 * np.trapz(cum, lor_x) + 1 / len(u)
top10 = u[int(len(u) * 0.9):].sum() / u.sum(); top1 = u[int(len(u) * 0.99):].sum() / u.sum()
bottom50 = u[: int(len(u) * 0.5)].sum() / u.sum()
conc = pd.Series({"Gini of units per customer": gini, "top 1% of customers: share of units": top1,
                  "top 10% of customers: share of units": top10, "bottom 50% of customers: share of units": bottom50,
                  "customers with a single visit": (cust.n_visits == 1).mean(), "customers with >= 4 visits": (cust.n_visits >= 4).mean()})
display(conc.to_frame("value"))
KEY.update(gini=float(gini), top10_units=float(top10), top1_units=float(top1), bottom50_units=float(bottom50),
           one_visit_cust=float((cust.n_visits == 1).mean()))
''')

code(r'''
# (c) Time: volume and channel mix across the window (a structural break would bias a pooled model)
wk = lines[lines.wk_ok].groupby(["week", "index_group_name"]).qty.sum().unstack().fillna(0)
mon_ch = lines.assign(m=lines.t_dat.dt.to_period("M").dt.to_timestamp()).groupby(["m", "sales_channel_id"]).qty.sum().unstack().fillna(0)
ch2_share = mon_ch[2] / mon_ch.sum(axis=1)
pre, post = ch2_share[(ch2_share.index >= "2019-03-01") & (ch2_share.index < "2019-09-01")].mean(), ch2_share[(ch2_share.index >= "2020-03-01") & (ch2_share.index < "2020-09-01")].mean()
vol_pre = wk[(wk.index >= "2019-03-01") & (wk.index < "2019-09-01")].sum(axis=1).mean()
vol_post = wk[(wk.index >= "2020-03-01") & (wk.index < "2020-09-01")].sum(axis=1).mean()
print(f"channel-2 share of units, Mar-Aug 2019: {pre:.1%}  vs  Mar-Aug 2020: {post:.1%}")
print(f"mean weekly units, Mar-Aug 2019: {vol_pre:,.0f}  vs  Mar-Aug 2020: {vol_post:,.0f}  ({vol_post/vol_pre-1:+.1%})")
KEY.update(ch2_pre=float(pre), ch2_post=float(post), vol_2020_vs_2019=float(vol_post / vol_pre - 1))
''')

code(r'''
fig, ax = plt.subplots(1, 3, figsize=(16, 4.4), gridspec_kw={"width_ratios": [1.0, 1.1, 1.2]})
# (a) Lorenz
ax[0].plot(lor_x * 100, cum * 100, color=C["blue"], lw=2.4, label=f"Customers (Gini {gini:.2f})")
ax[0].plot([0, 100], [0, 100], color=C["muted"], lw=1.2, ls="--", label="Equal split")
ax[0].fill_between(lor_x * 100, cum * 100, lor_x * 100, color=C["blue"], alpha=0.08)
ax[0].annotate(f"Top 10% of customers\nbuy {top10:.0%} of units", xy=(90, cum[int(len(u) * .9)] * 100), xytext=(30, 72),
               arrowprops=dict(arrowstyle="->", color=C["ink2"]), fontsize=9.5)
ax[0].set_xlabel("Customers, ranked light to heavy (%)"); ax[0].set_ylabel("Cumulative share of units (%)")
ax[0].set_title("A few heavy buyers dominate"); ax[0].legend(loc="upper left", fontsize=9)
# (b) missingness informativeness
m2 = miss[["median visits (group)", "median visits (others)"]]
x = np.arange(len(m2)); w = 0.38
ax[1].bar(x - w/2, m2.iloc[:, 0], w, color=C["orange"], label="Group (missing/inactive)")
ax[1].bar(x + w/2, m2.iloc[:, 1], w, color=C["blue"], label="All others")
for i, (a, b) in enumerate(zip(m2.iloc[:, 0], m2.iloc[:, 1])):
    ax[1].text(i - w/2, a + .1, f"{a:.0f}", ha="center", fontsize=9); ax[1].text(i + w/2, b + .1, f"{b:.0f}", ha="center", fontsize=9)
ax[1].set_xticks(x); ax[1].set_xticklabels(["Age\nunknown", "FN flag\nmissing", "Club status\nunknown/pre-create"], fontsize=9)
ax[1].set_ylabel("Median visits per customer"); ax[1].set_title("Is missingness informative?"); ax[1].legend(fontsize=9)
# (c) weekly volume and channel mix, two stacked panels (no dual axis)
sub = ax[2].get_subplotspec().subgridspec(2, 1, hspace=0.12); ax[2].remove()
tot = wk.sum(axis=1)
a_top = fig.add_subplot(sub[0]); a_bot = fig.add_subplot(sub[1], sharex=a_top)
a_top.plot(tot.index, tot / 1000, color=C["blue"], lw=1.8); a_top.set_ylim(0); a_top.set_ylabel("Units/week (000s)")
a_bot.plot(ch2_share.index + pd.Timedelta(days=14), ch2_share * 100, color=C["orange"], lw=2, marker="o", ms=3.5)
a_bot.set_ylabel("Channel-2 share (%)"); a_bot.set_ylim(0, 100)
for a_ in (a_top, a_bot): a_.axvline(pd.Timestamp("2020-03-11"), color=C["muted"], ls=":", lw=1.4)
a_top.text(pd.Timestamp("2020-03-20"), tot.max() / 1000 * 0.08, "Mar 2020: COVID-19\nlockdowns begin in Europe", fontsize=8.5, color=C["ink2"])
plt.setp(a_top.get_xticklabels(), visible=False); a_bot.xaxis.set_major_formatter(mpl.dates.DateFormatter("%b %y"))
a_top.set_title("A structural break in 2020")
fig.suptitle("Bias checks on the cleaned data: heavy-buyer dominance, informative missingness and a 2020 break", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout(); save(fig, "fig03_bias_checks")
''')

md('''**Coverage gaps the sample cannot fix** (documented, not testable here)

| Gap | Why it matters for Westside | Mitigation |
|---|---|---|
| No gender or size field; department is the only proxy for who wears the item | Mirror advice and fairness checks by gender cannot be computed from purchases | Use department as a labelled proxy; fairness by gender is tested in M5 on volunteer data |
| H&M customers, European assortment, European age mix | Westside sells in India, with Indian wear and a different price ladder | Treat results as patterns to re-validate on Westside data (charter limitation) |
| No store or stock field | Stock-aware suggestions and transfers cannot be learned here | Simulated in M6 (charter) |
| Price is normalised | No rupee claims | Relative price only |
| `sales_channel_id` unlabelled | We cannot tell which channel is in-store | Do not draw in-store conclusions from channel |
| Purchases only: no browsing, no returns | A purchase is a weak proxy for liking an item | Returns and try-on signals come from the mirror itself (charter) |''')
