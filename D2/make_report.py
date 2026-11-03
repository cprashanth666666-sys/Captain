"""Build ANCP_TM_D2_v1.pdf (audit report <= 8 pages + datasheet appendix). Run from D2/ after clean_data.py and make_figures.py."""
import json
from pathlib import Path

import matplotlib
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

HERE = Path(__file__).parent
M = json.loads((HERE / "audit_metrics.json").read_text())
I = json.loads((HERE / "sample_integrity.json").read_text())
K3 = json.loads((HERE.parent / "D3" / "outputs" / "key_numbers.json").read_text())
fd = Path("C:/Windows/Fonts")
for nm, fn in [("DV", "times.ttf"), ("DVB", "timesbd.ttf"), ("DVI", "timesi.ttf"), ("DVBI", "timesbi.ttf")]:
    pdfmetrics.registerFont(TTFont(nm, str(fd / fn)))      # Times New Roman, the XIME report face
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVBI")

INK, INK2, BLUE, GRID, MID = "#000000", "#404040", "#000000", "#c8c8c8", "#ebebeb"
S = lambda n, **kw: ParagraphStyle(n, **{"fontName": "DV", "textColor": colors.HexColor(INK), **kw})
title = S("t", fontName="DVB", fontSize=17, leading=21)
sub = S("s", fontSize=9.4, leading=12.4, textColor=colors.HexColor(INK2))
h1 = S("h1", keepWithNext=1, fontName="DVB", fontSize=13, leading=16, spaceBefore=10, spaceAfter=2.5, textColor=colors.HexColor(BLUE))
h2 = S("h2", keepWithNext=1, fontName="DVB", fontSize=11, leading=14, spaceBefore=6, spaceAfter=1)
body = S("b", fontSize=10.5, leading=14.2, spaceAfter=3.5, alignment=4)
cell = S("c", fontSize=9, leading=11.2)
cellb = S("cb", fontName="DVB", fontSize=9, leading=11.2)
cap = S("cap", fontSize=8.6, leading=10.8, textColor=colors.HexColor(INK2), spaceAfter=3)
P = lambda t, s=body: Paragraph(t, s)
n = lambda v: f"{v:,}"
pc = lambda v, d=1: f"{v*100:.{d}f}%"

C, R, F, MS, DU, PR, VO = M["clean"], M["rep"], M["features"], M["missing"], M["dups"], M["price"], M["volume"]
RAW = M["raw"]


cellD = S("cd", fontSize=10, leading=13)
cellDb = S("cdb", fontName="DVB", fontSize=10, leading=13)


def tbl(rows, widths, head=True, zebra=True, pad=2, big=False):
    cs, cb = (cellD, cellDb) if big else (cell, cellb)
    data = [[Paragraph(str(c), cb if (head and i == 0) else cs) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor(GRID)),
          ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MID)), ("LINEBELOW", (0, 0), (-1, 0), .8, colors.HexColor(INK2))]
    t.setStyle(TableStyle(st))
    return t


def footer(c, d):
    if d.page == 1:
        return
    c.saveState(); c.setFont("DV", 6.8); c.setFillColor(colors.HexColor(INK2))
    c.drawString(16 * mm, 9 * mm, "ANCP D2 · Data audit report · Group M · data-v1.0")
    c.drawRightString(194 * mm, 9 * mm, f"Page {d.page}")
    c.restoreState()


doc = BaseDocTemplate(str(HERE / "ANCP_TM_D2_v1.pdf"), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                      topMargin=14 * mm, bottomMargin=15 * mm, title="ANCP D2 Data audit report: Westside Stylist Mirror",
                      author="Group M", subject="Data audit, datasheet and cleaning log for data-v1.0", lang="en-IN")
doc.addPageTemplates([PageTemplate("p", [Frame(16 * mm, 15 * mm, 178 * mm, 268 * mm, leftPadding=0, rightPadding=0,
                                                topPadding=0, bottomPadding=0)], onPage=footer)])
W = 178
st = []

ct = lambda n_, **kw: ParagraphStyle(n_, fontName="DV", alignment=1, textColor=colors.black, **kw)
st += [Spacer(1, 22 * mm),
       Paragraph("A Project Report on", ct("c1", fontSize=14, leading=18)), Spacer(1, 6 * mm),
       Paragraph("<b><i>“Data Audit, Datasheet and Cleaned Dataset (D2): H&amp;M Purchase Sample as a Proxy for the Westside Stylist Mirror”</i></b>", ct("c2", fontSize=20, leading=26)),
       Spacer(1, 9 * mm), Paragraph("<b>Group M</b>", ct("c3", fontSize=16, leading=20)),
       Paragraph("Analytics Capstone Project (ANCP) · Module M2 · Deliverable D2 · Version v1 (data-v1.0)", ct("c4", fontSize=11, leading=15)),
       Spacer(1, 12 * mm), Paragraph("Submitted to", ct("c5", fontSize=12, leading=16)),
       Paragraph("<b>Xavier Institute of Management &amp; Entrepreneurship, Bangalore</b>", ct("c6", fontSize=14, leading=18)),
       Spacer(1, 5 * mm),
       Paragraph("<i>Linked course outcomes: CO2, CO6</i>", ct("c7", fontSize=11, leading=15)), Spacer(1, 14 * mm)]
roster = Table([[Paragraph("<b>Roll No.</b>", cell), Paragraph("<b>Name</b>", cell)],
                [Paragraph("BA05007", cell), Paragraph("Ambarish Sengupta", cell)],
                [Paragraph("BA05009", cell), Paragraph("Arpan Shah", cell)],
                [Paragraph("BA05015", cell), Paragraph("C Prashanth", cell)]], colWidths=[40 * mm, 70 * mm])
roster.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MID)),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
st += [roster, Spacer(1, 8 * mm), Paragraph("Repository: <u>https://github.com/cprashanth666666-sys/Captain/tree/prash/D2</u>", ct("c8", fontSize=10, leading=14)), Spacer(1, 12 * mm), Image(str(HERE / "xime_logo.png"), width=80 * mm, height=80 * mm * 202 / 684), PageBreak()]

# ======================================================================= PAGE 1: summary + sources
st += [P("Data audit: H&amp;M purchase sample used as a proxy for Westside", title),
       P("ANCP D2 · Group M · Module M2 (Data acquisition and preparation) · Lead owner: Arpan Shah · Linked outcomes CO2, CO6 · Version data-v1.0 · "
         "Audit date 28 Oct 2026 · Code in the repository folder named in section 7", sub), Spacer(1, 3)]
st += [P("Summary: what the audit found, worst first", h1)]
st += [P(f"<b>1. The data is a proxy, and the biggest risk is outside the file.</b> It is a European retailer's purchases with no gender, region, store "
         f"or skin-tone field, a normalised price and an unlabelled sales channel. Nothing here shows how Westside's shoppers behave. "
         f"Results from it are a proof of concept (section 4.2).", body),
       P(f"<b>2. Re-use rights limit how the cleaned data may be shared.</b> The Kaggle rules allow non-commercial and academic use and forbid passing the "
         f"data to anyone not in the competition. The cleaned files are derived data, so the public repository holds code, the dictionary and checksums only; the data files go privately to the course team and "
         f"assessor (sections 1, 2 and 7).", body),
       P(f"<b>3. The largest cleaning decision is duplicates.</b> {n(DU['exact_extra_rows'])} rows ({pc(DU['share'])}) are exact copies. The file has no "
         f"quantity column, so we read them as units bought together and keep them as <i>qty</i>, which preserves all units (section 3).", body),
       P(f"<b>4. The file is otherwise structurally clean.</b> No missing values in transactions, no unknown article or customer keys, no repeated IDs. "
         f"Missingness sits in customer attributes: age {pc(MS['customers_sample']['age'][1])}, club status {pc(MS['customers_sample']['club_member_status'][1])}, "
         f"and the FN and Active flags {pc(MS['customers_sample']['FN'][1],0)} (blank means \"not a member\").", body),
       P(f"<b>5. The 10% sample is faithful.</b> We re-read the full {n(I['full_rows'])}-row file: every row of all {n(I['sample_customers'])} sampled customers is in "
         f"the sample ({I['customers_with_row_count_mismatch']} count mismatches), and the sample's age mean differs from other customers by "
         f"{R['age_mean_sample']-R['age_mean_rest']:+.2f} years (section 4.1).", body),
       P(f"<b>6. After cleaning:</b> {n(C['units_final'])} units on {n(C['lines_final'])} lines, {n(C['customers_in_scope'])} customers, "
         f"20 Sep 2018 to 22 Sep 2020, with a date-based train / valid / test marker to prevent leakage (section 5).", body)]

st += [P("1  Source, access, licence and date accessed", h1)]
rows = [["Dataset / file", "Origin and size", "Licence or permission", "Accessed", "SHA-256 (first 12)"],
        ["articles.csv", f"Kaggle: H&amp;M Personalized Fashion Recommendations (H&amp;M Group, 2022). {n(RAW['articles'])} articles × 25 columns.",
         "Competition rules: non-commercial and academic research use; no redistribution. Rules page read 10 Oct 2026 (D1 research notes).", "27 Oct 2026*", M["inputs_sha256"]["articles.csv"][:12]],
        ["customers.csv", f"Same competition. {n(RAW['customers_all'])} customers × 7 columns (age, club flags, hashed postcode).", "As above.", "27 Oct 2026*", M["inputs_sha256"]["customers.csv"][:12]],
        ["transactions_train.csv", f"Same competition. {n(I['full_rows'])} rows, {n(I['full_buying_customers'])} buying customers. Used only to check the sample; not shipped.", "As above.", "27 Oct 2026*", "fff5e3b35c1b"],
        ["transactions_train_sample10pct.csv", f"Our extract: all purchases of a random {pc(I['sample_share_of_buying_customers'],2)} of buying customers. {n(RAW['tx_rows'])} rows, {n(RAW['tx_customers'])} customers. This is the audit input.",
         "Derived from the above; same terms apply.", "Made 27 Oct 2026*", M["inputs_sha256"]["transactions_train_sample10pct.csv"][:12]]]
st += [tbl(rows, [37, 56, 44, 20, 21])]
st += [P("* Date from the file's modified time on the team laptop; no download log was kept. The sampling seed was not recorded, so the sample cannot be redrawn; "
         "we fix it by checksum and by the integrity check in section 4.1. The other datasets in the charter data plan (Polyvore Outfits, Fashion Product Images, "
         "Casual Conversations v2, BodyM) are <b>not yet acquired</b> and are outside data-v1.0; each needs its own access request, licence check and datasheet.", cap)]

# ======================================================================= consent
st += [P("2  Consent and purpose limitation against the DPDP Act, 2023", h1)]
st += [P("<b>Status of the law.</b> The Digital Personal Data Protection Act, 2023 was enacted on 11 Aug 2023 and the Rules were notified on 14 Nov 2025. "
         "The consent, notice, security and retention duties start 18 months later (about 13 May 2027), so on today's date the older IT Act s.43A / SPDI Rules 2011 "
         "regime applies and DPDP is our design standard (D1 research notes; law-firm trackers, accessed 28 Oct 2026; a proposal to shorten the period was reported but we found no notification). "
         "This section is a team assessment, not legal advice. Section numbers were checked against the PRS summary and law-firm commentary, not the Gazette text.", body),
       P("<b>Is this personal data?</b> We treat it as personal data. The Act covers data about an individual who is identifiable by or in relation to it. Each record is "
         "a hashed customer ID with an age and a dated purchase history; we cannot reverse the hash, but H&amp;M can, and a long purchase trail can single out a person. "
         "<b>Consent.</b> We hold no consent from these people and have no relationship with them; H&amp;M collected the data and released it for a competition. "
         "Our use is therefore secondary use of already-released data, and we rely on the release terms, not on our own consent notice. "
         "<b>Purpose.</b> The only purpose is to build and test a recommender and forecasting prototype for a university capstone (exploratory analysis and model training, "
         "which is research and statistics). No decision will be taken about any person in the file: the mirror is never run on them, and nobody is contacted or profiled. "
         "The Act's research and statistical exemption (s.17(2)(b), as we read it) turns on exactly this: no decision specific to a person, plus prescribed standards in the Rules. we have not verified that we meet them, so <b>we do not rely on the exemption</b> and apply the principles below anyway.", body)]
rows = [["DPDP principle", "How data-v1.0 meets it", "Residual gap"],
        ["Consent and notice", "No new collection from people. Use stays within the Kaggle terms. Volunteer consent (faces, skin tone) is a separate design in D1 and no volunteer data is in this dataset.", "No consent from the 136,670 customers; relies on the controller's release."],
        ["Purpose limitation", "Used only for the capstone's models and analysis. Documented in the datasheet; a model trained on it is not deployed on those people.", "A later pilot at Westside must use Westside's own consented data, not this file."],
        ["Data minimisation", f"Postcode dropped (352,899 distinct hashes in the full customer file); the 64-character hash replaced by an integer key; "
         f"only buying customers kept ({n(C['customers_in_scope'])} of {n(RAW['customers_all'])}); {n(C['customers_under18_removed'])} customers under 18 removed; free-text kept only in the article catalogue (no personal text).", "Age and the purchase trail remain and are the signal we need."],
        ["Accuracy", "Age above 90 blanked; impossible values none found; missing values kept explicit, not guessed.", "Source accuracy beyond our checks is unknown."],
        ["Storage limitation", "Plan: keep until the capstone assessment ends, then delete the repository copy and local raw files. Date to be set with the course.", "Needs a named owner and date."],
        ["Security", "Data files kept out of the public repository and shared privately with team and assessor; SHA-256 checksums for integrity. No raw file in the repository.", "Laptop copies of raw data are unencrypted unless the team enables disk encryption."],
        ["Accountability", "This report, the datasheet, the cleaning script and the checksum list form the record. No attempt will be made to re-identify anyone; linking to other data is out of bounds.", "Team to confirm the no-linkage rule in writing."]]
st += [tbl(rows, [26, 110, 42])]

# ======================================================================= quality audit
st += [P("3  Quality audit: missing values, duplicates, outliers, and the treatment chosen", h1)]
st += [P(f"All counts below come from <i>clean_data.py</i> run on the raw sample (audit_metrics.json). Our figures reproduce D3's separately written notebook: "
         f"{n(K3['units_in_scope'])} units, {n(K3['units_dropped_baby'])} baby units, {n(K3['n_customers_in_scope'])} customers in scope.", body)]
st += [P("3.1 Missing values", h2)]
rows = [["Field", "Missing (sample buyers)", "Meaning", "Treatment and reason"],
        ["transactions: all 5 fields", "0", "Complete.", "None needed."],
        ["customers.age", f"{n(MS['customers_sample']['age'][0])} ({pc(MS['customers_sample']['age'][1])})", "Not recorded.", "Keep customer; band = \"unknown\"; no imputation, because a filled-in age would invent a signal. Missingness is tested as a feature in D3."],
        ["customers.FN, Active", f"{n(MS['customers_sample']['FN'][0])} / {n(MS['customers_sample']['Active'][0])} (about 65%)", "Blank = flag not set (Kaggle data description convention; our reading).", "Set to 0. Imputing from other fields would be guesswork."],
        ["club_member_status; fashion_news_frequency", f"{n(MS['customers_sample']['club_member_status'][0])}; {n(MS['customers_sample']['fashion_news_frequency'][0])} (under 1.2%)", "Not recorded.", "Label \"UNKNOWN\". Case of NONE/None normalised."],
        ["articles.detail_desc", f"{n(MS['articles']['detail_desc'][0])} ({pc(MS['articles']['detail_desc'][1])})", "No text description.", "Empty string plus <i>detail_desc_missing</i> flag; text is not used as a key."]]
st += [tbl(rows, [36, 34, 44, 64])]
st += [P("3.2 Duplicates", h2)]
st += [P(f"<b>Customers and articles:</b> no repeated IDs in either table. <b>Transactions:</b> {n(DU['exact_extra_rows'])} rows are exact repeats "
         f"(same customer, day, article, price, channel), from {n(DU['distinct_rows_with_copies'])} distinct lines that appear more than once. "
         f"<b>Treatment: collapse to one line with qty = number of copies.</b> Dropping them would remove {pc(DU['share'])} of units and understate basket size; "
         f"a quantity of 2 is the natural reading of two identical items in one bill. The risk is that some are logging errors, which would inflate demand slightly; "
         f"we cannot test this without a bill ID. A further {n(DU['same_cust_day_article_other_price'])} lines share customer, day and article but differ in price or channel; these are separate purchases and are kept.", body)]
st += [P("3.3 Outliers", h2)]
rows = [["Check", "Finding", "Treatment and reason"],
        ["Age", f"Range {RAW['age_min']:.0f} to {RAW['age_max']:.0f}. {n(RAW['age_lt18_sample'])} buyers under 18; {RAW['age_gt90_sample']} above 90.",
         "Under-18s removed (charter rules out minors; DPDP s.9 treats under-18s as children). Age above 90 set to missing, customer kept: the values look like defaults."],
        ["Price", f"Normalised scale, {PR['min']:.5f} to {PR['max']:.3f}, median {PR['p50']:.3f}. A global IQR fence would flag {n(PR['n_above_fence'])} rows ({pc(PR['n_above_fence']/RAW['tx_rows'])}), mostly just dearer products, so it is the wrong test.",
         f"Compared each line with its own article's train-window median instead: {n(F['price_rel_high'])} lines above 3× and {n(F['price_rel_low'])} below ⅓ ({pc(F['price_rel_low']/C['lines_final'])}, plausible markdowns). Flagged in <i>price_rel_flag</i>, none removed; price used as relative only."],
        ["Customer volume", f"Median {VO['rows_per_customer_p50']:.0f} rows per customer, 99th pct {VO['p99']:.0f}, maximum {n(VO['max'])}.",
         f"{F['heavy_buyers']} customers above the 99.9th percentile of train-window units ({F['heavy_buyer_cut']:.0f}) are flagged <i>heavy_buyer_flag</i>, not removed: they are real demand but may be resellers or staff. Models should be run with and without them."],
        ["Basket size", f"Largest same-day basket {VO['basket_max_rows']} rows; {VO['basket_gt50']} baskets above 50 rows.", "Kept. Large baskets could be bulk or gift orders; flagged by <i>basket_units</i>."],
        ["Dates", f"All dates parse, {RAW['date_min']} to {RAW['date_max']}. First and last months are part-months.", "Kept; weekly analyses drop the partial edge weeks (D3)."]]
st += [tbl(rows, [24, 66, 88])]
st += [P("3.4 Scope filters (rows leave only for a stated reason)", h2)]
st += [Image(str(HERE / "figures" / "fig1_quality.png"), width=W * mm, height=W * mm * 2.45 / 7.4)]
st += [P(f"Figure 1. (a) Units kept. Baby/Children ({n(C['units_out_of_scope_baby'])} units) are bought for someone else, so they cannot teach outfit advice for the shopper. "
         f"Non-apparel groups such as cosmetics and furniture ({n(C['units_out_of_scope_non_apparel'])} units) are not outfit items. Under-18 buyers are removed. "
         f"{n(C['units_raw']-C['units_final'])} units ({pc(1-C['units_final']/C['units_raw'])}) leave in total; {n(RAW['customers_sample']-C['customers_in_scope'])} customers leave "
         f"(under 18, or all purchases out of scope). (b) Most lines sit near the article's usual price. (c) Customer volume is heavily skewed.", cap)]

# ======================================================================= bias
st += [P("4  Representativeness and bias checks", h1)]
st += [P("4.1 Is the sample a fair copy of the H&amp;M population?", h2)]
rows = [["Check", "Sample buyers", "Other customers", "Gap"],
        ["Mean age (years)", f"{R['age_mean_sample']:.2f}", f"{R['age_mean_rest']:.2f}", f"standardised difference {R['age_smd']:.4f}"],
        ["Age missing", pc(R["age_missing_sample"], 2), pc(R["age_missing_rest"], 2), f"{(R['age_missing_sample']-R['age_missing_rest'])*100:+.2f} pp"],
        ["Club status ACTIVE", pc(R["club_sample"]["ACTIVE"], 2), pc(R["club_rest"]["ACTIVE"], 2), f"{(R['club_sample']['ACTIVE']-R['club_rest']['ACTIVE'])*100+0:+.2f} pp".replace("-0.00","0.00")],
        ["FN flag set", pc(R["fn_sample"], 2), pc(R["fn_rest"], 2), f"{(R['fn_sample']-R['fn_rest'])*100:+.2f} pp"],
        ["Rows per customer, sample vs full file", f"mean {K3['rpc_mean_sample']:.2f}", f"mean {K3['rpc_mean_full']:.2f}", "D3 profile of the full file"],
        ["Row counts for all sampled customers vs full file", f"{n(I['sample_rows'])}", f"{n(I['full_rows_for_sample_customers'])}", f"{I['customers_with_row_count_mismatch']} mismatches"]]
st += [tbl(rows, [62, 36, 36, 44])]
st += [P("Verdict: the sample is a customer-level random draw with complete purchase histories and matches the wider customer base to within 0.1 percentage point. "
         "Sampling is not a bias risk. D3 also reports that all 6 of its sample-versus-full-file checks (month, channel, product group, basket size) pass.", body)]
st += [P("4.2 Who or what is under-represented inside the data", h2)]
st += [Image(str(HERE / "figures" / "fig2_representativeness.png"), width=W * mm, height=W * mm * 2.5 / 7.4)]
st += [P(f"Figure 2. (a) The sample matches other customers on age. (b) Menswear is {pc(R['catalogue_share_by_index_group']['Menswear']/(1-R['catalogue_share_by_index_group']['Baby/Children']),0)} of in-scope articles "
         f"but {pc(R['units_by_index_group']['Menswear'],1)} of units. (c) Units per month; hollow points are part-months; shaded: after March 2020.", cap)]
rows = [["Dimension", "Finding", "Why it matters for Westside"],
        ["Gender", f"No gender field. Department is the only proxy: Ladieswear {pc(R['units_by_index_group']['Ladieswear'],0)} and Divided {pc(R['units_by_index_group']['Divided'],0)} of units, Menswear {pc(R['units_by_index_group']['Menswear'],1)}, Sport {pc(R['units_by_index_group']['Sport'],1)}. {n(R['buyers_by_index_group']['Menswear'])} customers bought menswear.", "Men are under-represented, yet the charter targets shirts, T-shirts and trousers. Fairness by gender cannot be tested here."],
        ["Age", f"65+ is {pc(R['age_band_sample']['65+'])} of customers and {pc(R['units_by_age_band']['65+']/C['units_final'])} of units; \"unknown\" age {pc(R['age_band_sample']['unknown'])}. 18-34 is {pc(R['age_band_sample']['18-24']+R['age_band_sample']['25-34'],0)} of customers.", "Older shoppers have the thinnest history; D3 shows they buy fewest items per visit. Report errors by age band."],
        ["Geography, culture, dress", "European store, Western apparel. No Indian wear, no region, no store ID, no climate field. Sales channel is an anonymous code 1 or 2 (71% of units in code 2).", "Westside's range and festive wear are absent. Use for method development only."],
        ["Skin tone and body", "No images and no such attributes. Colours are product colours; Black is 35% of units, White 13%, Blue 13%.", "The charter's skin-tone fairness test needs other data. This dataset says nothing on it."],
        ["Heavy buyers", f"{F['heavy_buyers']} customers above the 99.9th percentile; {n(F['customers_no_train_history'])} customers have no train-window history (cold start).", "Averages are pulled by few buyers; cold-start shoppers need a fallback."],
        ["Time", f"Two years only (two seasonal cycles); units fell about {abs(R['covid_units_2019_vs_2020_jan_aug'][1]/R['covid_units_2019_vs_2020_jan_aug'][0]-1)*100:.0f}% in Mar-Aug 2020 against Mar-Aug 2019 (pandemic). {n(R['catalogue_in_scope_never_sold'])} in-scope articles never sold in the sample.", "The final test week sits in an unusual year. Treat absolute forecasts with care."],
        ["Price", "Normalised, not a currency, and no cost or margin.", "No rupee claims; discount effects are only relative."]]
st += [tbl(rows, [24, 82, 72])]
st += [P("4.3 Effect of cleaning on representativeness. D3 compared customer attributes before and after cleaning: the largest standardised difference moved from "
         f"{K3['max_abs_smd_cust_raw']:.3f} to {K3['max_abs_smd_cust_clean']:.3f}, still small. Removing under-18s and baby buyers does change who is in the data: it drops "
         f"{pc(C['units_out_of_scope_baby']/C['units_raw'])} of units bought for children, so conclusions apply to adults buying for themselves.", body)]

# ======================================================================= features
st += [P("5  Feature engineering log and leakage risk", h1)]
st += [P(f"Rule used: the last 7 days (16 to 22 Sep 2020) are <b>test</b>, the 7 days before are <b>valid</b>, the rest is <b>train</b> (units {n(F['split_rows']['train'])} / {n(F['split_rows']['valid'])} / {n(F['split_rows']['test'])}). "
         "Any statistic that summarises many rows is computed from train only. This follows the charter: split by date, never by row.", body)]
rows = [["ID", "Feature (column)", "Logic", "Leakage risk and control"],
        ["F1", "qty", "Count of identical raw rows on a line.", "Low. Uses only that day's rows. Do not use as a feature to predict that same day's quantity."],
        ["F2", "split", "train / valid / test by date.", "This is the guard. Never shuffle across it."],
        ["F3", "basket_units", "Units the same customer bought on the same day.", "<b>High</b> if the task is to predict items in the same visit: the feature contains the answer. Use only for analysis of visits, not as a model input for same-visit targets."],
        ["F4", "price_rel, price_rel_flag", "price ÷ article median price over the train window; flags above 3 or below ⅓.", "Controlled: reference built from train only, so valid and test rows use past prices. Empty for articles unseen in train (5,373 lines)."],
        ["F5", "week_start, month", "Monday of the week; calendar month.", "None. Calendar facts."],
        ["F6", "age_band", "Bands of the cleaned age; \"unknown\" kept.", "None for purchases. Age is the value on the extract date, not on the purchase date; ages drift by up to 2 years across the window."],
        ["F7", "units_train, visits_train, first/last_purchase_train, has_train_history", "Customer totals and dates over the train window.", "<b>Medium.</b> Safe for predicting valid and test weeks. <b>Not safe</b> as a feature on train rows, because it counts the row's own and later purchases. For training, rebuild rolling features up to each cut-off in M4."],
        ["F8", "heavy_buyer_flag", "Train units above the 99.9th percentile.", "Same as F7. Flag only; used for sensitivity runs."]]
st += [tbl(rows, [8, 38, 54, 78])]
st += [P("Features not built, on purpose: article popularity, repeat-purchase and co-purchase counts, and any colour or outfit-pair feature. They are the most leakage-prone, "
         "because computing them across the whole file would let the test week leak into training. They belong in M4 behind the same date cut.", body)]

# ======================================================================= limits and deliverables
st += [P("6  Limitations of this audit", h1)]
st += [P("(1) No bill ID, store ID, size, quantity or returns, so duplicates, returns and stock cannot be audited directly; the charter plans to simulate stock. "
         "(2) We cannot see how H&amp;M built the file (pseudonymisation, filtering, rounding of price). (3) The sample seed is lost. (4) Our reading of blank FN/Active as \"not set\" "
         "follows the usual Kaggle interpretation and is not confirmed by the source. (5) Legal points are a student assessment and need a lawyer before any real deployment.", body)]
st += [P("7  Reproduce and verify", h1)]
st += [P(f"Repository folder <i>D2/</i>: <i>clean_data.py</i> (raw to cleaned, deterministic), <i>make_figures.py</i>, <i>make_report.py</i>, <i>verify_sample.py</i>, "
         f"<i>audit_metrics.json</i> (every number here), <i>sample_integrity.json</i>, and <i>data-v1.0/</i> with three cleaned tables, <i>data_dictionary.csv</i> and "
         f"<i>SHA256SUMS.txt</i>. Run <font face='Courier'>python -I clean_data.py &lt;raw_dir&gt; .</font> then compare checksums with <i>sha256sum -c SHA256SUMS.txt</i>. "
         f"The three data tables are held privately and are not in the public repository, because the Kaggle rules bar redistribution; raw files stay out too. Code and documents: <u>https://github.com/cprashanth666666-sys/Captain/tree/prash/D2</u> (branch prash).", body)]
rows = [["File in data-v1.0", "Rows", "Size", "SHA-256 (first 16)"]]
for f, r in [("transactions_clean.csv.gz", "transactions"), ("customers_clean.csv.gz", "customers"), ("articles_clean.csv.gz", "articles")]:
    rows.append([f, n(M["outputs"]["rows"][r]), f"{M['outputs'][f]['bytes']/1e6:.1f} MB", M["outputs"][f]["sha256"][:16]])
rows.append(["data_dictionary.csv", "31 entries", f"{M['outputs']['data_dictionary.csv']['bytes']/1e3:.1f} kB", M["outputs"]["data_dictionary.csv"]["sha256"][:16]])
st += [tbl(rows, [58, 30, 24, 66])]

# ======================================================================= DATASHEET
st += [PageBreak(), P("Appendix: Datasheet for data-v1.0", title),
       P("Format follows Gebru et al., \"Datasheets for Datasets\" (Communications of the ACM, 2021): motivation, composition, collection process, preprocessing, uses, distribution, maintenance.", sub), Spacer(1, 3)]


def ds(head, qa):
    st.append(P(head, h1))
    st.append(tbl([["Question", "Answer"]] + qa, [52, 126], pad=4, big=True))


ds("A  Motivation", [
    ["For what purpose was the dataset created?", "Original: a Kaggle competition by H&amp;M Group (2022) to test fashion recommenders. This version: a cleaned subset for the Westside Stylist Mirror capstone, to build and test purchase-history recommendations, outfit-completion analysis and weekly demand forecasts. Westside's own data is not available to us (D1)."],
    ["Who created it and who funded it?", "Source: H&amp;M Group (competition sponsor). Cleaned version: Group M, ANCP course, with Arpan Shah as D2 lead owner. No external funding."],
    ["Was there a specific gap it fills?", "We found no public Indian retailer purchase dataset for this use; H&amp;M is the closest public proxy we found (D1 research notes)."]])
ds("B  Composition", [
    ["What do the instances represent?", "Three linked tables. <i>transactions_clean</i>: one line per customer, day, article, price and channel, with quantity. <i>customers_clean</i>: one row per buying customer. <i>articles_clean</i>: one row per catalogue article."],
    ["How many?", f"{n(M['outputs']['rows']['transactions'])} transaction lines ({n(C['units_final'])} units); {n(M['outputs']['rows']['customers'])} customers; {n(M['outputs']['rows']['articles'])} articles ({n(M['articles']['in_scope'])} flagged in scope, the rest kept for reference)."],
    ["Is it a sample? How was it chosen?", f"Yes. All purchases of a random {pc(I['sample_share_of_buying_customers'],1)} of buying customers (seed unrecorded), then filtered as in section 3. Verified against the full file: {I['customers_with_row_count_mismatch']} mismatches. Representative of H&amp;M customers (section 4.1), not of Westside's."],
    ["What data does each instance hold?", "Transactions: customer_key, date, article_id, relative price, channel code, qty and engineered fields F1 to F5. Customers: age and band, club and news flags, train-window activity. Articles: 25 source columns (type, colour, department, description) plus two flags. See data_dictionary.csv."],
    ["Missing data? Errors, noise, redundancy?", "No missing values in transactions. Customer attributes have gaps (section 3.1). Price is relative. Article descriptions are free text and not audited. Some catalogue fields are redundant (code and name pairs)."],
    ["Confidential or sensitive content? Relation to people?", "Yes, it is about people: age and a purchase trail per pseudonymous customer. No names, contacts, addresses or postcodes; no special-category fields. Readers could infer gender or lifestyle from purchases. Treated as personal data (section 2)."],
    ["Subpopulations identified?", "Age bands and department only. No gender, ethnicity or region. Distribution in section 4.2."],
    ["Relationships between instances?", "Transactions join to customers on customer_key and to articles on article_id (10-character text, leading zero kept). All keys resolve; no orphans."],
    ["Recommended data splits?", "Use the <i>split</i> column: train to 8 Sep 2020, valid 9 to 15 Sep, test 16 to 22 Sep. Never split by row. Split people by customer if testing on unseen shoppers."],
    ["Does it contain data that might be considered offensive or that identifies people directly?", "No names, contact details, images or postcodes. Product text is catalogue copy. Indirect identification through a unique purchase trail is possible in principle, which is why linkage is barred."]])
ds("C  Collection process", [
    ["How was the data acquired?", "Logged by H&amp;M Group's sales systems and released, pseudonymised, via Kaggle. We have no detail on logging, hashing or price normalisation. Downloaded 27 Oct 2026 by the team."],
    ["Over what period?", "20 Sep 2018 to 22 Sep 2020 (purchases). Customer attributes are a single snapshot."],
    ["Were individuals told, and did they consent?", "Unknown to us. H&amp;M's own notice to customers was not available. We obtained no consent and do not contact anyone (section 2)."],
    ["Ethical review?", "None done by the source that we know of. Team review is this audit; no formal ethics board review."],
    ["Who collected it and how were they compensated?", "H&amp;M Group's systems collected it as a by-product of selling. We know of no payment or compensation to the customers."],
    ["Sampling strategy for this version?", "Customer-level random draw of about 10% so each person keeps a full purchase history. Chosen because history is what the mirror uses. Weakness: seed lost, so the draw cannot be repeated."]])
ds("D  Preprocessing, cleaning and labelling", [
    ["What was done?", f"Exact duplicates collapsed to qty ({n(DU['exact_extra_rows'])} rows); Baby/Children and non-apparel articles dropped ({n(C['units_out_of_scope_baby']+C['units_out_of_scope_non_apparel'])} units); under-18 buyers dropped ({n(C['customers_under18_removed'])}); age above 90 blanked; missing flags set explicitly; postcode removed; customer hash replaced by integer key; features F1 to F8 added; date-based split marker added."],
    ["Is the raw data kept?", "Yes, unmodified on team laptops (hashes in section 1); not in the repository. <i>clean_data.py</i> recreates all cleaned files from them, and the run is deterministic (same checksums on re-run)."],
    ["Labels?", "None. There is no target in the file; M4 defines targets (next-basket items, weekly demand) from the date split."],
    ["What was deliberately not done?", "No imputation of age; no removal of heavy buyers or price outliers (flagged instead); no removal of large baskets; no re-balancing by gender or age; no text cleaning of descriptions."],
    ["How can the cleaning be checked?", "Re-run clean_data.py on the raw files and compare SHA-256 sums. Counts also match D3's separately written notebook (units 3,066,344; customers 132,435)."]])
ds("E  Uses", [
    ["Intended uses.", "EDA (D3), training and evaluating a recommender against a best-seller baseline, an outfit-gap analysis, and weekly demand forecasts, all inside this course."],
    ["Uses already made.", "D3 exploratory analysis used the same raw files and the same cleaning rules (it reads raw, not these cleaned files)."],
    ["Uses to avoid.", "Any decision about the people in the file; re-identification or linkage to other data; commercial use; claims about Indian shoppers, gender or skin tone; absolute rupee or revenue claims; training on the test week."],
    ["What tasks is it not suitable for?", "Anything needing gender, store, size, returns, stock, skin tone, body shape or Indian styles. It is also unsuited to fairness claims about skin tone or gender."],
    ["Risks from composition?", "Women's wear and 18-34 skew; one retailer, one region, a pandemic year. A model fitted here may under-serve men, older shoppers and new items. Report results by age band and department."]])
ds("F  Distribution", [
    ["How is it shared?", "Code, dictionary and checksums are in the public GitHub repository (link in section 7). The data tables are <b>not public</b>: the Kaggle rules forbid passing the data to people outside the competition, so they go only to the team and the assessor, through a private channel, labelled data-v1.0."],
    ["Licence and terms?", "Inherits the competition rules (non-commercial, academic). We add no further licence. Source: H&amp;M Group. Cite as: H&amp;M Personalized Fashion Recommendations, Kaggle, 2022."],
    ["Third-party IP or fees?", "The data and catalogue text belong to H&amp;M Group under the competition rules. No fees. Catalogue images are not included."],
    ["Export controls or other limits?", "None known."]])
ds("G  Maintenance", [
    ["Who maintains it and how to reach them?", "Arpan Shah (D2 lead owner), Group M, through the course repository."],
    ["Updates and versioning?", "No new source data is expected. Changes to cleaning rules create data-v1.1 with a changelog and new checksums; v1.0 is never overwritten."],
    ["Retention?", "Until the capstone is assessed; then the repository copy and raw files are deleted. Date to be agreed with the course."],
    ["Can others extend or contribute?", "Team members only, by pull request that updates clean_data.py, the dictionary and the checksums together."],
    ["Will older versions stay available?", "Yes, by tag, until the retention date above."],
    ["Errors reported to?", "The repository issue list. Known open items: sampling seed lost; blank FN/Active reading unconfirmed; channel code meanings unknown; no bill ID."]])

doc.build(st)
print("built")
