"""
Download OFFICIAL Swedish salary statistics from Statistics Sweden (SCB) for the
IT occupations the dashboard covers, and save them as a dbt seed.

Why: Swedish job ads almost never publish pay ("lön enligt överenskommelse"),
so the real-data dashboard shows SCB's measured salaries per occupation instead.

Source: SCB table AM0110A/LoneSpridSektYrk4AN — "Average salary and salary
dispersion by sector, occupation (SSYK 2012) and sex" (open data, no key).
All sectors, men + women, latest year available.

SCB publishes once a year (June), so run this yearly, then `dbt seed`:
    python ingestion/fetch_scb_salaries.py

Output: dbt_project/seeds/scb_salaries.csv
"""

import csv
import json
import urllib.request
from pathlib import Path

API = "https://api.scb.se/OV0104/v1/doris/en/ssd/AM/AM0110/AM0110A/LoneSpridSektYrk4AN"
HEADERS = {"User-Agent": "job-market-skills-analyzer (student project)",
           "Content-Type": "application/json"}

# SSYK 2012 occupation codes used by seeds/role_occupation.csv
OCCUPATIONS = ["2511", "2512", "2514", "2515", "2516", "2519", "2173", "3512"]

MEASURES = {                 # SCB content code -> our column name
    "000007CD": "avg_monthly_sek",
    "000007CE": "median_monthly_sek",
    "000007CF": "p10_monthly_sek",
    "000007CG": "p25_monthly_sek",
    "000007CH": "p75_monthly_sek",
    "000007CI": "p90_monthly_sek",
}

OUT = Path(__file__).resolve().parents[1] / "dbt_project" / "seeds" / "scb_salaries.csv"


def get(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8-sig"))


def main():
    meta = get(API)
    variables = {v["code"]: v for v in meta["variables"]}
    latest_year = max(variables["Tid"]["values"])
    names = dict(zip(variables["Yrke2012"]["values"], variables["Yrke2012"]["valueTexts"]))

    query = {
        "query": [
            {"code": "Sektor", "selection": {"filter": "item", "values": ["0"]}},          # all sectors
            {"code": "Yrke2012", "selection": {"filter": "item", "values": OCCUPATIONS}},
            {"code": "Kon", "selection": {"filter": "item", "values": ["1+2"]}},           # men + women
            {"code": "ContentsCode", "selection": {"filter": "item", "values": list(MEASURES)}},
            {"code": "Tid", "selection": {"filter": "item", "values": [latest_year]}},
        ],
        "response": {"format": "json"},
    }
    result = get(API, query)

    columns = [c["code"] for c in result["columns"]]
    content_codes = [c["code"] for c in result["columns"] if c.get("type") == "c"]
    rows = {}
    for item in result["data"]:
        key = dict(zip(columns, item["key"]))
        code = key["Yrke2012"]
        row = rows.setdefault(code, {"ssyk_code": code, "occupation": names[code].strip(),
                                     "year": int(latest_year)})
        for content_code, value in zip(content_codes, item["values"]):
            row[MEASURES[content_code]] = int(value) if value.strip().isdigit() else ""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ssyk_code", "occupation", "year", *MEASURES.values()]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for code in OCCUPATIONS:
            if code in rows:
                writer.writerow(rows[code])
    print(f"wrote {len(rows)} occupations for {latest_year} -> {OUT}")


if __name__ == "__main__":
    main()
