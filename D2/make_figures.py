"""Figures for the D2 audit report. Usage: python -I make_figures.py  (run from D2/, after clean_data.py)"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
M = json.loads((HERE / "audit_metrics.json").read_text())
D = HERE / "data-v1.0"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

BLUE, ORANGE, INK, INK2, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
mpl.rcParams.update({"font.family": "Times New Roman", "font.size": 9.5, "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": .6, "axes.axisbelow": True, "legend.frameon": False})

# ---- Figure 1: quality audit
tx = pd.read_csv(D / "transactions_clean.csv.gz", usecols=["price_rel"])
cu = pd.read_csv(D / "customers_clean.csv.gz", usecols=["units_train"])
C = M["clean"]
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.45), gridspec_kw={"width_ratios": [1.15, 1, 1]})
labels = ["Raw units", "less Baby/\nChildren", "less non-\napparel", "less under-\n18 buyers"]
vals = [C["units_raw"], C["units_raw"] - C["units_out_of_scope_baby"],
        C["units_after_scope"], C["units_final"]]
bars = ax[0].bar(range(4), vals, color=[MUTED, BLUE, BLUE, BLUE], width=.62)
ax[0].bar(3, vals[3], color=ORANGE, width=.62)
for i, v in enumerate(vals):
    ax[0].text(i, v + 60000, f"{v/1e6:.3f}M", ha="center", fontsize=7.5, color=INK)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(labels, fontsize=7)
ax[0].set_ylim(0, 3.7e6); ax[0].set_yticks([]); ax[0].set_title("a  Units kept at each filter")
ax[0].grid(False); ax[0].spines["left"].set_visible(False)
r = np.log10(tx.price_rel.dropna().to_numpy())
ax[1].hist(r, bins=90, range=(-1.5, 1.5), color=BLUE, linewidth=0)
for x, t in [(np.log10(1 / 3), "×1/3"), (np.log10(3), "×3")]:
    ax[1].axvline(x, color=ORANGE, lw=1.2); ax[1].text(x, ax[1].get_ylim()[1] * .93, t, color=ORANGE, ha="center", fontsize=7.5,
                                                         bbox=dict(fc="white", ec="none", pad=1))
ax[1].set_xticks([-1, 0, 1]); ax[1].set_xticklabels(["0.1×", "1×", "10×"])
ax[1].set_yticks([]); ax[1].set_title("b  Price vs article median"); ax[1].set_xlabel("price / train-window median", fontsize=7.5)
ax[1].grid(False); ax[1].spines["left"].set_visible(False)
u = cu.units_train[cu.units_train > 0]
ax[2].hist(np.log10(u), bins=60, color=BLUE, linewidth=0)
cut = M["features"]["heavy_buyer_cut"]
ax[2].axvline(np.log10(cut), color=ORANGE, lw=1.2)
ax[2].text(np.log10(cut) - .05, ax[2].get_ylim()[1] * .9, f"99.9th pct\n{cut:.0f} units", color=ORANGE, ha="right", fontsize=7.5)
ax[2].set_xticks([0, 1, 2, 3]); ax[2].set_xticklabels(["1", "10", "100", "1,000"])
ax[2].set_yticks([]); ax[2].set_title("c  Units per customer"); ax[2].set_xlabel("units in train window (log scale)", fontsize=7.5)
ax[2].grid(False); ax[2].spines["left"].set_visible(False)
fig.tight_layout(w_pad=1.2)
fig.savefig(FIG / "fig1_quality.png", dpi=220, facecolor="white")

# ---- Figure 2: representativeness
R = M["rep"]
bandmap = {"(17, 24]": "18-24", "(24, 34]": "25-34", "(34, 44]": "35-44", "(44, 54]": "45-54", "(54, 64]": "55-64", "(64, 200]": "65+"}
bands = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
rest = {bandmap[k]: v for k, v in R["age_band_rest"].items() if k in bandmap}
rs = sum(rest.values())
art = pd.read_csv(D / "articles_clean.csv.gz", usecols=["index_group_name", "in_scope"])
cat = art[art.in_scope == 1].index_group_name.value_counts(normalize=True)
groups = ["Ladieswear", "Divided", "Menswear", "Sport"]
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.5), gridspec_kw={"width_ratios": [1, 1, 1.15]})
x = np.arange(len(bands)); w = .38
ax[0].bar(x - w / 2, [R["age_band_sample"][b] * 100 for b in bands], w, color=BLUE, label="Sample buyers")
ax[0].bar(x + w / 2, [rest[b] / rs * 100 for b in bands], w, color=ORANGE, label="Other customers")
ax[0].set_xticks(x); ax[0].set_xticklabels(bands, fontsize=6.3); ax[0].set_ylabel("% of customers", fontsize=7.5); ax[0].set_ylim(0, 40)
ax[0].set_title("a  Age mix: sample vs rest"); ax[0].legend(fontsize=6.3, loc="upper right")
x = np.arange(len(groups))
ax[1].bar(x - w / 2, [cat[g] * 100 for g in groups], w, color=MUTED, label="Catalogue")
ax[1].bar(x + w / 2, [R["units_by_index_group"][g] * 100 for g in groups], w, color=BLUE, label="Units sold")
ax[1].set_xticks(x); ax[1].set_xticklabels(["Ladies", "Divided", "Men", "Sport"], fontsize=6.8); ax[1].set_ylabel("%", fontsize=7.5); ax[1].set_ylim(0, 95)
ax[1].set_title("b  Department mix"); ax[1].legend(fontsize=6.3, loc="upper right")
mon = pd.Series(R["units_by_month"]); idx = pd.to_datetime(mon.index + "-01")
ax[2].plot(idx, mon.values / 1000, color=BLUE, lw=1.6)
ax[2].scatter([idx[0], idx[-1]], [mon.iloc[0] / 1000, mon.iloc[-1] / 1000], s=18, facecolor="white", edgecolor=BLUE, zorder=3)
ax[2].axvspan(pd.Timestamp("2020-03-01"), idx[-1], color=GRID, alpha=.6, lw=0)
ax[2].text(pd.Timestamp("2020-03-10"), 178, "2020 break", fontsize=7, color=INK2)
ax[2].set_ylabel("units (thousand)", fontsize=7.5); ax[2].set_title("c  Units per month")
ax[2].xaxis.set_major_formatter(mpl.dates.DateFormatter("%b\n%y")); ax[2].xaxis.set_major_locator(mpl.dates.MonthLocator([1, 7]))
ax[2].tick_params(axis="x", labelsize=7)
fig.tight_layout(w_pad=1.0)
fig.savefig(FIG / "fig2_representativeness.png", dpi=220, facecolor="white")
print("figures ok")
