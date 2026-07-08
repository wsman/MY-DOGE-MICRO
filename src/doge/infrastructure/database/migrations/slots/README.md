# Slot Migrations

Slot SQLite migrations are registered in
`src/doge/infrastructure/database/migration_runner.py`.

This package-local directory is the ownership marker for Slot Platform local
state such as persisted bundle activation. `agent_schema.sql` remains a
bootstrap snapshot for fresh local databases.
