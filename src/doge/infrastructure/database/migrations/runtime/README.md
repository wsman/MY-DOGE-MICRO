# Runtime Migrations

Runtime SQLite migrations are registered in
`src/doge/infrastructure/database/migration_runner.py`.

This source-local directory is the ownership marker for run, session, event,
approval, outbox, and queue migrations. `agent_schema.sql` remains a bootstrap
snapshot for fresh local databases.
