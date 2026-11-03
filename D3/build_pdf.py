import json
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

HERE = Path(__file__).parent
K = json.loads((HERE / "outputs" / "key_numbers.json").read_text())
fd = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(fd / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(fd / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

INK, INK2, BLUE, ORANGE, GRID = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834", "#e1e0d9"
S = lambda name, **kw: ParagraphStyle(name, **{"fontName": "DV", "textColor": colors.HexColor(INK), **kw})
title = S("t", fontName="DVB", fontSize=15, leading=18)
sub = S("s", fontSize=7.8, leading=10, textColor=colors.HexColor(INK2))
h2 = S("h2", fontName="DVB", fontSize=10, leading=12.5, spaceBefore=5, spaceAfter=2, textColor=colors.HexColor(BLUE))
body = S("b", fontSize=8.2, leading=10.6)
small = S("sm", fontSize=7.2, leading=9.1)
cell = S("c", fontSize=6.9, leading=8.6)
cellb = S("cb", fontName="DVB", fontSize=6.9, leading=8.6)
cap = S("cap", fontSize=6.8, leading=8.4, textColor=colors.HexColor(INK2))

H = K["hist"]
story = []
story += [Paragraph("Westside Stylist Mirror: what the purchase data says", title),
          Paragraph("ANCP D3 · EDA insight summary · Group M · C Prashanth · Linked outcomes CO2, CO4 · Data: H&amp;M 10% customer sample "
                    f"({K['raw_rows']:,} rows, Sep 2018–Sep 2020) as a proxy for Westside purchase history", sub), Spacer(1, 3)]
story += [Paragraph("Bottom line", h2),
          Paragraph(f"The data support building the mirror as an <b>outfit completer and re-buy assistant</b>, not as a taste-learner for one-item shoppers. "
                    f"Fewer than half of garment visits ({K['complete']:.0%}) contain a complete outfit, but baskets are not thin on average "
                    f"({K['p_single']:.0%} single-unit visits; {K['mean_units_visit']:.1f} units per visit). History helps mainly through exact re-buys, "
                    f"and demand turns over within weeks. The 10% sample matches the full file on every representativeness check, so the main risks are the proxy "
                    f"(European, no gender or store field) and the 2020 break, not sampling.", body)]

story.append(Paragraph("The five insights that matter most, and how each shapes modelling", h2))
ins = [
    ("1  The gap is the incomplete outfit, not the one-item basket.",
     f"Garment visits: complete {K['complete']:.0%}, top only {K['top_only']:.0%}, bottom only {K['bottom_only']:.0%}. Single-unit visits {K['p_single']:.0%} "
     f"(95% CI {K['p_single_lo']:.0%}–{K['p_single_hi']:.0%}); thin baskets sit in one channel (38% vs 25%; meaning of the code unverified).",
     "Set the items-per-bill baseline at about 3.5, not 1, and target top-only / bottom-only moments. Revise uplift assumptions in the M6 simulation."),
    ("2  History predicts re-buying, not taste.",
     f"Exact-article repeat: {H['Exact article (repeat purchase)']['real']:.1%} vs {H['Exact article (repeat purchase)']['base']:.1%} for a same-week random draw "
     f"({H['Exact article (repeat purchase)']['ratio']:.0f}×). Product type {H['Product type']['ratio']:.2f}×, colour {H['Colour (master)']['ratio']:.2f}×.",
     "M4 recommender: start with repeat and recency features and item-to-item cross-sell; add taste embeddings only if they beat that."),
    ("3  Demand turns over within weeks.",
     f"Last week's top 12 covers {K['cov12']:.1%} of next week's units, top 100 covers {K['cov100']:.1%}; top-100 overlap {K['jac1']:.2f} at 1 week "
     f"(noise ceiling {K['jac_ceiling']:.2f}), {K['jac4']:.2f} at 4 weeks. {K['novelty']:.0%} of weekly units come from articles first sold ≤ 8 weeks earlier.",
     "Rebuild the best-seller baseline weekly; validate by date; give new articles an attribute-based fallback; add season terms to the forecast."),
    ("4  Heavy buyers dominate; many shoppers have no history; older shoppers buy least per visit.",
     f"Top 10% of customers buy {K['top10_units']:.0%} of units; {K['one_visit_cust']:.0%} have one visit. Single-unit share by age: 65+ "
     f"{K['seg_age']['65+']['single']:.0%} vs 25–34 {K['seg_age']['25-34']['single']:.0%}.",
     "Split by customer, report by activity tier and age band, weight heavy buyers, and ship a popularity / content fallback for one-visit members."),
    ("5  Co-purchase cannot identify complements; colour is mostly neutrals.",
     f"Median adjusted lift: top×bottom {K['lift_tb_median']:.2f}, top×top {K['lift_tt_median']:.2f} (no difference). "
     f"{', '.join(K['top3_names'])} = {K['top3_colour']:.0%} of units; light share {K['light_summer']:.0%} summer vs {K['light_winter']:.0%} winter.",
     "Use co-purchase only to propose candidates; train and test the outfit matcher on Polyvore. Test colour advice against shopper-chosen colours in M5."),
]
rows = [[Paragraph("<b>Insight</b>", cell), Paragraph("<b>Evidence</b>", cell), Paragraph("<b>Shapes modelling</b>", cell)]]
for a, b, c in ins:
    rows.append([Paragraph(f"<b>{a}</b>", cell), Paragraph(b, cell), Paragraph(c, cell)])
t = Table(rows, colWidths=[44 * mm, 76 * mm, 58 * mm], repeatRows=1)
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f2fd")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
story.append(t)
story.append(Spacer(1, 4))
fw = 59 * mm
def img(name, w=fw):
    from PIL import Image as PI
    iw, ih = PI.open(HERE / "figures" / name).size
    return Image(str(HERE / "figures" / name), width=w, height=w * ih / iw)
figs = Table([[img("fig05_basket_composition.png", 89 * mm), img("fig06_history_signal.png", 89 * mm)],
              [Paragraph("Figure 5. Most visits are not single-unit; outfits are incomplete.", cap), Paragraph("Figure 6. History is strongest for exact re-buys.", cap)],
              [img("fig09_demand_concentration_churn.png", 180 * mm), ""],
              [Paragraph("Figure 9. Demand is concentrated at the top and the top list changes quickly.", cap), ""]], colWidths=[91 * mm, 91 * mm])
figs.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                          ("SPAN", (0, 2), (1, 2)), ("SPAN", (0, 3), (1, 3))]))
story.append(figs)
story.append(PageBreak())

# ---------------- page 2
story.append(Paragraph("Hypotheses, bias checks and limits", title))
story.append(Spacer(1, 2))
story.append(Paragraph("Seven hypotheses tested against rules fixed before loading the data", h2))
V = K["verdicts"]
hyp = [
    ("H1", "BQ1", "Thin baskets, outfit rarely complete", f"Single-unit {K['p_single']:.0%} (rule ≥ 50%); top+bottom {K['p_pair']:.0%} (rule ≤ 15%)"),
    ("H2", "BQ2", "History predicts next purchase (≥ 1.5×)", f"Type {H['Product type']['ratio']:.2f}×, colour {H['Colour (master)']['ratio']:.2f}×; exact article {H['Exact article (repeat purchase)']['ratio']:.0f}× (not in rule)"),
    ("H3", "BQ3", "Top–bottom pairs are complementary", f"Median lift {K['lift_tb_median']:.2f} (rule ≥ 1.2); top×top {K['lift_tt_median']:.2f}, so not specific to complements"),
    ("H4", "BQ4", "Long tail, fast churn", f"Top 1% of articles hold {K['top1_art']:.0%} (rule < 25%); overlap {K['jac1']:.2f} at 1 wk (ceiling {K['jac_ceiling']:.2f}), {K['jac4']:.2f} at 4 wk"),
    ("H5", "BQ5", "Segments differ", f"Cramér's V {K['cramer']:.2f} (rule ≥ 0.15) fails; single-unit gap {K['single_gap']*100:.0f} pts across age bands passes"),
    ("H6", "BQ2/5", "Heavy buyers dominate", f"Top 10% of customers buy {K['top10_units']:.0%} of units (rule ≥ 40%); Gini {K['gini']:.2f}"),
    ("H7", "BQ3/4", "Colour concentrated and seasonal", f"Top 3 colours {K['top3_colour']:.0%} (rule ≥ 50%); light share {K['light_summer']:.0%} vs {K['light_winter']:.0%}"),
]
rows = [[Paragraph(f"<b>{x}</b>", cell) for x in ["ID", "Question", "Hypothesis", "Evidence vs rule", "Verdict"]]]
for i, q, h, e in hyp:
    v = V[i]
    rows.append([Paragraph(i, cellb), Paragraph(q, cell), Paragraph(h, cell), Paragraph(e, cell),
                 Paragraph(f'<font color="{"#006300" if v == "Supported" else "#c8501f"}"><b>{v}</b></font>', cell)])
t = Table(rows, colWidths=[9 * mm, 16 * mm, 47 * mm, 82 * mm, 25 * mm], repeatRows=1)
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f2fd")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                       ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
story.append(t)
story.append(Paragraph("Four supported, three not. The three failures each correct a charter assumption (thin baskets, taste-based history, age-driven department mix).", small))

story.append(Paragraph("Representativeness and bias, repeated on raw and cleaned data", h2))
story.append(Paragraph(
    f"<b>Sample vs full population:</b> {K['rep_raw_pass']} of {K['rep_checks']} checks pass on raw data and the cleaned frame: department mix (largest gap 0.05 pp), monthly profile (0.06 pp), "
    f"channel mix (0.02 pp), basket size, purchases per customer (23.5 vs 23.3), customer age and club status (largest |SMD| {K['max_abs_smd_cust_clean']:.2f}). "
    f"<b>Cleaning:</b> duplicate rows kept as quantity ({K['dup_rows']:,} rows, units preserved); Baby/Children ({K['baby_units_share']:.1%} of units), non-apparel and under-18 customers excluded; "
    f"{K['units_in_scope']:,} units in scope. <b>Remaining bias:</b> missing age, FN flag or club status mark light buyers (median 1–2 visits vs 3–4); "
    f"units in Mar–Aug 2020 were {K['vol_2020_vs_2019']*100:+.0f}% vs 2019 and channel-2 share rose from {K['ch2_pre']:.0%} to {K['ch2_post']:.0%}; "
    f"no gender, size or store field; European assortment; price is normalised.", body))

story.append(Paragraph("Insight log (full table with evidence and so-what in the notebook, section 9)", h2))
import csv
with open(HERE / "outputs" / "insight_log.csv", encoding="utf-8-sig") as f:
    log = list(csv.DictReader(f))
rows = [[Paragraph(f"<b>{x}</b>", cell) for x in ["ID", "Insight", "Decision it informs", "Confidence"]]]
dec = {"I1": "Mirror scope; items-per-bill baseline", "I2": "In-store simulation inputs", "I3": "Recommender features", "I4": "Outfit-matcher data source",
       "I5": "Baseline, forecast, validation design", "I6": "Splits, weighting, cold-start", "I7": "Fairness plan (M5)", "I8": "Colour-advice value; seasonality terms",
       "I9": "Validation windows; transfer to Westside", "I10": "Business-case sizing; survey"}
for r in log:
    ins_ = r["Insight"].split(". ")[0].rstrip(".")
    rows.append([Paragraph(r["ID"], cellb), Paragraph(ins_ + ".", cell), Paragraph(dec[r["ID"]], cell), Paragraph(r["Confidence"], cell)])
t = Table(rows, colWidths=[9 * mm, 90 * mm, 49 * mm, 30 * mm], repeatRows=1)
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f2fd")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)), ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
                       ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
story.append(t)
story.append(Paragraph("Confidence: High = large sample, narrow interval, same direction on raw and cleaned data; Medium = depends on an unverified label, noisy measure or Westside transfer; Low = behavioural proxy.", small))

story.append(Paragraph("Limits and next steps", h2))
story.append(Paragraph(
    "H&amp;M customers are not Westside's; every number is a pattern to re-validate on Westside data. The target group (low-effort, low-confidence dressers) cannot be seen in transactions; "
    f"our proxy (4+ visits, 60%+ single-unit) covers {K['proxy_share_cust']:.0%} of repeat customers and {K['proxy_share_units']:.1%} of their units, and the M3 shopper survey must confirm it. "
    "Next: confirm what the sales-channel code means; run the survey; carry the weekly baseline, date-and-customer splits and age-band fairness checks into D4/D5.", body))

story.append(Spacer(1, 4))
story.append(Paragraph('Code and files: <link href="https://github.com/cprashanth666666-sys/Captain/tree/D3" color="#2a78d6"><u>https://github.com/cprashanth666666-sys/Captain/tree/D3</u></link>', body))

def footer(c, d):
    c.saveState(); c.setFont("DV", 6.5); c.setFillColor(colors.HexColor(INK2))
    c.drawString(14 * mm, 8 * mm, "ANCP D3 summary · Group M · Westside Stylist Mirror · numbers from ANCP_TM_D3_eda.ipynb (outputs/key_numbers.json)")
    c.drawRightString(196 * mm, 8 * mm, f"Page {d.page} of 2"); c.restoreState()


doc = BaseDocTemplate(str(HERE / "ANCP_TM_D3_summary.pdf"), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=13 * mm,
                      title="ANCP D3 EDA insight summary: Westside Stylist Mirror", author="Group M")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(14 * mm, 13 * mm, 182 * mm, 272 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])
doc.build(story)
print("built")
