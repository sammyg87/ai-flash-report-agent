# AI Flash Report Agent

An AI agent that turns a month of P&L data into a leadership-ready **flash report**: P&L summary, variance analysis against budget and prior year, and written commentary, in seconds instead of hours.

Built by **Samuel Gonzalez**, Farm Analyst moving into FP&A.

---

## The problem

Every month-end, an analyst pulls actuals, compares them to budget and prior year, finds the variances that matter, and writes commentary explaining them. The math is repetitive, and the writing takes time. That's exactly the kind of work an agent can draft so the analyst can spend their time checking the drivers.

## How it works

The key design choice: **code does the math, AI does the writing, and a check keeps the AI honest.**

```
pl_monthly.csv ──► 1. Python / pandas ──► 2. Claude ──► 3. Guardrail ──► flash_report.md
                   all calculations       commentary      flags any $
                   MTD + YTD variances     from those      figure that
                   materiality flags       numbers only    isn't in the data
```

1. **Calculations (pandas).** Rolls accounts into P&L lines (Revenue, Cost of sales, Gross margin, OpEx, Operating income) for the month and year to date. Computes variances against budget and prior year, and marks each one favorable or unfavorable. Cost accounts are favorable when under budget.
2. **Materiality.** Flags only variances that are both **> 5%** and **> $10K**, the same filter an analyst applies by eye.
3. **Commentary (Claude API).** The model gets the computed numbers as JSON and is told never to calculate. It leads with the bottom line, explains the material variances, and turns likely drivers into questions to confirm with the account owner.
4. **Guardrail.** Every dollar figure in the commentary is checked against the real numbers, allowing for rounding. Anything that doesn't match is flagged with ⚠️ in the report.

## Sample output (October 2026, fictional data)

**Month P&L**

| Line | Actual | Budget | Var vs Budget | Prior Year | Var vs PY |
|---|---:|---:|---:|---:|---:|
| Revenue | $2.40M | $2.40M | $5K | $2.28M | $126K |
| Cost of sales | $931K | $839K | $92K | $798K | $133K |
| Gross margin | $1.47M | $1.56M | -$87K | $1.48M | -$7K |
| Operating expenses | $399K | $375K | $24K | $368K | $31K |
| Operating income | $1.07M | $1.19M | -$111K | $1.11M | -$37K |
| Gross margin % | 61.3% | 65.0% | -3.7 pts | 65.0% | -3.7 pts |

**Material variances flagged**

| Account | Actual | Budget | Variance | % | Fav/Unfav |
|---|---:|---:|---:|---:|---|
| Grape sales | $1.07M | $960K | $106K | 11.0% | Favorable |
| Citrus sales | $1.34M | $1.44M | -$101K | -7.0% | Unfavorable |
| Harvest labor | $575K | $504K | $71K | 14.0% | Unfavorable |
| Repairs & maintenance | $78K | $55K | $23K | 42.0% | Unfavorable |
| Fuel & diesel | $76K | $60K | $16K | 27.0% | Unfavorable |

**AI commentary**

> _Paste the Commentary section from your `flash_report_2026-10.md` here._

See [`flash_report_2026-10.md`](flash_report_2026-10.md) for the full report.

## Run it yourself

```bash
pip3 install anthropic pandas
export ANTHROPIC_API_KEY="your-key"

python3 flash_report_agent.py                  # latest month in the data
python3 flash_report_agent.py --month 2026-09  # a specific month
python3 flash_report_agent.py --no-ai          # numbers only, no API key needed
```

The report is saved as `flash_report_<month>.md`.

## Files

| File | What it is |
|---|---|
| `flash_report_agent.py` | The agent: calculations, AI commentary, guardrail, report |
| `pl_monthly.csv` | Sample P&L data (Jan–Oct 2026) for **Sunridge Farms**, a made-up company |
| `make_sample_data.py` | Generates the sample data, including planted variances for the agent to find |
| `flash_report_2026-10.md` | Example output |

> All data is fictional. No real company figures are used.

## Using your own data

Swap in any CSV with these columns:

`month` (YYYY-MM) · `account` · `category` (Revenue / Cost of sales / Operating expenses) · `actual` · `budget` · `prior_year`

Materiality thresholds are set at the top of the script (`MATERIAL_PCT`, `MATERIAL_USD`).

## What I'd add next

- Rolling forecast: update the full-year outlook from actuals and explain what changed
- Excel output with formatted tables for finance teams that live in Excel
- Department-level drill-downs, and a check against the GL detail

## Tech

Python · pandas · Claude API (Anthropic) · Markdown output
