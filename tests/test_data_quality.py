"""
Data quality tests for generated raw datasets.
"""

from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def users():
    path = RAW_DIR / "dim_users.parquet"

    if not path.exists():
        pytest.skip("Raw users data not found. Run `make generate` first.")

    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def events():
    path = RAW_DIR / "fact_events.parquet"

    if not path.exists():
        pytest.skip("Raw events data not found. Run `make generate` first.")

    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def subscriptions():
    path = RAW_DIR / "fact_subscriptions.parquet"

    if not path.exists():
        pytest.skip(
            "Raw subscriptions data not found. Run `make generate` first."
        )

    return pd.read_parquet(path)


class TestRawUsers:

    def test_expected_row_count(self, users):
        assert len(users) == 100_000

    def test_user_ids_unique(self, users):
        assert users["user_id"].is_unique

    def test_user_ids_not_null(self, users):
        assert users["user_id"].notna().all()

    def test_signup_dates_not_null(self, users):
        assert users["signup_date"].notna().all()

    def test_no_duplicate_users(self, users):
        assert users.duplicated("user_id").sum() == 0


class TestRawEvents:

    def test_events_not_empty(self, events):
        assert len(events) > 0

    def test_event_ids_unique(self, events):
        assert events["event_id"].is_unique

    def test_event_user_ids_not_null(self, events):
        assert events["user_id"].notna().all()

    def test_event_names_not_null(self, events):
        assert events["event_name"].notna().all()


class TestRawSubscriptions:

    def test_one_subscription_per_user(self, subscriptions):
        assert subscriptions["user_id"].is_unique

    def test_subscription_user_ids_not_null(self, subscriptions):
        assert subscriptions["user_id"].notna().all()

    def test_mrr_non_negative(self, subscriptions):
        assert (subscriptions["mrr"] >= 0).all()

    def test_subscription_dates_are_valid(self, subscriptions):
        paid = subscriptions[
            subscriptions["paid_start_date"].notna()
        ]

        if not paid.empty:
            assert (
                pd.to_datetime(paid["paid_start_date"])
                <= pd.Timestamp("2025-12-31")
            ).all()
