from doge.infrastructure.database.sqlite import SQLiteConnection


def test_sqlite_connection_creates_missing_parent_directory(tmp_path):
    db_path = tmp_path / "missing" / "research_insights.db"

    with SQLiteConnection(db_path).connect() as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    assert db_path.exists()
