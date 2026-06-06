# Seed Report

Date: 2026-06-06

## Tables seeded

| Table | Before count | After count | Rows inserted |
| --- | ---: | ---: | ---: |
| historical_matches | 964 | 1928 | 964 |

## Additional fixture count

| Table | Count | Notes |
| --- | ---: | --- |
| matches | 8 | Fixture table was queried for visibility, but the importer did not touch this table. |

## Rows skipped

None reported by the importer.

## Notes

- The existing importer was run unchanged against production Supabase using the configured service-role key.
- The direct invocation `venv/bin/python scripts/import_historical_matches.py` failed before any database write because Python could not resolve `app.core.logging` from the script entrypoint.
- The same script file was then run unchanged with `PYTHONPATH=.` so local imports resolved.
- The importer does not deduplicate existing historical matches, so it inserted another 964 rows on top of the 964 rows already present.
