# Key sync investigation — progress (2026-07-20)

## Done
- Root cause: batch webhook `sync_tags` + `autoflush=False` → uk_tag_project IntegrityError → keys rollback
- Fix in `app/api/router/lokalise.py` (tag session cache + error labeling)
- Backfill recent 5000: missing **513** (company* 96), all inserted; prod restarted 15:28
- Intermediate sync dumps/logs/script removed; also historical `key_list/`, `import_keys.*`, `migrate_tags.*`
