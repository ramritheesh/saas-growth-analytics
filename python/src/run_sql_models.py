"""Execute SQL staging views and mart tables via DuckDB.

Reads raw Parquet files, runs staging SQL to create views,
then runs mart SQL to create tables, and exports each mart
as a Parquet file to data/processed/.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

RAW_TABLES = {
    "raw_dim_users": "dim_users.parquet",
    "raw_fact_events": "fact_events.parquet",
    "raw_fact_subscriptions": "fact_subscriptions.parquet",
    "raw_fact_experiments": "fact_experiments.parquet",
}

STAGING_ORDER = [
    "stg_users",
    "stg_events",
    "stg_subscriptions",
    "stg_experiments",
]

MART_ORDER = [
    "mart_funnel",
    "mart_cohort_retention",
    "mart_experiment_results",
    "mart_product_growth_daily",
    "mart_customer_intelligence",
    "mart_revenue_risk",
]


def _register_raw_tables(con: duckdb.DuckDBPyConnection) -> None:
    for table_name, filename in RAW_TABLES.items():
        path = RAW_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing raw data: {path}. Run `make generate` first.")
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')")
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  Registered {table_name}: {count:,} rows")


def _run_sql_files(con: duckdb.DuckDBPyConnection, folder: str, names: list[str]) -> None:
    sql_folder = SQL_DIR / folder
    for name in names:
        sql_path = sql_folder / f"{name}.sql"
        sql = sql_path.read_text()
        con.execute(sql)
        print(f"  Executed {folder}/{name}.sql")


def _export_marts(con: duckdb.DuckDBPyConnection) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for mart in MART_ORDER:
        out_path = PROCESSED_DIR / f"{mart}.parquet"
        con.execute(f"COPY {mart} TO '{out_path}' (FORMAT PARQUET)")
        count = con.execute(f"SELECT COUNT(*) FROM {mart}").fetchone()[0]
        print(f"  Exported {mart}: {count:,} rows -> {out_path}")


def main() -> None:
    con = duckdb.connect(":memory:")

    print("Loading raw Parquet files into DuckDB...")
    _register_raw_tables(con)

    print("\nRunning staging models...")
    _run_sql_files(con, "staging", STAGING_ORDER)

    print("\nRunning mart models...")
    _run_sql_files(con, "marts", MART_ORDER)

    print("\nExporting marts to Parquet...")
    _export_marts(con)

    con.close()
    print("\nDone. Processed data in", PROCESSED_DIR)


if __name__ == "__main__":
    main()
