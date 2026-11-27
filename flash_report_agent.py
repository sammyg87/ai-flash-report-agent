"""
Monthly Flash Report Agent
--------------------------
Reads monthly P&L data (actual, budget, prior year), does ALL the math in pandas,
then has Claude write the leadership commentary from those numbers only.

Key lesson: the AI never calculates. Code does the math, the AI explains it,
and a final check catches any dollar figure the AI made up.

Usage:
  pip3 install anthropic pandas
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 flash_report_agent.py                    # latest month in the file
  python3 flash_report_agent.py --month 2026-09    # a specific month
  python3 flash_report_agent.py --no-ai            # numbers only, no API call
"""

import argparse
import json
import re

import pandas as pd

DATA_FILE = "pl_monthly.csv"
MODEL = "claude-sonnet-5-5"
MATERIAL_PCT = 5.0       # flag variances bigger than this %...
MATERIAL_USD = 10_000    # ...AND bigger than this many dollars
COST_CATEGORIES = {"Cost of sales", "Operating expenses"}


# ---------- 1. THE MATH (code, not AI) ----------
def load(month: str | None):
    df = pd.read_csv(DATA_FILE)
    month = month or df["month"].max()
    if month not in set(df["month"]):
        raise SystemExit(f"Month {month} not in {DATA_FILE}")
    mtd = df[df["month"] == month]
    ytd = df[df["month"] <= month].groupby(["account", "category"], as_index=False)[
        ["actual", "budget", "prior_year"]].sum()
    return month, mtd, ytd


def summarize(frame: pd.DataFrame) -> dict:
    """Roll accounts up into P&L lines."""
    def total(cat, col):
        return float(frame.loc[frame["category"] == cat, col].sum())

    out = {}
    for col in ["actual", "budget", "prior_year"]:
        rev = total("Revenue", col)
        cos = total("Cost of sales", col)
        opx = total("Operating expenses", col)
        out[col] = {
            "Revenue": rev,
            "Cost of sales": cos,
            "Gross margin": rev - cos,
            "Gross margin %": round((rev - cos) / rev * 100, 1) if rev else 0.0,
            "Operating expenses": opx,
            "Operating income": rev - cos - opx,
        }
    return out


def account_variances(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in frame.iterrows():
        var = r["actual"] - r["budget"]
        pct = var / r["budget"] * 100 if r["budget"] else 0.0
        is_cost = r["category"] in COST_CATEGORIES
        favorable = (var < 0) if is_cost else (var > 0)
        rows.append({
            "account": r["account"],
            "category": r["category"],
            "actual": int(r["actual"]),
            "budget": int(r["budget"]),
            "prior_year": int(r["prior_year"]),
            "var_vs_budget": int(var),
            "var_pct": round(pct, 1),
            "var_vs_py_pct": round((r["actual"] - r["prior_year"]) / r["prior_year"] * 100, 1),
            "favorable": bool(favorable),
            "material": abs(pct) >= MATERIAL_PCT and abs(var) >= MATERIAL_USD,
        })
    return sorted(rows, key=lambda x: abs(x["var_vs_budget"]), reverse=True)


# ---------- 2. THE AI (commentary only) ----------
def write_commentary(month: str, facts: dict) -> str:
    import anthropic

    client = anthropic.Anthropic()
    prompt = f"""You are an FP&A analyst writing the monthly flash report commentary
for leadership of a farming company, for {month}.

Rules:
- Use ONLY the numbers in the JSON below. Never calculate new numbers.
- Round dollars to the nearest $K (e.g. $123K) or $M with one decimal.
- Lead with the bottom line: operating income vs budget, month and year to date.
- Then 3-5 bullets on the material variances (material=true), biggest first.
  Say favorable/unfavorable, and give a plausible business driver phrased as
  a question to confirm with the owner (e.g. "confirm with ops: diesel prices?").
- End with 1-2 "watch items" for next month.
- Plain business English, under 250 words. Markdown.

DATA:
{json.dumps(facts, indent=1)}"""

    resp = client.messages.create(
        model=MODEL, max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# ---------- 3. THE GUARDRAIL (catch made-up numbers) ----------
def unverified_figures(text: str, facts: dict) -> list[str]:
    """Return $ figures in the commentary that don't match any real number (within rounding)."""
    known = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            known.append(abs(float(x)))
    walk(facts)

    bad = []
    for m in re.finditer(r"\$\s?([\d,.]+)\s?([KkMm]?)", text):
        num = float(m.group(1).replace(",", "") or 0)
        mult = {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)
        val = num * mult
        tol = max(0.5 * mult, val * 0.06)  # allow for rounding
        if not any(abs(val - k) <= tol for k in known):
            bad.append(m.group(0))
    return bad


# ---------- 4. BUILD THE REPORT ----------
def money(x):
    sign = "-" if x < 0 else ""
    x = abs(x)
    return f"{sign}${x/1e6:,.2f}M" if x >= 1e6 else f"{sign}${x/1e3:,.0f}K"


def pnl_table(title: str, s: dict) -> str:
    lines = [f"### {title}", "",
             "| Line | Actual | Budget | Var vs Budget | Prior Year | Var vs PY |",
             "|---|---:|---:|---:|---:|---:|"]
    for line in ["Revenue", "Cost of sales", "Gross margin", "Operating expenses", "Operating income"]:
        a, b, p = s["actual"][line], s["budget"][line], s["prior_year"][line]
        lines.append(f"| {line} | {money(a)} | {money(b)} | {money(a-b)} | {money(p)} | {money(a-p)} |")
    lines.append(f"| Gross margin % | {s['actual']['Gross margin %']}% | {s['budget']['Gross margin %']}% | "
                 f"{round(s['actual']['Gross margin %']-s['budget']['Gross margin %'],1)} pts | "
                 f"{s['prior_year']['Gross margin %']}% | "
                 f"{round(s['actual']['Gross margin %']-s['prior_year']['Gross margin %'],1)} pts |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month")
    ap.add_argument("--no-ai", action="store_true")
    args = ap.parse_args()

    month, mtd, ytd = load(args.month)
    facts = {
        "month": month,
        "month_summary": summarize(mtd),
        "ytd_summary": summarize(ytd),
        "month_account_variances": account_variances(mtd),
        "ytd_account_variances": account_variances(ytd),
    }

    material = [v for v in facts["month_account_variances"] if v["material"]]
    flags = ["| Account | Actual | Budget | Variance | % | Fav/Unfav |", "|---|---:|---:|---:|---:|---|"]
    for v in material:
        flags.append(f"| {v['account']} | {money(v['actual'])} | {money(v['budget'])} | "
                     f"{money(v['var_vs_budget'])} | {v['var_pct']}% | "
                     f"{'Favorable' if v['favorable'] else 'Unfavorable'} |")

    commentary = "_AI commentary skipped (--no-ai)._"
    warning = ""
    if not args.no_ai:
        commentary = write_commentary(month, facts)
        bad = unverified_figures(commentary, facts)
        if bad:
            warning = ("\n> ⚠️ **Check these figures** — they don't match the data: "
                       + ", ".join(sorted(set(bad))) + "\n")

    report = f"""# Flash Report — {month}

## Commentary
{commentary}
{warning}
## P&L summary
{pnl_table("Month", facts["month_summary"])}

{pnl_table("Year to date", facts["ytd_summary"])}

## Material variances this month (>{MATERIAL_PCT:.0f}% and >{money(MATERIAL_USD)})
{chr(10).join(flags) if material else "None."}
"""
    out = f"flash_report_{month}.md"
    with open(out, "w") as f:
        f.write(report)
    print(report)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
