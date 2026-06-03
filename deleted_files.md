# Deleted Files Report

Generated: 2026-06-03

## Scope

This cleanup only processed `Deletion Risk = Low` items from `cleanup_report.md` and did not modify forbidden areas: `app/services`, `app/scoring`, `app/agent`, `app/api`, or `frontend`.

## Deleted files

| File | Reason | Reference chain proof |
| --- | --- | --- |
| None | `cleanup_report.md` did not identify any whole-file candidate with an unqualified `Deletion risk = Low`. The only strict Low item was the unused `SignalItem` schema inside `app/schemas.py`, while that file still contains active response schemas. | `cleanup_report.md` marks `SignalItem` as Low risk, but the same file also contains `HealthResponse`, `SystemStatusResponse`, and `UniverseItem`, which are imported by API routes. |

## Low-risk removals performed

| File | Removed item | Reason | Reference chain proof |
| --- | --- | --- | --- |
| `app/schemas.py` | `SignalItem` class | Static analysis found no references outside its own definition. | `cleanup_report.md` states `SignalItem` is not referenced by `app/api/*`, services, or tests. |
| `.env.example` | `APP_HOST`, `APP_PORT` | Static analysis classified these example environment variables as Low-risk stale config because runtime binding is controlled by the process runner. | `cleanup_report.md` states no code reads `settings.app_host` or `settings.app_port`; README now documents using `uvicorn --host/--port`. |
| `app/config.py` | `app_host`, `app_port` settings fields | Removed the corresponding stale settings fields while preserving tolerance for old local `.env` files via `extra="ignore"`. | `rg` found no references to `app_host` or `app_port` outside config/example/report before removal. |
| `README.md` | Added cleanup note | Documents the supported host/port launch style after removing stale env examples. | README now shows `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`. |

## Requirements cleanup

No Python or frontend dependencies were tied exclusively to the Low-risk removals, so no `requirements.txt` or frontend package entries were removed.
