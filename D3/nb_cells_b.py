# Cells for sections 4-8 (distributions, relationships, demand, segments, verdicts)
from nb_helpers import md, code

md('''## 4. Distributions

How big are baskets, how often do people shop, who are they, and what do items cost? All on the cleaned frame.''')
code(r'''
def ratio_ci(cust_codes, num, den, n_boot=300, seed=SEED):
    # Cluster bootstrap by customer for sum(num)/sum(den): visits of one customer are not independent.
    df = pd.DataFrame({"c": np.asarray(cust_codes), "n": np.asarray(num, float), "d": np.asarray(den, float)}).groupby("c").sum()
    n, d = df.n.to_numpy(), df.d.to_numpy(); m = len(df); r = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        j = r.integers(0, m, m); bs[i] = n[j].sum() / d[j].sum()
    return n.sum() / d.sum(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)

fig, ax = plt.subplots(2, 2, figsize=(13, 8.4))
# (a) visits per customer
bins = np.unique(np.round(np.logspace(0, np.log10(cust.n_visits.max() + 1), 32)))
ax[0, 0].hist(cust.n_visits, bins=bins, color=C["blue"], edgecolor="white", lw=0.4)
ax[0, 0].set_xscale("log"); ax[0, 0].axvline(cust.n_visits.median(), color=C["ink2"], ls="--", lw=1.2)
ax[0, 0].text(cust.n_visits.median() * 1.15, ax[0, 0].get_ylim()[1] * 0.9, f"median {cust.n_visits.median():.0f} visits", fontsize=9.5, color=C["ink2"])
ax[0, 0].set_xlabel("Visits (customer-days) per customer, log scale"); ax[0, 0].set_ylabel("Customers")
ax[0, 0].set_title("Most customers shop rarely; a long tail shops often")
# (b) units per visit
ub = visits.units.clip(upper=6).value_counts(normalize=True).sort_index() * 100
ax[0, 1].bar(range(len(ub)), ub.values, color=C["blue"])
for i, v in enumerate(ub.values): ax[0, 1].text(i, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9.5)
ax[0, 1].set_xticks(range(len(ub))); ax[0, 1].set_xticklabels([str(int(i)) if i < 6 else "6+" for i in ub.index])
ax[0, 1].set_xlabel("Units bought per visit"); ax[0, 1].set_ylabel("Share of visits (%)"); ax[0, 1].set_title("Baskets are thin")
# (c) age
ages = cust.age_clean.dropna()
ax[1, 0].hist(ages, bins=np.arange(16, 92, 2), color=C["blue"], edgecolor="white", lw=0.4)
ax[1, 0].axvline(ages.median(), color=C["ink2"], ls="--", lw=1.2); ax[1, 0].text(ages.median() + 1, ax[1, 0].get_ylim()[1] * 0.92, f"median {ages.median():.0f}", fontsize=9.5, color=C["ink2"])
ax[1, 0].set_xlabel("Age (years, known ages only)"); ax[1, 0].set_ylabel("Customers"); ax[1, 0].set_title("Young adults dominate the customer base")
# (d) price by role
order = ["Top", "Bottom", "Full-body", "Accessory", "Footwear", "Underwear"]
samp = lines.sample(400_000, random_state=SEED)
data_ = [samp.loc[samp.role == r_, "price"].to_numpy() * 1000 for r_ in order]
ax[1, 1].boxplot(data_, whis=(5, 95), showfliers=False, patch_artist=True, medianprops=dict(color=C["ink"], lw=1.5),
                 boxprops=dict(facecolor="#9ec5f4", edgecolor=C["blue"]), whiskerprops=dict(color=C["blue"]), capprops=dict(color=C["blue"]))
ax[1, 1].set_yscale("log"); ax[1, 1].set_xticklabels(order, fontsize=9.5)
ax[1, 1].set_ylabel("Relative price (normalised ×1000, log scale)"); ax[1, 1].set_title("Price ladder by item role")
fig.suptitle("Typical shopper: young, buys one or two items, a handful of times", x=0.01, ha="left", fontsize=13.5, fontweight="bold", y=1.0)
fig.tight_layout(); save(fig, "fig04_distributions")
desc = pd.DataFrame({"visits per customer": cust.n_visits.describe(), "units per visit": visits.units.describe(), "age": ages.describe()})
display(desc.round(2))
KEY.update(median_visits=float(cust.n_visits.median()), mean_units_visit=float(visits.units.mean()), median_age=float(ages.median()))
''')
md('''**So what.** Half of customers buy on only a few days and the basket is small. A mirror is used at the moment of a visit, so the typical interaction has little history behind it and one or two items in hand. That affects how much a personalised model can know at the mirror, tested next.''')

md('''## 5. Relationships: baskets, history signal and complementary items

### 5.1 H1: How thin are the baskets, and is the outfit incomplete?''')
code(r'''
# Mutually exclusive visit types
vt = np.select([visits.pair, visits.single], ["Top + bottom together", "Single unit"], default="Several units, no top+bottom pair")
vt = pd.Series(vt, index=visits.index)
p_single, lo_s, hi_s = ratio_ci(visits.cust, visits.single, np.ones(len(visits)))
p_pair, lo_p, hi_p = ratio_ci(visits.cust, visits.pair, np.ones(len(visits)))
# Among visits that contain any garment, how complete is the outfit?
g = visits[visits.has_top | visits.has_bottom | visits.has_full]
comp = np.select([g.has_full | (g.has_top & g.has_bottom), g.has_top & ~g.has_bottom, g.has_bottom & ~g.has_top],
                 ["Complete (top+bottom or full-body)", "Top only", "Bottom only"], default="Other")
comp = pd.Series(comp).value_counts(normalize=True)
print(f"single-unit visits: {p_single:.1%} (95% CI {lo_s:.1%}-{hi_s:.1%})")
print(f"visits with a top AND a bottom: {p_pair:.1%} (95% CI {lo_p:.1%}-{hi_p:.1%})")
display(comp.to_frame("share of garment visits"))
fig, ax = plt.subplots(1, 2, figsize=(13, 3.9), gridspec_kw={"width_ratios": [1, 1]})
v = vt.value_counts(normalize=True).reindex(["Single unit", "Several units, no top+bottom pair", "Top + bottom together"]) * 100
ax[0].barh(range(3), v.values, color=[C["blue"], "#9ec5f4", C["orange"]])
for i, x_ in enumerate(v.values): ax[0].text(x_ + 1, i, f"{x_:.0f}%", va="center", fontsize=10)
ax[0].set_yticks(range(3)); ax[0].set_yticklabels(v.index); ax[0].invert_yaxis(); ax[0].set_xlim(0, 100)
ax[0].set_xlabel("Share of visits (%)"); ax[0].set_title("What a visit contains")
c2 = comp.reindex(["Complete (top+bottom or full-body)", "Top only", "Bottom only"]).fillna(0) * 100
ax[1].barh(range(3), c2.values, color=[C["orange"], C["blue"], "#9ec5f4"])
for i, x_ in enumerate(c2.values): ax[1].text(x_ + 1, i, f"{x_:.0f}%", va="center", fontsize=10)
ax[1].set_yticks(range(3)); ax[1].set_yticklabels(c2.index); ax[1].invert_yaxis(); ax[1].set_xlim(0, 100)
ax[1].set_xlabel("Share of visits that include a garment (%)"); ax[1].set_title("How complete the outfit is")
fig.suptitle(f"{p_single:.0%} of visits are a single unit; only {p_pair:.0%} pair a top with a bottom", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.04)
fig.tight_layout(); save(fig, "fig05_basket_composition")
KEY.update(p_single=float(p_single), p_single_lo=float(lo_s), p_single_hi=float(hi_s), p_pair=float(p_pair), p_pair_lo=float(lo_p), p_pair_hi=float(hi_p),
           top_only=float(comp.get("Top only", 0)), bottom_only=float(comp.get("Bottom only", 0)), complete=float(comp.get("Complete (top+bottom or full-body)", 0)))
''')

md('''### 5.2 H2: Does purchase history predict the next purchase?

For every item bought after a customer's first visit, we ask: had this customer already bought the same article, product type, colour or department before that day? The **random baseline** shuffles the attribute among items bought in the *same week*, so it keeps seasonality and popularity but breaks the link to the customer. A ratio well above 1 means history carries information that a best-seller list cannot.''')
code(r'''
day = lines.t_dat.values.astype("datetime64[D]").astype(np.int64)
cust_a = lines.cust.to_numpy().astype(np.int64)
first_day = pd.Series(day).groupby(cust_a).transform("min").to_numpy()
elig = day > first_day                              # items bought after the customer's first day
week_idx = lines.groupby("week").indices            # week -> row positions

def hist_hit_rates(col, n_shuf=3):
    code_ = pd.factorize(lines[col])[0].astype(np.int64); K = int(code_.max()) + 1
    fs = pd.Series(day).groupby(cust_a * K + code_).min()     # first day the customer bought this attribute value
    def hit(codes_): return fs.reindex(cust_a * K + codes_).to_numpy() < day
    real = hit(code_)[elig].mean()
    base = []
    for _ in range(n_shuf):
        sh = code_.copy()
        for w, idx in week_idx.items(): sh[idx] = rng.permutation(code_[idx])
        base.append(hit(sh)[elig].mean())
    return real, float(np.mean(base))

t = time.time()
hist = pd.DataFrame([(name, *hist_hit_rates(col)) for name, col in [
    ("Exact article (repeat purchase)", "article_id"), ("Product type", "product_type_name"),
    ("Colour (master)", "perceived_colour_master_name"), ("Department", "index_group_name")]],
    columns=["attribute", "hit rate (history)", "hit rate (random, same week)"]).set_index("attribute")
hist["ratio"] = hist.iloc[:, 0] / hist.iloc[:, 1]
display(hist); print(f"items evaluated: {int(elig.sum()):,}  ({time.time()-t:.0f}s)")
KEY["hist"] = {k: dict(real=float(r["hit rate (history)"]), base=float(r["hit rate (random, same week)"]), ratio=float(r["ratio"])) for k, r in hist.iterrows()}
KEY["items_eval"] = int(elig.sum())

fig, ax = plt.subplots(figsize=(9.5, 3.8))
y = np.arange(len(hist))[::-1]
for yi, (k, r) in zip(y, hist.iterrows()):
    ax.plot([r.iloc[1] * 100, r.iloc[0] * 100], [yi, yi], color=C["muted"], lw=2.5, zorder=1)
    ax.scatter(r.iloc[1] * 100, yi, s=90, color=C["muted"], zorder=2); ax.scatter(r.iloc[0] * 100, yi, s=90, color=C["blue"], zorder=2)
    ax.text(r.iloc[0] * 100 * 1.12, yi, f"{r.iloc[0]:.0%} vs {r.iloc[1]:.0%}  ({r['ratio']:.1f}×)", va="center", fontsize=9.5)
ax.set_yticks(y); ax.set_yticklabels(hist.index); ax.set_xscale("log"); ax.set_xlim(0.5, 400)
ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}%")); ax.set_xlabel("Share of later purchases already seen in the customer's own history (log scale)")
ax.scatter([], [], color=C["blue"], label="Customer's actual history"); ax.scatter([], [], color=C["muted"], label="Random items from the same week"); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=9)
ax.set_title("A customer's own history beats a same-week random draw on every attribute")
fig.tight_layout(); save(fig, "fig06_history_signal")
''')
md('''**So what.** Where the ratio is far above 1, a model that reads the member's history has real information to work with that a best-seller list lacks. Where the baseline hit rate is already high (department, product type), the gain over chance is small in absolute terms because the choice set is small; the useful signal is at the finer levels (colour, exact article).''')

md('''### 5.3 H3: Which product types are bought together?

Raw co-occurrence is misleading: big baskets contain everything. The **adjusted lift** divides the observed number of visits containing both types by the number expected when the same items are shuffled among visits of the same size and week (average of 5 shuffles). Lift above 1 means the pair is bought together more than basket size and season explain. The unit is the distinct product type within a visit, and only visits with two or more distinct types are used.''')
code(r'''
t = time.time()
# Unit of analysis: distinct product types within a visit (a visit with three T-shirts counts T-shirt once),
# so the shuffle keeps each visit's number of distinct types and the null is not distorted by repeated types.
L2 = lines[["vid", "week", "product_type_name", "role"]].drop_duplicates(["vid", "product_type_name"]).reset_index(drop=True)
L2["vsize"] = L2.groupby("vid").vid.transform("size")
L2 = L2[L2.vsize >= 2].reset_index(drop=True)
ptc, ptu = pd.factorize(L2.product_type_name)
L2["ptc"] = ptc
vis_per_type = L2[["vid", "ptc"]].drop_duplicates().ptc.value_counts()
topK = vis_per_type.index[:16].to_numpy(); K = len(topK)
type_role = L2.groupby("ptc").role.agg(lambda s: s.value_counts().index[0])
role_order = {"Top": 0, "Bottom": 1, "Full-body": 2, "Footwear": 3, "Accessory": 4}
topK = sorted(topK, key=lambda t_: (role_order.get(type_role[t_], 9), -vis_per_type[t_]))
pos = {t_: i for i, t_ in enumerate(topK)}
vcode = pd.factorize(L2.vid)[0]; nv = vcode.max() + 1

def cooc(types_):
    m = np.isin(types_, topK)
    X = sparse.coo_matrix((np.ones(m.sum(), np.float32), (vcode[m], np.array([pos[t_] for t_ in types_[m]]))), shape=(nv, K)).tocsr()
    X.data[:] = 1
    M = (X.T @ X).toarray(); np.fill_diagonal(M, 0); return M

obs = cooc(ptc)
strata = L2.assign(vb=L2.vsize.clip(upper=6)).groupby(["week", "vb"]).indices
shuf = []
for _ in range(5):
    sh = ptc.copy()
    for idx in strata.values(): sh[idx] = rng.permutation(ptc[idx])
    shuf.append(cooc(sh))
exp_ = np.mean(shuf, axis=0)
lift = np.where(exp_ > 0, obs / np.maximum(exp_, 1e-9), np.nan)
names = [ptu[t_] for t_ in topK]; roles_ = [type_role[t_] for t_ in topK]
lift_df = pd.DataFrame(lift, index=names, columns=names); obs_df = pd.DataFrame(obs, index=names, columns=names)

tb = [(i, j) for i in range(K) for j in range(i + 1, K) if {roles_[i], roles_[j]} == {"Top", "Bottom"}]
tt = [(i, j) for i in range(K) for j in range(i + 1, K) if roles_[i] == roles_[j] == "Top"]
lift_tb = np.array([lift[i, j] for i, j in tb]); lift_tt = np.array([lift[i, j] for i, j in tt])
print(f"top x bottom pairs: n={len(tb)}, median adjusted lift {np.median(lift_tb):.2f}, share with lift>=1.2: {(lift_tb>=1.2).mean():.0%}")
print(f"top x top pairs   : n={len(tt)}, median adjusted lift {np.median(lift_tt):.2f}")
pairs = pd.DataFrame([(names[i], names[j], roles_[i] + " x " + roles_[j], lift[i, j], int(obs[i, j])) for i in range(K) for j in range(i + 1, K)],
                     columns=["type A", "type B", "roles", "adjusted lift", "visits together"])
display(pairs[pairs["visits together"] >= 200].sort_values("adjusted lift", ascending=False).head(10).reset_index(drop=True))
KEY.update(lift_tb_median=float(np.median(lift_tb)), lift_tb_n=len(tb), lift_tb_share12=float((lift_tb >= 1.2).mean()), lift_tt_median=float(np.median(lift_tt)),
           top_pairs=pairs[pairs["visits together"] >= 200].sort_values("adjusted lift", ascending=False).head(5).values.tolist())
print(f"({time.time()-t:.0f}s)")
''')
code(r'''
fig, ax = plt.subplots(figsize=(10.5, 8.2))
Z = np.log2(np.where(np.isnan(lift), 1, lift)); np.fill_diagonal(Z, np.nan)
im = ax.imshow(Z, cmap=DIV, vmin=-1.5, vmax=1.5)
ax.set_xticks(range(K)); ax.set_yticks(range(K)); ax.set_xticklabels([f"{n}" for n in names], rotation=60, ha="right", fontsize=9); ax.set_yticklabels(names, fontsize=9)
ax.grid(False)
for i in range(K):
    for j in range(K):
        if i != j and not np.isnan(lift[i, j]): ax.text(j, i, f"{lift[i, j]:.1f}", ha="center", va="center", fontsize=7.5, color=C["ink"] if abs(Z[i, j]) < 1.0 else "white")
# role separators
cuts = [i for i in range(1, K) if roles_[i] != roles_[i - 1]]
for c_ in cuts: ax.axhline(c_ - .5, color=C["ink2"], lw=1); ax.axvline(c_ - .5, color=C["ink2"], lw=1)
cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02); cb.set_ticks([-1.5, -1, 0, 1, 1.5]); cb.set_ticklabels(["0.35×", "0.5×", "1× (chance)", "2×", "2.8×"])
cb.set_label("Adjusted lift vs shuffled baskets")
ax.set_title("Types bought together: orange = more than chance, blue = less", fontsize=12)
fig.tight_layout(); save(fig, "fig07_pair_lift")
''')
md('''**So what.** This is the evidence base for the outfit matcher. Pairs with high adjusted lift are candidate "goes with" rules the model can learn from purchases alone. Pairs of the *same* role (two tops) show whether shoppers buy alternatives or duplicates; an outfit model should not suggest them together unless the lift supports it.''')

md('''## 6. Demand over time: seasonality, concentration and churn (H4)

Weekly analyses use complete weeks only. Because the sample holds 10% of customers, weekly counts for a single article are noisy; a **split-half ceiling** (two random halves of the customers compared in the same week) shows how much overlap sampling noise alone would allow.''')
code(r'''
lw = lines[lines.wk_ok]
weeks = sorted(lw.week.unique())
aw = lw.groupby(["week", "article_id"]).qty.sum()
wk_ser = {w: s.droplevel(0).sort_values(ascending=False) for w, s in aw.groupby(level=0)}

# (a) concentration of units over articles
au = lines.groupby("article_id").qty.sum().sort_values(ascending=False); cum_a = au.cumsum() / au.sum()
n_art = len(au); top1_art = cum_a.iloc[int(n_art * 0.01) - 1]; top10_art = cum_a.iloc[int(n_art * 0.10) - 1]
n50 = int((cum_a < 0.5).sum() + 1)
print(f"articles sold: {n_art:,} | top 1% hold {top1_art:.1%} of units | top 10% hold {top10_art:.1%} | {n50:,} articles ({n50/n_art:.1%}) make half of units")

# (b) coverage of next week's units by last week's top-K
Ks = [12, 100, 500]
cov = {k: [] for k in Ks}
for a_, b_ in zip(weeks[:-1], weeks[1:]):
    prev, cur = wk_ser[a_], wk_ser[b_]
    for k in Ks: cov[k].append(cur.reindex(prev.index[:k]).fillna(0).sum() / cur.sum())
cov = pd.DataFrame(cov, index=weeks[1:])

# (c) overlap of the top-100 between weeks, by lag; split-half noise ceiling
def jac(a, b): a, b = set(a), set(b); return len(a & b) / len(a | b)
jl = {}
for lag in [1, 4, 13, 52]:
    jl[lag] = np.mean([jac(wk_ser[weeks[i]].index[:100], wk_ser[weeks[i + lag]].index[:100]) for i in range(len(weeks) - lag)])
half = pd.Series(rng.integers(0, 2, lines.cust.max() + 1), name="half")
lwh = lw.assign(h=half.reindex(lw.cust).to_numpy())
cei = []
for w, g in lwh.groupby("week"):
    a_ = g[g.h == 0].groupby("article_id").qty.sum().nlargest(100).index; b_ = g[g.h == 1].groupby("article_id").qty.sum().nlargest(100).index
    cei.append(jac(a_, b_))
ceiling = float(np.mean(cei))
print("top-100 Jaccard by lag (weeks):", {k: round(v, 3) for k, v in jl.items()}, "| same-week split-half ceiling:", round(ceiling, 3))
print("last-week top-K covers next week's units (mean):", {k: f"{cov[k].mean():.1%}" for k in Ks})

# (d) novelty and lifespan
first_wk = lw.groupby("article_id").week.min(); last_wk = lw.groupby("article_id").week.max()
lw2 = lw.assign(age_w=((lw.week - lw.article_id.map(first_wk)).dt.days // 7))
nov = (lw2[lw2.age_w <= 8].groupby("week").qty.sum() / lw2.groupby("week").qty.sum()).reindex(weeks).fillna(0)
nov = nov.iloc[26:]
art_tot = lw.groupby("article_id").qty.sum()
cand = first_wk[(first_wk >= weeks[8]) & (first_wk <= weeks[52]) & (art_tot.reindex(first_wk.index) >= 5)]
span = ((last_wk.reindex(cand.index) - cand).dt.days // 7)
print(f"articles launched in weeks 9-53 with >=5 units: {len(cand):,} | median span {span.median():.0f} weeks | still selling 26+ weeks later: {(span>=26).mean():.0%}")
print(f"share of weekly units from articles first sold <= 8 weeks earlier (weeks 27+): mean {nov.mean():.1%}")
KEY.update(top1_art=float(top1_art), top10_art=float(top10_art), n_art=int(n_art), n50=n50, cov12=float(cov[12].mean()), cov100=float(cov[100].mean()), cov500=float(cov[500].mean()),
           jac1=float(jl[1]), jac4=float(jl[4]), jac13=float(jl[13]), jac52=float(jl[52]), jac_ceiling=ceiling, novelty=float(nov.mean()), span_med=float(span.median()), span26=float((span >= 26).mean()))
''')
code(r'''
# Weekly units by department: small multiples, one colour per department (own y-scale; shape is what matters)
fig, axs = plt.subplots(2, 2, figsize=(13, 6.8), sharex=True)
for a_, d_ in zip(axs.ravel(), ["Ladieswear", "Divided", "Menswear", "Sport"]):
    s = wk[d_] / 1000
    a_.plot(s.index, s.values, color=DEPT_COL[d_], lw=1.8); a_.set_ylim(0); a_.set_title(d_, fontsize=11.5); a_.set_ylabel("Units per week (000s)")
    pk = s.idxmax(); a_.annotate(f"peak {pk:%d %b %y}", xy=(pk, s.max()), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5, color=C["ink2"])
    a_.axvline(pd.Timestamp("2020-03-11"), color=C["muted"], ls=":", lw=1.2)
    a_.xaxis.set_major_formatter(mpl.dates.DateFormatter("%b %y"))
fig.suptitle("Weekly demand is strongly seasonal in every department (dotted line: Mar 2020)", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.0)
fig.tight_layout(); save(fig, "fig08_weekly_by_dept")
mw_ = wk["Menswear"]; KEY["menswear_cv"] = float(mw_.std() / mw_.mean()); KEY["all_cv"] = float(wk.sum(axis=1).std() / wk.sum(axis=1).mean())
KEY["menswear_share_units"] = float(lines.loc[lines.index_group_name == "Menswear", "qty"].sum() / lines.qty.sum())
''')
code(r'''
fig, ax = plt.subplots(1, 3, figsize=(16, 4.5), gridspec_kw={"width_ratios": [1.05, 1.25, 1]})
# (a) Pareto
xs = np.arange(1, n_art + 1) / n_art * 100
ax[0].plot(xs, cum_a.values * 100, color=C["blue"], lw=2.4)
for p_, v_ in [(1, top1_art), (10, top10_art)]:
    ax[0].scatter([p_], [v_ * 100], color=C["orange"], zorder=3, s=45); ax[0].annotate(f"top {p_}% of articles\n= {v_:.0%} of units", xy=(p_, v_ * 100), xytext=(p_ + 12, v_ * 100 - 14), fontsize=9.5, arrowprops=dict(arrowstyle="-", color=C["muted"]))
ax[0].set_xlabel("Articles, ranked by units sold (%)"); ax[0].set_ylabel("Cumulative share of units (%)"); ax[0].set_title("Demand is long-tailed")
# (b) coverage over time
for k, col, ls in [(12, C["orange"], "-"), (100, C["blue"], "-"), (500, C["aqua"], "-")]:
    ax[1].plot(cov.index, cov[k] * 100, color=col, lw=1.7, label=f"Last week's top {k}")
ax[1].set_ylabel("Share of next week's units (%)"); ax[1].set_ylim(0); ax[1].legend(fontsize=9, loc="upper left"); ax[1].set_title("A static best-seller list covers little")
ax[1].xaxis.set_major_formatter(mpl.dates.DateFormatter("%b %y"))
# (c) overlap by lag with ceiling
lags = list(jl.keys()); ax[2].bar(range(len(lags)), [jl[k] for k in lags], color=C["blue"])
ax[2].axhline(ceiling, color=C["orange"], lw=2, ls="--"); ax[2].text(3.45, ceiling + 0.015, f"noise ceiling {ceiling:.2f}", ha="right", fontsize=9.5, color=C["ink2"])
for i, k in enumerate(lags): ax[2].text(i, jl[k] + 0.01, f"{jl[k]:.2f}", ha="center", fontsize=9.5)
ax[2].set_xticks(range(len(lags))); ax[2].set_xticklabels([f"{k} wk" for k in lags]); ax[2].set_ylim(0, 0.8)
ax[2].set_xlabel("Gap between the two weeks"); ax[2].set_ylabel("Top-100 overlap (Jaccard)"); ax[2].set_title("Best-seller lists churn")
fig.suptitle("Demand is concentrated at the top yet turns over quickly: lists go stale within weeks", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout(); save(fig, "fig09_demand_concentration_churn")
''')
md('''**So what.** The charter's best-seller baseline is the bar the recommender must clear. This section shows how hard that bar is on a time-split: the share of next week's units that last week's top articles capture, and how fast the list changes. It also tells M4 that the weekly forecast must handle new articles that have no history.''')

md('''## 7. Segments: age, channel, colour, and a proxy for the target group

### 7.1 H5: Do segments differ?''')
code(r'''
# (a) department mix by age band (units)
au_ = lines.assign(age_band=lines.cust.map(cust_s_c.age_band)).groupby(["age_band", "index_group_name"]).qty.sum().unstack().fillna(0).reindex(BAND_ORDER[1:])
au_ = au_[["Ladieswear", "Divided", "Menswear", "Sport"]]
chi2, p_chi, dof, _ = stats.chi2_contingency(au_.values)
cramer = math.sqrt(chi2 / (au_.values.sum() * (min(au_.shape) - 1)))
print(f"age band x department (known ages): chi2={chi2:,.0f}, dof={dof}, Cramer's V={cramer:.3f}")
mix = au_.div(au_.sum(axis=1), axis=0)

# (b) basket behaviour by age band with cluster-bootstrap CIs
rows = []
for b_ in BAND_ORDER[1:]:
    v_ = visits[visits.age_band == b_]
    s_, sl, sh = ratio_ci(v_.cust, v_.single, np.ones(len(v_)))
    u_, ul, uh = ratio_ci(v_.cust, v_.units, np.ones(len(v_)))
    rows.append((b_, v_.cust.nunique(), len(v_), s_, sl, sh, u_, ul, uh))
seg = pd.DataFrame(rows, columns=["age band", "customers", "visits", "single share", "s lo", "s hi", "units/visit", "u lo", "u hi"]).set_index("age band")
display(seg.round(3))
big = seg[seg.customers >= THR["H5_min_customers"]]
gap_single = float(big["single share"].max() - big["single share"].min())
print(f"single-unit share gap across age bands with >= {THR['H5_min_customers']} customers: {gap_single*100:.1f} points ({big['single share'].idxmin()} vs {big['single share'].idxmax()})")

# (c) channel and department of the visit
rows = []
for name, col in [("Channel", "channel"), ("Visit department", "dept")]:
    for lvl, v_ in visits.groupby(col):
        s_, sl, sh = ratio_ci(v_.cust, v_.single, np.ones(len(v_)), n_boot=150)
        rows.append((name, str(lvl), v_.cust.nunique(), len(v_), s_, sl, sh, v_.units.mean()))
seg2 = pd.DataFrame(rows, columns=["dimension", "level", "customers", "visits", "single share", "s lo", "s hi", "units/visit"])
display(seg2.round(3))
KEY.update(cramer=float(cramer), single_gap=gap_single, seg_age={k: dict(single=float(r["single share"]), lo=float(r["s lo"]), hi=float(r["s hi"]), n=int(r["customers"])) for k, r in seg.iterrows()},
           seg_ch={r.level: float(r["single share"]) for _, r in seg2[seg2.dimension == "Channel"].iterrows()})
''')
code(r'''
fig, ax = plt.subplots(1, 2, figsize=(14.5, 4.9), gridspec_kw={"width_ratios": [1.0, 1.0]})
im = ax[0].imshow(mix.values * 100, cmap=SEQ, aspect="auto", vmin=0, vmax=65)
ax[0].grid(False); ax[0].set_xticks(range(4)); ax[0].set_xticklabels(mix.columns); ax[0].set_yticks(range(len(mix))); ax[0].set_yticklabels(mix.index)
for i in range(mix.shape[0]):
    for j in range(mix.shape[1]): ax[0].text(j, i, f"{mix.values[i, j]*100:.0f}%", ha="center", va="center", fontsize=10, color="white" if mix.values[i, j]*100 > 36 else C["ink"])
ax[0].set_ylabel("Age band"); ax[0].set_title(f"Department mix shifts with age (Cramér's V = {cramer:.2f})")
s_ = seg.loc[BAND_ORDER[1:]]
xs_ = np.arange(len(s_))
ax[1].errorbar(xs_, s_["single share"] * 100, yerr=[(s_["single share"] - s_["s lo"]) * 100, (s_["s hi"] - s_["single share"]) * 100], fmt="o", color=C["blue"], ms=8, capsize=4, lw=1.8)
for i, (v_, n_) in enumerate(zip(s_["single share"], s_["customers"])): ax[1].text(i, v_ * 100 + 2.2, f"{v_:.0%}", ha="center", fontsize=9.5); ax[1].text(i, 34.5, f"n={n_:,}", ha="center", fontsize=8, color=C["muted"])
ax[1].set_xticks(xs_); ax[1].set_xticklabels(s_.index); ax[1].set_ylim(33, 80); ax[1].set_ylabel("Single-unit visits (%, 95% CI)"); ax[1].set_xlabel("Age band")
ax[1].set_title(f"Basket thinness by age: gap of {gap_single*100:.0f} points among large bands")
fig.suptitle("Segments differ in what they buy, much less in how much they buy per visit", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout(); save(fig, "fig10_segments_age")
''')

md('''### 7.2 H7: Colour mix and season''')
code(r'''
known = lines[~lines.perceived_colour_master_name.isin(["Unknown", "undefined"])]
col_all = known.groupby("perceived_colour_master_name").qty.sum().sort_values(ascending=False); col_sh = col_all / col_all.sum()
top3 = float(col_sh.iloc[:3].sum()); top3_names = list(col_sh.index[:3])
print(f"top 3 colours ({', '.join(top3_names)}): {top3:.1%} of units with a known colour; colours covering 80%: {int((col_sh.cumsum() < 0.8).sum() + 1)} of {len(col_sh)}")
by_dept = known[known.index_group_name.isin(["Menswear", "Ladieswear"])].groupby(["index_group_name", "perceived_colour_master_name"]).qty.sum().unstack(0)
by_dept = by_dept / by_dept.sum()
top_c = col_sh.index[:10]

LIGHT = ["Light", "Dusty Light", "Bright"]; DARK = ["Dark", "Medium Dark"]
vv = lines[lines.perceived_colour_value_name.isin(LIGHT + DARK + ["Medium Dusty"])].copy()
vv["is_light"] = vv.perceived_colour_value_name.isin(LIGHT); vv["month"] = vv.t_dat.dt.month
seas = vv.groupby("month").apply(lambda g: (g.qty * g.is_light).sum() / g.qty.sum())
seas_d = vv[vv.index_group_name.isin(["Menswear", "Ladieswear"])].groupby(["index_group_name", "month"]).apply(lambda g: (g.qty * g.is_light).sum() / g.qty.sum()).unstack(0)
summer, winter = seas.loc[[6, 7, 8]].mean(), seas.loc[[12, 1, 2]].mean()
print(f"light/bright share of units: summer (Jun-Aug) {summer:.1%} vs winter (Dec-Feb) {winter:.1%}; gap {abs(summer-winter)*100:.1f} points")
KEY.update(top3_colour=top3, top3_names=top3_names, light_summer=float(summer), light_winter=float(winter),
           black_share_men=float(by_dept.loc["Black", "Menswear"]), black_share_ladies=float(by_dept.loc["Black", "Ladieswear"]))

fig, ax = plt.subplots(1, 2, figsize=(14, 4.9), gridspec_kw={"width_ratios": [1.15, 1]})
y_ = np.arange(len(top_c))[::-1]; h = 0.38
ax[0].barh(y_ + h/2, by_dept.loc[top_c, "Menswear"] * 100, h, color=C["aqua"], label="Menswear")
ax[0].barh(y_ - h/2, by_dept.loc[top_c, "Ladieswear"] * 100, h, color=C["blue"], label="Ladieswear")
ax[0].set_yticks(y_); ax[0].set_yticklabels(top_c); ax[0].set_xlabel("Share of units with a known colour (%)"); ax[0].legend(fontsize=9.5)
ax[0].set_title(f"Three colours ({', '.join(top3_names)}) take {top3:.0%} of units")
mnames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ax[1].plot(range(1, 13), seas_d["Menswear"] * 100, color=C["aqua"], lw=2.2, marker="o", ms=5, label="Menswear")
ax[1].plot(range(1, 13), seas_d["Ladieswear"] * 100, color=C["blue"], lw=2.2, marker="o", ms=5, label="Ladieswear")
ax[1].set_xticks(range(1, 13)); ax[1].set_xticklabels(mnames, fontsize=9); ax[1].set_ylabel("Light & bright share of units (%)"); ax[1].legend(fontsize=9.5)
ax[1].set_title(f"Light colours peak in summer ({summer:.0%} vs {winter:.0%} in winter)")
fig.suptitle("Colour choice is concentrated in neutrals and follows the season", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.tight_layout(); save(fig, "fig11_colour")
''')

md('''### 7.3 A behavioural proxy for the charter's target group

The charter's target group buys one safe item and leaves, and relies on suggestions. Transactions cannot show confidence or effort, so we define a **proxy** with a rule fixed here: customers with at least 4 visits of which at least 60% are single-unit visits. This is a hypothesis about behaviour, not a measurement of the group; the M3 survey must confirm it.''')
code(r'''
rep_ = cust[cust.n_visits >= 4].copy()
rep_["proxy"] = rep_.single_share >= 0.6
share_cust = rep_.proxy.mean(); share_units = rep_.loc[rep_.proxy, "units"].sum() / rep_.units.sum()
dept_units = lines.groupby(["cust", "index_group_name"]).qty.sum().unstack().fillna(0)
dm = dept_units.reindex(rep_.index)
mixp = pd.DataFrame({"proxy segment": dm[rep_.proxy].sum() / dm[rep_.proxy].sum().sum(), "other repeat customers": dm[~rep_.proxy].sum() / dm[~rep_.proxy].sum().sum()})
prof = pd.DataFrame({"proxy segment": [rep_[rep_.proxy].n_visits.median(), rep_[rep_.proxy].age_clean.median(), rep_[rep_.proxy].n_types.median(), (rep_[rep_.proxy].age_band == "unknown").mean()],
                     "other repeat customers": [rep_[~rep_.proxy].n_visits.median(), rep_[~rep_.proxy].age_clean.median(), rep_[~rep_.proxy].n_types.median(), (rep_[~rep_.proxy].age_band == "unknown").mean()]},
                    index=["median visits", "median age", "median distinct product types", "share with unknown age"])
print(f"repeat customers (>=4 visits): {len(rep_):,} = {len(rep_)/len(cust):.1%} of customers; proxy segment is {share_cust:.1%} of them and {share_units:.1%} of their units")
display(prof.round(2)); display(mixp.round(3))
KEY.update(proxy_share_cust=float(share_cust), proxy_share_units=float(share_units), n_repeat=int(len(rep_)), proxy_types=float(prof.loc["median distinct product types", "proxy segment"]),
           other_types=float(prof.loc["median distinct product types", "other repeat customers"]))
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
ax[0].hist(rep_.single_share * 100, bins=np.arange(0, 105, 5), color=C["blue"], edgecolor="white", lw=0.5)
ax[0].axvline(60, color=C["orange"], lw=2, ls="--"); ax[0].text(61, ax[0].get_ylim()[1] * 0.9, f"proxy: ≥ 60% single-unit visits\n({share_cust:.0%} of repeat customers)", fontsize=9.5, color=C["ink2"])
ax[0].set_xlabel("Share of a customer's visits that are single-unit (%)"); ax[0].set_ylabel("Customers with ≥ 4 visits"); ax[0].set_title("Single-item habit among repeat customers")
x = np.arange(4); w = 0.38
ax[1].bar(x - w/2, mixp["proxy segment"] * 100, w, color=C["orange"], label="Proxy segment"); ax[1].bar(x + w/2, mixp["other repeat customers"] * 100, w, color=C["blue"], label="Other repeat customers")
ax[1].set_xticks(x); ax[1].set_xticklabels(mixp.index); ax[1].set_ylabel("Share of units (%)"); ax[1].legend(fontsize=9.5); ax[1].set_title("What the proxy segment buys")
fig.suptitle("A single-item habit is common among repeat customers (proxy only; survey needed)", x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.04)
fig.tight_layout(); save(fig, "fig12_target_proxy")
''')

md('''## 8. Hypothesis verdicts

Each rule from section 1 is applied to the numbers computed above, using the thresholds fixed before the data was loaded.''')
code(r'''
H = KEY["hist"]
checks = [
    ("H1", "Thin baskets, outfit rarely complete",
     f"single-unit visits {KEY['p_single']:.1%} (≥ {THR['H1_single_min']:.0%}); top+bottom visits {KEY['p_pair']:.1%} (≤ {THR['H1_pair_max']:.0%})",
     KEY["p_single"] >= THR["H1_single_min"] and KEY["p_pair"] <= THR["H1_pair_max"]),
    ("H2", "History predicts next purchase",
     f"product type {H['Product type']['ratio']:.2f}×, colour {H['Colour (master)']['ratio']:.2f}× the random baseline (≥ {THR['H2_ratio_min']}×)",
     H["Product type"]["ratio"] >= THR["H2_ratio_min"] and H["Colour (master)"]["ratio"] >= THR["H2_ratio_min"]),
    ("H3", "Top-bottom pairs are complementary",
     f"median adjusted lift of top×bottom pairs {KEY['lift_tb_median']:.2f} (≥ {THR['H3_lift_min']}); top×top {KEY['lift_tt_median']:.2f}",
     KEY["lift_tb_median"] >= THR["H3_lift_min"]),
    ("H4", "Long tail and fast churn",
     f"top 1% of articles hold {KEY['top1_art']:.1%} (< {THR['H4_top1pct_max']:.0%}); top-100 overlap at 1 week {KEY['jac1']:.2f} (< {THR['H4_jaccard_max']}; noise ceiling {KEY['jac_ceiling']:.2f})",
     KEY["top1_art"] < THR["H4_top1pct_max"] and KEY["jac1"] < THR["H4_jaccard_max"]),
    ("H5", "Segments differ",
     f"Cramér's V {KEY['cramer']:.2f} (≥ {THR['H5_cramer_min']}); single-unit share gap {KEY['single_gap']*100:.1f} pts (≥ {THR['H5_gap_min']*100:.0f})",
     KEY["cramer"] >= THR["H5_cramer_min"] and KEY["single_gap"] >= THR["H5_gap_min"]),
    ("H6", "Heavy buyers dominate",
     f"top 10% of customers buy {KEY['top10_units']:.1%} of units (≥ {THR['H6_top10_min']:.0%}); Gini {KEY['gini']:.2f}",
     KEY["top10_units"] >= THR["H6_top10_min"]),
    ("H7", "Colour concentrated and seasonal",
     f"top 3 colours {KEY['top3_colour']:.1%} (≥ {THR['H7_top3_min']:.0%}); light share summer {KEY['light_summer']:.1%} vs winter {KEY['light_winter']:.1%} ({abs(KEY['light_summer']-KEY['light_winter'])*100:.1f} pts, ≥ {THR['H7_season_min']*100:.0f})",
     KEY["top3_colour"] >= THR["H7_top3_min"] and abs(KEY["light_summer"] - KEY["light_winter"]) >= THR["H7_season_min"]),
]
verd = pd.DataFrame(checks, columns=["ID", "hypothesis", "evidence vs pre-set rule", "supported"])
verd["verdict"] = np.where(verd.supported, "Supported", "Not supported")
verd = verd.drop(columns="supported").set_index("ID")
KEY["verdicts"] = verd.verdict.to_dict()
with pd.option_context("display.max_colwidth", None):
    display(verd)
''')
