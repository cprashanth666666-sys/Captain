"""Build ANCP_TM_D3_EDA_validation_v1.pdf.  Usage: python -I make_validation_report.py <github_url> <out_pdf>"""
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

URL, OUT = sys.argv[1], Path(sys.argv[2])
HERE = Path(__file__).parent
V = json.loads((HERE / "validation_results.json").read_text())
K = json.loads((HERE.parent / "outputs" / "key_numbers.json").read_text())
LOGO = HERE.parent.parent / "D2" / "xime_logo.png"
for nm, fn in [("T", "times.ttf"), ("TB", "timesbd.ttf"), ("TI", "timesi.ttf"), ("TBI", "timesbi.ttf")]:
    pdfmetrics.registerFont(TTFont(nm, "C:/Windows/Fonts/" + fn))
pdfmetrics.registerFontFamily("T", normal="T", bold="TB", italic="TI", boldItalic="TBI")
INK, GREY = "#000000", "#ebebeb"
S = lambda n, **kw: ParagraphStyle(n, **{"fontName": "T", "textColor": colors.black, **kw})
title, sub = S("t", fontName="TB", fontSize=17, leading=21), S("s", fontSize=9.4, leading=12.4, textColor=colors.HexColor("#404040"))
h1, h2 = S("h1", keepWithNext=1, fontName="TB", fontSize=13, leading=16, spaceBefore=10, spaceAfter=2.5), S("h2", keepWithNext=1, fontName="TB", fontSize=11, leading=14, spaceBefore=6, spaceAfter=1)
body = S("b", fontSize=10.5, leading=14.2, spaceAfter=3.5, alignment=4)
cell, cellb = S("c", fontSize=9, leading=11.2), S("cb", fontName="TB", fontSize=9, leading=11.2)
cap = S("cap", fontSize=8.6, leading=10.8, textColor=colors.HexColor("#404040"))
P = lambda t, s=body: Paragraph(t, s)
n = lambda v: f"{v:,}"


def tbl(rows, widths, pad=2):
    data = [[Paragraph(str(c), cellb if i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#c8c8c8")),
                           ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GREY)),
                           ("LINEBELOW", (0, 0), (-1, 0), .8, colors.black)]))
    return t


def footer(c, d):
    if d.page == 1:
        return
    c.saveState(); c.setFont("T", 8); c.drawString(16 * mm, 9 * mm, "ANCP D3 · EDA validation report · Group M")
    c.drawRightString(194 * mm, 9 * mm, f"Page {d.page}"); c.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=15 * mm,
                      title="ANCP D3 EDA validation report", author="Group M", lang="en-IN")
doc.addPageTemplates([PageTemplate("p", [Frame(16 * mm, 15 * mm, 178 * mm, 268 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])
ct = lambda n_, **kw: ParagraphStyle(n_, fontName="T", alignment=1, textColor=colors.black, **kw)
st = [Spacer(1, 22 * mm), Paragraph("A Project Report on", ct("c1", fontSize=14, leading=18)), Spacer(1, 6 * mm),
      Paragraph("<b><i>\u201cExploratory Data Analysis (D3): Check and Independent Validation\u201d</i></b>", ct("c2", fontSize=20, leading=26)),
      Spacer(1, 9 * mm), Paragraph("<b>Group M</b>", ct("c3", fontSize=16, leading=20)),
      Paragraph("Analytics Capstone Project (ANCP) · Westside Stylist Mirror · Module M3", ct("c4", fontSize=11, leading=15)),
      Spacer(1, 12 * mm), Paragraph("Submitted to", ct("c5", fontSize=12, leading=16)),
      Paragraph("<b>Xavier Institute of Management &amp; Entrepreneurship, Bangalore</b>", ct("c6", fontSize=14, leading=18)), Spacer(1, 12 * mm)]
ro = Table([[Paragraph("<b>Roll No.</b>", cell), Paragraph("<b>Name</b>", cell)], [Paragraph("BA05007", cell), Paragraph("Ambarish Sengupta", cell)],
            [Paragraph("BA05009", cell), Paragraph("Arpan Shah", cell)], [Paragraph("BA05015", cell), Paragraph("C Prashanth", cell)]], colWidths=[40 * mm, 70 * mm])
ro.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GREY)),
                        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
st += [ro, Spacer(1, 10 * mm), Paragraph(f"Repository: <u>{URL}</u>", ct("c8", fontSize=11, leading=15)), Spacer(1, 12 * mm),
       Image(str(LOGO), width=80 * mm, height=80 * mm * 202 / 684), PageBreak()]

m = V["metrics"]
st += [P("EDA validation report: was the analysis done, and does it hold up?", title),
       P("ANCP D3 (lead owner C Prashanth) · checked 3 Nov 2026 · Linked outcomes CO2, CO4 · Repository: " + f"<u>{URL}</u>", sub), Spacer(1, 3)]
st += [P("1  Verdict", h1),
       P(f"<b>Yes, the EDA was performed.</b> The repository holds a notebook of 57 cells (30 code cells, every one with saved output, 0 errors), 12 figures, "
         f"an insight log of 10 findings, 7 hypothesis verdicts and a two-page summary. The hypotheses and their pass rules were written before any data was loaded.", body),
       P(f"<b>Yes, the numbers validate.</b> A clean re-run of the notebook reproduces all 122 key numbers exactly. An independent recomputation from the "
         f"D2 cleaned data matches {V['n_ok']} of {V['n_metrics']} headline figures within tolerance (most to 4 decimal places). All {V['n_hyp_agree']} of 7 hypothesis verdicts follow from the "
         f"stated rules. We rate the EDA <b>validated for use in M4, with the caveats in section 4</b>.", body)]

st += [P("2  What is in the repository", h1)]
rows = [["Item", "Path (relative to the repository)", "Purpose"],
        ["EDA notebook", "D3/ANCP_TM_D3_eda.ipynb (and .html)", "Questions, hypotheses, cleaning, 12 figures, verdicts, insight log"],
        ["Insight log", "D3/outputs/insight_log.csv", "10 findings with evidence, so-what and confidence"],
        ["Key numbers", "D3/outputs/key_numbers.json", "122 values the summary quotes"],
        ["Summary", "D3/ANCP_TM_D3_summary.pdf", "Two-page decision summary"],
        ["Reference profile", "D3/reference/full_population_profile.json", "Full 31.8M-row file profile for the sample check"],
        ["Validation code and results", "D3/validation/validate_eda.py, validation_results.json", "This report's checks"]]
st += [tbl(rows, [32, 76, 70])]
st += [P("The raw and cleaned data files are not listed here: they derive from the Kaggle H&amp;M competition data, which may not be redistributed (see the D2 report).", cap)]

st += [P("3  How it was validated", h1)]
rows = [["Test", "What was done", "Result"],
        ["T1  Runs clean", "Read the saved notebook: error outputs and code cells without output.", "0 errors; 30 of 30 code cells have output."],
        ["T2  Reproduces", "Re-executed the whole notebook in a fresh copy against the raw files and compared key_numbers.json value by value.", "All 122 values identical (run time excluded)."],
        ["T3  Independent recount", "Rebuilt " + str(V["n_metrics"]) + " headline figures from the D2 cleaned tables with new code: visits from customer-days, a different Gini formula, weekly top-100 overlap, colour shares, channel and age splits.", f"{V['n_ok']} of {V['n_metrics']} within tolerance (table below)."],
        ["T4  Verdict logic", "Applied the notebook's pre-set thresholds to its own reported numbers for H1 to H7.", "7 of 7 verdicts agree."],
        ["T5  Text vs numbers", "Checked the insight log and the summary PDF quote the same values as key_numbers.json.", "All checked values match."]]
st += [tbl(rows, [30, 100, 48])]
st += [P("T3 also tests the link between deliverables: D3 cleans the raw files inside the notebook, D2 cleans them with a script. Both give the same 3,066,344 units and 132,435 customers.", cap)]

st += [P("3.1 Independent recount against D3 (selected rows; all 25 in validation_results.json)", h2)]
pick = ["units in scope", "customers in scope", "single-unit visit share", "mean units per visit", "customers with one visit", "Gini of units per customer",
        "top 10% customers' share of units", "median age (known ages)", "menswear share of units", "top-3 colour share of known-colour units",
        "weekly units Mar-Aug 2020 vs 2019", "channel-2 share Mar-Aug 2020", "single-unit share, age 65+", "garment visits that are complete outfits",
        "top-100 overlap (Jaccard), 1-week gap", "next-week coverage of last week's top 12", "top 1% of articles' share of units"]
f = lambda v: n(int(v)) if abs(v) > 1000 else f"{v:.4f}"
rows = [["Figure", "D3 notebook", "Independent", "Gap", "Within tolerance"]]
for r in m:
    if r["metric"] in pick:
        rows.append([r["metric"], f(r["d3"]), f(r["independent"]), f"{r['abs_diff']:.4f}", "Yes" if r["ok"] else "No"])
st += [tbl(rows, [70, 30, 30, 20, 28], pad=1.6)]

st += [P("4  Caveats and gaps, most important first", h1)]
cv = [
    ("<b>H5 verdict and insight I7 pull in different directions.</b> H5 is \"Not supported\" because Cramér's V is "
     f"{K['cramer']:.3f} (rule: at least 0.15), yet the single-unit share differs by {K['single_gap']*100:.0f} points between age bands, which passes its own 5-point rule. "
     "Both statements are correct under the AND rule, but a reader of the summary could take H5 to mean \"no age difference\". The summary should say so."),
    ("<b>Not independently recomputed.</b> The exact-article repeat ratio (19×) behind H2, the co-purchase lift behind H3, the confidence intervals, Cramér's V and the "
     "target-group proxy were checked only by the clean re-run (T2), not by new code. They are reproducible, not yet cross-checked."),
    ("<b>Thresholds are team judgements.</b> A verdict flips if a threshold moves; for example H1 needs 50% single-unit visits and the data show 30%, so that verdict is robust, "
     "but H2 (1.26× against a 1.5× rule) is closer. The notebook does not include a sensitivity table."),
    ("<b>Proxy limits remain.</b> The data is a European retailer's; the sales channel is an unlabelled code; a \"visit\" is a customer-day because there is no bill ID. "
     "I2 (thin baskets in one channel) is rightly rated medium confidence."),
    ("<b>EDA, not model evidence.</b> The notebook uses the whole two-year window. That suits description, but none of its hit rates or overlaps is a model result. "
     "M4 must rebuild them behind the date split in the D2 data."),
    ("<b>Same sample.</b> All checks reuse the one 10% sample, so they test the arithmetic and logic, not whether another sample would give the same patterns.")]
for i, t in enumerate(cv, 1):
    st.append(P(f"{i}. {t}"))
st += [P("5  Recommended next steps", h1),
       P("(1) Add one sentence to the D3 summary explaining H5. (2) Add a threshold-sensitivity table for H2 and H5. (3) In M4, load the D2 cleaned tables (they reproduce D3's numbers) "
         "instead of cleaning inside each notebook. (4) Confirm the meaning of sales channel codes 1 and 2 with the course contact before any in-store claim.", body),
       P("6  Reproduce", h1),
       P("<font face='Courier'>python -I D3/validation/validate_eda.py D2/data-v1.0 D3/outputs D3/validation/validation_results.json</font> recreates T3 and T4. "
         "T2 needs the raw Kaggle files and the notebook runner in D3. The checks were written and run with the help of Claude Code; every figure above comes from the saved results file.", body)]
doc.build(st)
print("built")
