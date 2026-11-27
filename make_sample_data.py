"""Creates fake monthly P&L data for a made-up company (Sunridge Farms) to practice on."""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
accounts = [  # account, category, monthly budget base, seasonality on/off
    ("Citrus sales", "Revenue", 1_200_000, True),
    ("Grape sales", "Revenue", 800_000, True),
    ("Harvest labor", "Cost of sales", 420_000, True),
    ("Packing materials", "Cost of sales", 150_000, True),
    ("Fuel & diesel", "Cost of sales", 60_000, False),
    ("Chemicals & fertilizer", "Cost of sales", 95_000, False),
    ("Salaries & benefits", "Operating expenses", 260_000, False),
    ("Repairs & maintenance", "Operating expenses", 55_000, False),
    ("Utilities", "Operating expenses", 38_000, False),
    ("Insurance", "Operating expenses", 22_000, False),
]
season = [0.9, 0.85, 0.8, 0.75, 0.8, 0.95, 1.1, 1.25, 1.3, 1.2, 1.05, 0.95]
rows = []
for m in range(1, 11):  # Jan-Oct 2026
    for acct, cat, base, seas in accounts:
        f = season[m - 1] if seas else 1.0
        budget = base * f
        prior = budget * rng.normal(0.95, 0.04)
        actual = budget * rng.normal(1.0, 0.025)
        # a few real "stories" for the commentary to find
        if acct == "Fuel & diesel" and m >= 9: actual = budget * (1.18 if m == 9 else 1.27)
        if acct == "Harvest labor" and m == 10: actual = budget * 1.14
        if acct == "Grape sales" and m == 10: actual = budget * 1.11
        if acct == "Repairs & maintenance" and m == 10: actual = budget * 1.42
        if acct == "Citrus sales" and m == 10: actual = budget * 0.93
        rows.append({"month": f"2026-{m:02d}", "account": acct, "category": cat,
                     "actual": round(actual), "budget": round(budget), "prior_year": round(prior)})
pd.DataFrame(rows).to_csv("pl_monthly.csv", index=False)
print("wrote pl_monthly.csv")
