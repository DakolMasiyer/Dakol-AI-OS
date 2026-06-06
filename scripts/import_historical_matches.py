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
from app.core.logging import get_logger

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
logger = get_logger(__name__)


def download_csv(url: str) -> str:
    logger.info("Downloading historical matches CSV", extra={"url": url})
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
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        return

    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)

    # 1. Download data
    try:
        csv_data = download_csv(CSV_URL)
    except Exception as e:
        logger.error("Error downloading CSV", exc_info=True)
        return

    # 2. Parse matches
    lines = csv_data.strip().split("\n")
    reader = csv.DictReader(lines)

    matches_to_insert = []
    logger.info("Parsing historical matches")

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
            logger.warning("Skipping line due to parse error", exc_info=True)

    total_parsed = len(matches_to_insert)
    logger.info("Parsed historical World Cup matches", extra={"total_parsed": total_parsed})

    if total_parsed == 0:
        logger.info("No historical matches found to insert")
        return

    # 3. Seed Supabase in batches of 100
    batch_size = 100
    inserted = 0

    logger.info("Uploading historical matches to Supabase")
    for i in range(0, total_parsed, batch_size):
        batch = matches_to_insert[i:i + batch_size]
        try:
            res = supabase.table("historical_matches").insert(batch).execute()
            inserted += len(batch)
            logger.info(
                "Inserted historical matches batch",
                extra={
                    "batch": i // batch_size + 1,
                    "inserted": inserted,
                    "total_parsed": total_parsed,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to insert historical matches batch",
                extra={"batch_start_index": i},
                exc_info=True,
            )
            logger.error("Verify the database migrations created the historical_matches table")
            return

    logger.info("Successfully seeded historical matches into Supabase", extra={"inserted": inserted})


if __name__ == "__main__":
    parse_and_seed()
