"""
Download REAL Swedish job ads from Arbetsförmedlingen's open JobTech API
(https://jobsearch.api.jobtechdev.se — free, no API key, open data) and write
them in the same format as the synthetic data, so the rest of the pipeline
(Snowflake load -> dbt -> dashboard) works unchanged.

By default it fetches every live ad in the "Data/IT" occupation field
(about 3 000 ads). The API only pages up to offset 2 000, so we page backwards
through publication dates.

Usage:
    python ingestion/fetch_jobtech.py                    # all live Data/IT ads
    python ingestion/fetch_jobtech.py --max-ads 500      # quick test

Output: data/jobtech_sweden.csv
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://jobsearch.api.jobtechdev.se/search"
DATA_IT_FIELD = "apaJ_2ja_LuF"          # taxonomy concept id of the "Data/IT" occupation field
PAGE = 100                              # max page size allowed by the API
MAX_OFFSET = 2000                       # API limit for offset
COLUMNS = ["job_id", "job_title", "company_name", "location", "experience_required",
           "salary_range", "work_mode", "posted_date", "job_description", "source_site"]

# "5+ års erfarenhet", "minst 3 år erfarenhet", "3 years of experience"
EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:års?|years?)[^.\n]{0,40}?(?:erfarenhet|experience)",
    re.IGNORECASE)


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"accept": "application/json",
                                               "User-Agent": "job-market-skills-analyzer (student project)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as exc:                       # network hiccup -> retry politely
            if attempt == 3:
                raise
            print(f"  retrying after error: {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def experience_text(hit, description):
    if hit.get("experience_required") is False:
        return "Entry level"                           # "Ingen erfarenhet krävs"
    m = EXPERIENCE_RE.search(description or "")
    if m and int(m.group(1)) <= 15:
        return f"{int(m.group(1))}+ years"
    return "Experience required"                       # dbt turns this into 'Unknown'


def work_mode(hit, description):
    if hit.get("remote_work"):
        return "Remote"
    text = (description or "").lower()
    if "hybrid" in text or "delvis distans" in text:
        return "Hybrid"
    return "On-site"


def to_row(hit):
    addr = hit.get("workplace_address") or {}
    if addr.get("country_code") not in (None, "199"):  # 199 = Sverige; skip ads abroad
        return None
    place = addr.get("municipality") or addr.get("city") or addr.get("region") or "Unspecified"
    description = (hit.get("description") or {}).get("text") or ""
    return {
        "job_id": f"AF{hit['id']}",
        "job_title": hit.get("headline") or "",
        "company_name": (hit.get("employer") or {}).get("name") or "",
        "location": f"{place}, Sweden",
        "experience_required": experience_text(hit, description),
        "salary_range": hit.get("salary_description") or "Not disclosed",
        "work_mode": work_mode(hit, description),
        "posted_date": (hit.get("publication_date") or "")[:10],
        "job_description": description,
        "source_site": "jobtech",
    }


def fetch(max_ads):
    rows, seen = [], set()
    published_before = None
    last_date = None
    while True:
        new_in_window = 0
        for offset in range(0, MAX_OFFSET, PAGE):
            params = {"occupation-field": DATA_IT_FIELD, "sort": "pubdate-desc",
                      "limit": PAGE, "offset": offset}
            if published_before:
                params["published-before"] = published_before
            hits = get(params).get("hits", [])
            for hit in hits:
                if hit["id"] in seen:
                    continue
                seen.add(hit["id"])
                row = to_row(hit)
                if row:
                    rows.append(row)
                    new_in_window += 1
            if hits:
                last_date = hits[-1].get("publication_date")
            print(f"  fetched {len(rows):5d} ads", end="\r", flush=True)
            if len(rows) >= max_ads or len(hits) < PAGE:
                return rows[:max_ads]
            time.sleep(0.2)                            # be polite to the free API
        if new_in_window == 0 or not last_date:
            return rows
        published_before = last_date                   # next window: older ads


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-ads", type=int, default=20000)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent.parent / "data" / "jobtech_sweden.csv")
    args = parser.parse_args()

    print("Downloading live Data/IT job ads from Arbetsförmedlingen (JobTech API) ...")
    rows = fetch(args.max_ads)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} real ads to {args.out}")


if __name__ == "__main__":
    main()
