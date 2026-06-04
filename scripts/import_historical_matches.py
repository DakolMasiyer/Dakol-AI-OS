#!/usr/bin/env python3
"""
Dakol AI OS — Historical Matches Importer
Downloads men's international results CSV from GitHub and seeds the Supabase
'historical_matches' table with all past FIFA World Cup results (1930-2022).
"""

import os
import csv
import urllib.request
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def download_csv(url: str) -> str:
    print(f"Downloading CSV from: {url} ...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_and_seed():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        return

    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)

    # 1. Download data
    try:
        csv_data = download_csv(CSV_URL)
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return

    # 2. Parse matches
    lines = csv_data.strip().split("\n")
    reader = csv.DictReader(lines)

    matches_to_insert = []
    print("Parsing matches...")

    for row in reader:
        # We only want final tournament FIFA World Cup matches
        if row.get("tournament", "").lower() != "fifa world cup":
            continue

        try:
            date_str = row.get("date")
            year = int(date_str.split("-")[0]) if date_str else 1930
            # Skip future years if any
            if year >= 2026:
                continue

            neutral_val = row.get("neutral", "true").lower() == "true"

            matches_to_insert.append({
                "year": year,
                "date": date_str,
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "home_score": int(row.get("home_score", 0)),
                "away_score": int(row.get("away_score", 0)),
                "tournament": row.get("tournament"),
                "city": row.get("city"),
                "country": row.get("country"),
                "neutral": neutral_val
            })
        except Exception as ex:
            print(f"Skipping line due to parse error: {ex}")

    total_parsed = len(matches_to_insert)
    print(f"Parsed {total_parsed} historical World Cup matches.")

    if total_parsed == 0:
        print("No matches found to insert.")
        return

    # 3. Seed Supabase in batches of 100
    batch_size = 100
    inserted = 0

    print("Uploading to Supabase...")
    for i in range(0, total_parsed, batch_size):
        batch = matches_to_insert[i:i + batch_size]
        try:
            res = supabase.table("historical_matches").insert(batch).execute()
            inserted += len(batch)
            print(f"Inserted batch {i // batch_size + 1}: {inserted}/{total_parsed} matches uploaded.")
        except Exception as e:
            print(f"Failed to insert batch starting at index {i}: {e}")
            print("Verify you have run the database migrations and created the 'historical_matches' table.")
            return

    print(f"Successfully seeded {inserted} historical matches into Supabase!")


if __name__ == "__main__":
    parse_and_seed()
