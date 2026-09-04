"""Cached data loaders for Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@st.cache_data
def load_funnel() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "mart_funnel.parquet")


@st.cache_data
def load_cohort_retention() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "mart_cohort_retention.parquet")


@st.cache_data
def load_experiment_results() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "mart_experiment_results.parquet")


@st.cache_data
def load_daily_growth() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / "mart_product_growth_daily.parquet")
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    return df


@st.cache_data
def load_churn_scores() -> pd.DataFrame:
    from python.src.analysis import score_churn_risk
    return score_churn_risk()

@st.cache_data
def load_customer_intelligence() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "mart_customer_intelligence.parquet")
