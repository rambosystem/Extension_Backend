# Key sync investigation — progress (2026-07-20)

## Verdict
`company*` keys missing from DB is **not** a prefix filter. Root cause: batch webhook `project.keys.added` fails when multiple keys share a **new** tag, because `Session(autoflush=False)` + `sync_tags` re-INSERTs the same tag → `uk_tag_project` IntegrityError → **entire key batch rolls back**.

## Evidence
- DB: `company%` = 0; only related: `Company Board`, `comkey1..13`, `commercekey*`
- JSON dumps (`key_list/`): also 0 `company*` (never in historical import)
- Access log: client searched `company` / `company001` / `company94..96` on Common + `search-by-names` → not found
- Live repro (before fix): batch add `company94/95` with shared new tag `test-sync` → HTTP 200 but `success=false`, IntegrityError on `lokalise_tags.uk_tag_project`
- Single `project.key.added` works; AmazonSearch still syncing (latest `wmtkey700` 2026-07-17)

## Root cause detail
1. `app/db/database.py`: `sessionmaker(..., autoflush=False)`
2. `sync_tags()`: for each key, query tag; if missing `db.add(new_tag)` without session cache
3. Same-request 2nd key: SELECT sees no unflushed tag → second INSERT → commit IntegrityError
4. `handle_keys_added` re-raises → outer webhook handler returned **mislabeled** `Invalid JSON format: ...` and HTTP 200 → Lokalise does not retry → keys lost forever unless re-imported

## Fix applied (code, needs restart)
File: `app/api/router/lokalise.py`
- `sync_tags`: session cache `db.info['_lokalise_tag_cache']` so each (project_id, tag_name) created once per transaction; usage_count increments correctly
- webhook: separate JSON-parse vs processing errors (no longer label DB failures as Invalid JSON)
- Verified offline: batch `company94/95/96` + new tag commits OK, usage_count=3

## Deploy / recovery (pending user)
1. Restart production (`./restart_production.sh`) — gunicorn `preload_app=True`, code not live until restart
2. Re-sync missing company keys from Lokalise (re-export/import or re-fire webhooks / modify keys). Already-failed webhooks will not replay.

## Sync architecture (unchanged)
- Write: Lokalise webhook → `lokalise_keys` (+ `lokalise_tags` side-effect)
- Batch: `import_keys.py` from `key_list/*.json`
- Autocomplete read filter: `is_single_word=1` only (does **not** block insert; `company001` would be autocompleteable if stored)
