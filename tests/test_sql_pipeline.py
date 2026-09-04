"""Integration test for the DuckDB SQL pipeline.

Runs the full staging + mart SQL against the already-generated data
and validates mart output shapes and key invariants.
"""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql"

STAGING_ORDER = ["stg_users", "stg_events", "stg_subscriptions", "stg_experiments"]
MART_ORDER = ["mart_funnel", "mart_cohort_retention", "mart_experiment_results", "mart_product_growth_daily",
              "mart_customer_intelligence", "mart_revenue_risk",]


@pytest.fixture(scope="module")
def duckdb_con():
    """Build a DuckDB connection with all staging + mart models loaded."""
    con = duckdb.connect(":memory:")

    for table_name, filename in {
        "raw_dim_users": "dim_users.parquet",
        "raw_fact_events": "fact_events.parquet",
        "raw_fact_subscriptions": "fact_subscriptions.parquet",
        "raw_fact_experiments": "fact_experiments.parquet",
    }.items():
        path = RAW_DIR / filename
        if not path.exists():
            pytest.skip(f"Raw data not found at {path}. Run `make generate` first.")
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')")

    for name in STAGING_ORDER:
        sql = (SQL_DIR / "staging" / f"{name}.sql").read_text()
        con.execute(sql)

    for name in MART_ORDER:
        sql = (SQL_DIR / "marts" / f"{name}.sql").read_text()
        con.execute(sql)

    yield con
    con.close()


class TestMartFunnel:
    def test_has_rollup_row(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        rollup = df[df["acquisition_channel"].isna()]
        assert len(rollup) == 1

    def test_has_channel_rows(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        channels = df.dropna(subset=["acquisition_channel"])
        assert len(channels) >= 2

    def test_funnel_monotonically_decreasing(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        rollup = df[df["acquisition_channel"].isna()].iloc[0]
        steps = ["signup_users", "workspace_users", "invite_users", "project_users", "paid_users"]
        values = [rollup[s] for s in steps]
        for i in range(1, len(values)):
            assert values[i] <= values[i - 1], f"{steps[i]} ({values[i]}) > {steps[i-1]} ({values[i-1]})"


class TestMartCohortRetention:
    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        assert len(df) > 0

    def test_retention_rate_between_zero_and_one(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        assert df["retention_rate"].min() >= 0
        assert df["retention_rate"].max() <= 1.0

    def test_week_zero_retention_highest(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        for cohort, group in df.groupby("cohort_week"):
            w0 = group[group["weeks_since_signup"] == 0]["retention_rate"].iloc[0]
            later = group[group["weeks_since_signup"] > 0]["retention_rate"]
            if len(later) > 0:
                assert w0 >= later.min(), f"Cohort {cohort}: W0 ({w0}) < later min ({later.min()})"


class TestMartExperimentResults:
    def test_two_variants(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_experiment_results").fetchdf()
        assert set(df["variant"]) == {"control", "treatment"}

    def test_activation_rate_valid(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_experiment_results").fetchdf()
        for _, row in df.iterrows():
            assert 0 <= row["activation_rate"] <= 1.0


class TestMartProductGrowthDaily:
    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily").fetchdf()
        assert len(df) > 100

    def test_mrr_non_negative(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily").fetchdf()
        assert (df["mrr"] >= 0).all()

    def test_dates_are_ordered(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily ORDER BY metric_date").fetchdf()
        dates = pd.to_datetime(df["metric_date"])
        assert dates.is_monotonic_increasing
# ── Customer Intelligence ────────────────────────────────────────────────────


class TestMartCustomerIntelligence:

    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute(
            "SELECT * FROM mart_customer_intelligence"
        ).fetchdf()

        assert len(df) > 0

    def test_one_row_per_customer(self, duckdb_con):
        df = duckdb_con.execute(
            "SELECT * FROM mart_customer_intelligence"
        ).fetchdf()

        assert df["user_id"].is_unique

    def test_matches_user_count(self, duckdb_con):
        user_count = duckdb_con.execute(
            "SELECT COUNT(*) FROM stg_users"
        ).fetchone()[0]

        customer_count = duckdb_con.execute(
            "SELECT COUNT(*) FROM mart_customer_intelligence"
        ).fetchone()[0]

        assert customer_count == user_count

    def test_engagement_score_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT engagement_score
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        assert df["engagement_score"].between(0, 100).all()

    def test_mrr_non_negative(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT mrr
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        assert (df["mrr"] >= 0).all()

    def test_customer_flags_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT is_paid, is_churned
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        assert set(df["is_paid"].unique()).issubset({0, 1})
        assert set(df["is_churned"].unique()).issubset({0, 1})

    def test_customer_segments_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT DISTINCT customer_segment
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        expected = {
            "Churned",
            "High Value",
            "Engaged",
            "At Risk",
            "Growth Opportunity",
            "Nurture",
            "Low Engagement",
        }

        assert set(df["customer_segment"]).issubset(expected)

    def test_revenue_segments_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT DISTINCT revenue_segment
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        expected = {
            "High Revenue",
            "Medium Revenue",
            "Low Revenue",
            "Non-Paying",
        }

        assert set(df["revenue_segment"]).issubset(expected)

    def test_engagement_segments_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT DISTINCT engagement_segment
            FROM mart_customer_intelligence
            """
        ).fetchdf()

        expected = {
            "Highly Engaged",
            "Moderately Engaged",
            "Low Engagement",
            "Inactive",
        }

        assert set(df["engagement_segment"]).issubset(expected)


# ── Revenue Risk ─────────────────────────────────────────────────────────────


class TestMartRevenueRisk:

    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute(
            "SELECT * FROM mart_revenue_risk"
        ).fetchdf()

        assert len(df) > 0

    def test_same_customer_count_as_customer_mart(self, duckdb_con):
        customer_count = duckdb_con.execute(
            "SELECT COUNT(*) FROM mart_customer_intelligence"
        ).fetchone()[0]

        risk_count = duckdb_con.execute(
            "SELECT COUNT(*) FROM mart_revenue_risk"
        ).fetchone()[0]

        assert risk_count == customer_count

    def test_churn_probability_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT estimated_churn_probability
            FROM mart_revenue_risk
            """
        ).fetchdf()

        assert df["estimated_churn_probability"].between(0, 1).all()

    def test_revenue_at_risk_non_negative(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT revenue_at_risk
            FROM mart_revenue_risk
            """
        ).fetchdf()

        assert (df["revenue_at_risk"] >= 0).all()

    def test_risk_tiers_valid(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT DISTINCT revenue_risk_tier
            FROM mart_revenue_risk
            """
        ).fetchdf()

        expected = {
            "High",
            "Medium",
            "Low",
        }

        assert set(df["revenue_risk_tier"]).issubset(expected)

    def test_revenue_at_risk_formula(self, duckdb_con):
        df = duckdb_con.execute(
            """
            SELECT
                mrr,
                estimated_churn_probability,
                revenue_at_risk
            FROM mart_revenue_risk
            """
        ).fetchdf()

        expected = (
            df["mrr"]
            * df["estimated_churn_probability"]
        ).round(2)

        assert (
            df["revenue_at_risk"] == expected
        ).all()
