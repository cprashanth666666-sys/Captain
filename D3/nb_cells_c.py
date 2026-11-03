# Cells for sections 8 (reading), 9 (insight log), 10 (summary and modelling implications), appendix
from nb_helpers import md, code

md('''**Reading the verdicts.** Four hypotheses are supported and three are not, under rules fixed before the data was loaded. The three that fail are the most useful for the project, because each corrects an assumption in the charter:

* **H1 fails.** Baskets are not thin on average; the opportunity is an *incomplete outfit* (a top without a bottom), not a one-item visit.
* **H2 fails as written.** Coarse history (product type, colour, department) beats chance only slightly. The strong signal is exact-article repeat buying (about 19× chance), which the rule did not test directly.
* **H5 fails on the department-mix part** but the basket-thinness gap across age bands is large (17 points). The rule required both, so the verdict stays "Not supported", and the gap is carried into the insight log.

Two supported verdicts need a caveat. **H3:** top×top pairs show the same lift as top×bottom pairs, so co-purchase cannot by itself separate complements from alternatives. **H4:** the lag-1 overlap threshold (0.50) is above the sampling-noise ceiling (about 0.37), so that half of the rule was easy to pass; the 4-week and 13-week overlaps and the next-week coverage are the stronger evidence.''')

md('''## 9. Insight log

**Confidence levels.** *High*: large sample, narrow interval, same direction on raw and cleaned data. *Medium*: solid in the H&M data but rests on an unverified label, a noisy measure, or an assumption that Westside data must confirm. *Low*: a behavioural proxy or a pattern we cannot validate with these data.''')
code(r'''
H = KEY["hist"]
tbp = pairs[(pairs.roles.isin(["Top x Bottom", "Bottom x Top"])) & (pairs["visits together"] >= 200)].sort_values("adjusted lift", ascending=False).iloc[0]
ch1, ch2 = KEY["seg_ch"]["1"], KEY["seg_ch"]["2"]
sa = KEY["seg_age"]
rows = [
 ("I1", "Baskets are not thin on average; outfits are incomplete. Among visits that include a garment, fewer than half (45%) are complete (top + bottom, or full-body).",
  f"Fig 5. Single-unit visits {KEY['p_single']:.1%} (95% CI {KEY['p_single_lo']:.1%}-{KEY['p_single_hi']:.1%}); mean {KEY['mean_units_visit']:.1f} units per visit; garment visits: complete {KEY['complete']:.0%}, top only {KEY['top_only']:.0%}, bottom only {KEY['bottom_only']:.0%}.",
  "The charter's 'buys one item and leaves' premise does not hold for the average shopper. Target the mirror at the top-only and bottom-only moments and set the items-per-bill baseline at about 3.5 units, not 1. Revise the uplift assumptions in the M6 simulation.",
  "High (H&M data); Medium for transfer to Westside", "H1, BQ1"),
 ("I2", "Thin baskets sit in one sales channel.",
  f"Section 7.1. Single-unit share {ch1:.0%} in channel 1 vs {ch2:.0%} in channel 2; units per visit about 2.5 vs 4.1.",
  "If channel 1 is the physical store (the file does not say), the headroom is where the mirror will stand. Confirm the channel meaning before the simulation uses it; until then do not claim an in-store effect.",
  "Medium (channel label unverified)", "H1, BQ1"),
 ("I3", "A customer's own history is a strong predictor only at the level of the exact article. Product type and colour history add little over what is popular that week.",
  f"Fig 6. Exact-article repeat {H['Exact article (repeat purchase)']['real']:.1%} vs {H['Exact article (repeat purchase)']['base']:.1%} random ({H['Exact article (repeat purchase)']['ratio']:.0f}x); product type {H['Product type']['ratio']:.2f}x; colour {H['Colour (master)']['ratio']:.2f}x; department {H['Department']['ratio']:.2f}x. {KEY['items_eval']:,} items evaluated.",
  "Expect the recommender's edge over best-sellers to come from re-buy and from item-to-item cross-selling, not from learning a shopper's 'taste' in category or colour. Build article-level repeat and recency features first; treat taste embeddings as a second step.",
  "Medium (ratio depends on history length; measured on H&M only)", "H2, BQ2"),
 ("I4", "Purchases show which types are bought together, but not which are complements. Top x bottom pairs and top x top pairs have the same lift.",
  f"Fig 7. Median adjusted lift: top x bottom {KEY['lift_tb_median']:.2f} ({KEY['lift_tb_share12']:.0%} of pairs at 1.2 or more), top x top {KEY['lift_tt_median']:.2f}. Strongest top x bottom pair with 200+ visits: {tbp['type A']} + {tbp['type B']} (lift {tbp['adjusted lift']:.2f}).",
  "Use co-purchase only as a candidate generator for the outfit matcher. Compatibility must be learned from Polyvore outfit labels and judged on fill-in-the-blank accuracy, as the charter plans; do not evaluate the matcher on H&M co-purchase.",
  "Medium", "H3, BQ3"),
 ("I5", "Demand turns over fast. A best-seller list is stale within weeks, and new articles carry a large share of sales.",
  f"Fig 9. Last week's top 12 / 100 / 500 cover {KEY['cov12']:.1%} / {KEY['cov100']:.1%} / {KEY['cov500']:.1%} of next week's units. Top-100 overlap {KEY['jac1']:.2f} at 1 week (sampling ceiling {KEY['jac_ceiling']:.2f}), {KEY['jac4']:.2f} at 4 weeks, {KEY['jac52']:.2f} at 52. {KEY['novelty']:.0%} of weekly units come from articles first sold 8 weeks earlier or less.",
  "Recompute the best-seller baseline weekly on a short window and validate by date, never by random rows. Forecasts and suggestions need an attribute-based fallback for new articles. The MAP@12 target of three times the baseline is demanding because the baseline itself is weak at the article level.",
  "High (direction); Medium (levels, 10% sample is noisy)", "H4, BQ4"),
 ("I6", "A minority of heavy buyers dominates the data and a large group has almost no history.",
  f"Fig 3. Top 10% of customers buy {KEY['top10_units']:.0%} of units (Gini {KEY['gini']:.2f}); {KEY['one_visit_cust']:.0%} of customers have one visit; customers with unknown age or club status have a median of 1 visit vs 3 for others.",
  "Split train/test by customer, report metrics by activity tier, and weight or stratify so heavy buyers do not set the model. A third of members would meet the mirror with no history, so a popularity or content-based fallback is required, not optional.",
  "High", "H6, BQ2, BQ5"),
 ("I7", "Segments differ more in basket thinness than in what they buy. Older shoppers buy the fewest items per visit.",
  f"Fig 10. Single-unit share: 65+ {sa['65+']['single']:.0%} (CI {sa['65+']['lo']:.0%}-{sa['65+']['hi']:.0%}), 18-24 {sa['18-24']['single']:.0%}, 25-34 {sa['25-34']['single']:.0%}; gap {KEY['single_gap']*100:.0f} points. Department mix vs age: Cramer's V {KEY['cramer']:.2f} (weak).",
  "Evaluate quality by age band at one fixed setting (M5 fairness plan). A pooled model will be tuned to 25-34 baskets; older shoppers need single-item completion. Department is only a weak age signal, so age cannot be inferred from what is in the basket.",
  "High", "H5, BQ5"),
 ("I8", "Colour choice is concentrated in three neutrals and follows the season.",
  f"Fig 11. {', '.join(KEY['top3_names'])} = {KEY['top3_colour']:.0%} of units with a known colour. Light/bright share {KEY['light_summer']:.0%} in Jun-Aug vs {KEY['light_winter']:.0%} in Dec-Feb.",
  "For about two thirds of purchases colour matching is a choice among neutrals, so the incremental value of skin-tone-based colour advice is likely small and must be shown in the M5 colour-choice comparison. Add month and season to every model.",
  "Medium (colour attribute is the catalogue's, not the shopper's)", "H7, BQ3, BQ4"),
 ("I9", "The sample is not the bias; the proxy and the period are. The 10% sample matches the full file on every check, but 2020 is a structural break.",
  f"Figs 1-3. {KEY['rep_raw_pass']} of {KEY['rep_checks']} representativeness checks pass on raw data and the cleaned frame (max |SMD| {KEY['max_abs_smd_cust_clean']:.2f}). Mar-Aug 2020 units were {KEY['vol_2020_vs_2019']*100:+.0f}% vs 2019; channel-2 share {KEY['ch2_pre']:.0%} to {KEY['ch2_post']:.0%}. Baby/Children is {KEY['baby_units_share']:.1%} of raw units and was removed.",
  "Do not tune on the 2020 weeks alone; test models before and after March 2020. State in D4/D5 that results are patterns from European H&M data and must be re-validated on Westside data, as the charter says.",
  "High (sample); Medium (cause of the 2020 break)", "Bias checks"),
 ("I10", "The 'single-item habit' group the charter targets is visible but small, and transactions cannot show confidence or effort.",
  f"Fig 12. Proxy (4+ visits, 60%+ single-unit): {KEY['proxy_share_cust']:.1%} of {KEY['n_repeat']:,} repeat customers and {KEY['proxy_share_units']:.1%} of their units; median {KEY['proxy_types']:.0f} distinct product types vs {KEY['other_types']:.0f}.",
  "Do not size the business case on this proxy. The shopper survey planned for M3 must establish whether low-effort, low-confidence dressers exist at Westside and how large the group is.",
  "Low", "BQ5"),
]
insight_log = pd.DataFrame(rows, columns=["ID", "Insight", "Evidence (figure / number)", "So-what for the decision", "Confidence", "Hypothesis / question"]).set_index("ID")
insight_log.to_csv(OUT / "insight_log.csv", encoding="utf-8-sig")
with pd.option_context("display.max_colwidth", None):
    display(insight_log.style.set_properties(**{"text-align": "left", "white-space": "pre-wrap", "vertical-align": "top"}).set_table_styles(
        [{"selector": "th", "props": [("text-align", "left")]}]))
''')

md('''## 10. Summary: what matters most and how it shapes modelling

**The five insights that matter most**

1. **The gap is the incomplete outfit, not the one-item basket (I1, I2).** Fewer than half (45%) of garment visits are complete; 30% of visits are single-unit and the thin baskets sit in one channel. The mirror's job is to complete the outfit, and the items-per-bill baseline is about 3.5, not 1.
2. **History is useful for re-buying, not for taste (I3).** Exact-article repeat is about 19 times chance; product type and colour history barely beat a same-week random draw. M4 should start from repeat and recency features, then item-to-item co-purchase, before any taste embedding.
3. **Demand churns within weeks (I5).** A one-week-old top-12 list covers about 1.6% of next week's units and 39% of weekly units come from articles launched in the last 8 weeks. The best-seller baseline must be rebuilt weekly, validation must be by date, and new articles need an attribute-based fallback.
4. **Heavy buyers dominate and many shoppers have no history (I6, I7).** Top 10% of customers buy 48% of units; a third have one visit; older shoppers have the thinnest baskets. Split by customer, report by activity tier and age band, and ship a cold-start fallback.
5. **Co-purchase does not identify complements (I4), and colour is mostly neutrals (I8).** Purchases are a candidate generator for the outfit matcher only; compatibility comes from Polyvore. Colour advice has limited headroom and must be tested against shopper-chosen colours in M5.

| M4/M5 component | What the EDA changes |
|---|---|
| Best-seller baseline | Weekly rebuild, short window; report coverage by K. Expect a low absolute score (top-12 covers about 1.6%). |
| Recommender | Features: exact-article repeat, recency, department, month. Fallback for one-visit and unknown-age members. Weight or stratify by customer activity. |
| Outfit matcher | Use co-purchase lift only to propose candidates; train and test on Polyvore (fill-in-the-blank), never on H&M co-purchase. |
| Demand forecast | Seasonal terms, article age, attribute pooling for new articles; evaluate by WAPE on later weeks, with a pre/post-March-2020 check. |
| Validation | Split by date and by customer; no random row split. Treat the 2020 weeks as a separate regime. |
| Fairness | Report quality by age band and activity tier at one fixed setting; department stands in for gender only as a labelled proxy. |
| Open items | Channel meaning; shopper survey for the target group; Westside data to re-validate every number here. |''')

code(r'''
# Persist headline numbers for the PDF summary and print run metadata
KEY["runtime_sec"] = round(time.time() - T0)
def _clean(o):
    if isinstance(o, dict): return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)): return o.item()
    return o
(OUT / "key_numbers.json").write_text(json.dumps(_clean(KEY), indent=2))
import platform, matplotlib, scipy
print(f"python {platform.python_version()} | pandas {pd.__version__} | numpy {np.__version__} | matplotlib {matplotlib.__version__} | scipy {scipy.__version__}")
print(f"seed {SEED} | total runtime {KEY['runtime_sec']} s | figures: {len(list(FIG.glob('*.png')))} | outputs: {[p.name for p in OUT.iterdir()]}")
''')
