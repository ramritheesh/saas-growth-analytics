"""
Revenue Risk Intelligence Dashboard

Customer-level churn prediction, revenue exposure,
segmentation, and retention prioritization.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Revenue Risk Intelligence",
    page_icon="📊",
    layout="wide",
)


# =============================================================================
# DATA LOADING
# =============================================================================


@st.cache_data
def load_churn_predictions() -> pd.DataFrame:
    """
    Load the latest customer-level churn predictions.
    """

    path = (
        "data/processed/churn_predictions.parquet"
    )

    df = pd.read_parquet(path)

    return df


df = load_churn_predictions()


# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("Revenue Risk Intelligence")

st.caption(
    "Customer-level churn prediction, revenue exposure, "
    "segmentation, and retention prioritization"
)


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================

st.sidebar.header("Filters")


# -----------------------------------------------------------------------------
# Risk Tier
# -----------------------------------------------------------------------------

risk_options = [
    "All",
    "high",
    "medium",
    "low",
]

selected_risk = st.sidebar.selectbox(
    "Risk Tier",
    risk_options,
)


# -----------------------------------------------------------------------------
# Plan Type
# -----------------------------------------------------------------------------

plan_options = [
    "All"
] + sorted(
    df["plan_type"]
    .dropna()
    .unique()
    .tolist()
)

selected_plan = st.sidebar.selectbox(
    "Plan Type",
    plan_options,
)


# -----------------------------------------------------------------------------
# Industry
# -----------------------------------------------------------------------------

industry_options = [
    "All"
] + sorted(
    df["industry"]
    .dropna()
    .unique()
    .tolist()
)

selected_industry = st.sidebar.selectbox(
    "Industry",
    industry_options,
)


# -----------------------------------------------------------------------------
# Acquisition Channel
# -----------------------------------------------------------------------------

channel_options = [
    "All"
] + sorted(
    df["acquisition_channel"]
    .dropna()
    .unique()
    .tolist()
)

selected_channel = st.sidebar.selectbox(
    "Acquisition Channel",
    channel_options,
)


# -----------------------------------------------------------------------------
# Number of Accounts
# -----------------------------------------------------------------------------

accounts_to_display = st.sidebar.slider(
    "Accounts to display",
    min_value=10,
    max_value=100,
    value=25,
    step=5,
)


# =============================================================================
# APPLY FILTERS
# =============================================================================

filtered = df.copy()


if selected_risk != "All":
    filtered = filtered[
        filtered["risk_tier"]
        == selected_risk
    ]


if selected_plan != "All":
    filtered = filtered[
        filtered["plan_type"]
        == selected_plan
    ]


if selected_industry != "All":
    filtered = filtered[
        filtered["industry"]
        == selected_industry
    ]


if selected_channel != "All":
    filtered = filtered[
        filtered["acquisition_channel"]
        == selected_channel
    ]


# =============================================================================
# EMPTY FILTER STATE
# =============================================================================

if filtered.empty:

    st.warning(
        "No customers match the selected filters."
    )

    st.stop()


# =============================================================================
# CALCULATE KPI VALUES
# =============================================================================

customer_count = len(filtered)

total_mrr = filtered["mrr"].sum()

total_revenue_at_risk = (
    filtered["revenue_at_risk"].sum()
)

average_churn_probability = (
    filtered["churn_probability"].mean()
)

high_risk_count = (
    filtered["risk_tier"]
    .eq("high")
    .sum()
)


if total_mrr > 0:

    revenue_exposure_rate = (
        total_revenue_at_risk
        / total_mrr
    )

else:

    revenue_exposure_rate = 0


# =============================================================================
# KPI ROW
# =============================================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Customers",
        f"{customer_count:,}",
    )


with col2:

    st.metric(
        "Current MRR",
        f"${total_mrr:,.0f}",
    )


with col3:

    st.metric(
        "Modeled Revenue Exposure",
        f"${total_revenue_at_risk:,.0f}",
    )


with col4:

    st.metric(
        "Avg. Churn Probability",
        f"{average_churn_probability:.1%}",
    )


st.divider()


# =============================================================================
# RISK TIER SUMMARY
# =============================================================================

st.subheader(
    "Risk Exposure Overview"
)


risk_summary = (
    filtered
    .groupby(
        "risk_tier",
        observed=False,
    )
    .agg(
        customers=(
            "user_id",
            "count",
        ),
        current_mrr=(
            "mrr",
            "sum",
        ),
        revenue_at_risk=(
            "revenue_at_risk",
            "sum",
        ),
        avg_churn_probability=(
            "churn_probability",
            "mean",
        ),
    )
    .reset_index()
)


# =============================================================================
# RISK CHARTS
# =============================================================================

chart_col1, chart_col2 = st.columns(2)


with chart_col1:

    st.markdown(
        "**Modeled Revenue Exposure by Risk Tier**"
    )

    exposure_chart = (
        risk_summary
        .set_index("risk_tier")[
            "revenue_at_risk"
        ]
    )

    st.bar_chart(
        exposure_chart,
        use_container_width=True,
    )


with chart_col2:

    st.markdown(
        "**Customer Distribution by Risk Tier**"
    )

    customer_chart = (
        risk_summary
        .set_index("risk_tier")[
            "customers"
        ]
    )

    st.bar_chart(
        customer_chart,
        use_container_width=True,
    )


# =============================================================================
# RISK SUMMARY TABLE
# =============================================================================

st.markdown(
    "**Risk Tier Summary**"
)


display_summary = risk_summary.copy()


display_summary[
    "current_mrr"
] = display_summary[
    "current_mrr"
].map(
    lambda x: f"${x:,.0f}"
)


display_summary[
    "revenue_at_risk"
] = display_summary[
    "revenue_at_risk"
].map(
    lambda x: f"${x:,.0f}"
)


display_summary[
    "avg_churn_probability"
] = display_summary[
    "avg_churn_probability"
].map(
    lambda x: f"{x:.1%}"
)


display_summary = display_summary.rename(
    columns={
        "risk_tier": "Risk Tier",
        "customers": "Customers",
        "current_mrr": "Current MRR",
        "revenue_at_risk": "Revenue at Risk",
        "avg_churn_probability": "Avg. Churn Probability",
    }
)


st.dataframe(
    display_summary,
    use_container_width=True,
    hide_index=True,
)


st.divider()


# =============================================================================
# SEGMENT ANALYSIS
# =============================================================================

st.subheader(
    "Customer Segment Analysis"
)


segment_col1, segment_col2 = st.columns(2)


# -----------------------------------------------------------------------------
# Plan analysis
# -----------------------------------------------------------------------------

with segment_col1:

    st.markdown(
        "**Revenue Exposure by Plan**"
    )

    plan_analysis = (
        filtered
        .groupby("plan_type")
        .agg(
            customers=(
                "user_id",
                "count",
            ),
            current_mrr=(
                "mrr",
                "sum",
            ),
            revenue_at_risk=(
                "revenue_at_risk",
                "sum",
            ),
            avg_churn_probability=(
                "churn_probability",
                "mean",
            ),
        )
        .reset_index()
    )

    plan_chart = (
        plan_analysis
        .set_index("plan_type")[
            "revenue_at_risk"
        ]
    )

    st.bar_chart(
        plan_chart,
        use_container_width=True,
    )


# -----------------------------------------------------------------------------
# Acquisition analysis
# -----------------------------------------------------------------------------

with segment_col2:

    st.markdown(
        "**Revenue Exposure by Acquisition Channel**"
    )

    channel_analysis = (
        filtered
        .groupby("acquisition_channel")
        .agg(
            customers=(
                "user_id",
                "count",
            ),
            current_mrr=(
                "mrr",
                "sum",
            ),
            revenue_at_risk=(
                "revenue_at_risk",
                "sum",
            ),
            avg_churn_probability=(
                "churn_probability",
                "mean",
            ),
        )
        .reset_index()
    )

    channel_chart = (
        channel_analysis
        .set_index(
            "acquisition_channel"
        )[
            "revenue_at_risk"
        ]
    )

    st.bar_chart(
        channel_chart,
        use_container_width=True,
    )


# =============================================================================
# INDUSTRY ANALYSIS
# =============================================================================

st.markdown(
    "**Revenue Exposure by Industry**"
)


industry_analysis = (
    filtered
    .groupby("industry")
    .agg(
        customers=(
            "user_id",
            "count",
        ),
        current_mrr=(
            "mrr",
            "sum",
        ),
        revenue_at_risk=(
            "revenue_at_risk",
            "sum",
        ),
        avg_churn_probability=(
            "churn_probability",
            "mean",
        ),
    )
    .reset_index()
    .sort_values(
        "revenue_at_risk",
        ascending=False,
    )
)


industry_chart = (
    industry_analysis
    .set_index("industry")[
        "revenue_at_risk"
    ]
)


st.bar_chart(
    industry_chart,
    use_container_width=True,
)


st.divider()


# =============================================================================
# RETENTION PRIORITY ENGINE
# =============================================================================

st.subheader(
    "Retention Priority Engine"
)

st.caption(
    "Ranks accounts using predicted churn probability "
    "and modeled revenue exposure."
)


# -----------------------------------------------------------------------------
# Normalize revenue exposure
# -----------------------------------------------------------------------------

max_revenue_risk = (
    filtered[
        "revenue_at_risk"
    ].max()
)


if max_revenue_risk > 0:

    filtered[
        "revenue_risk_score"
    ] = (
        filtered[
            "revenue_at_risk"
        ]
        / max_revenue_risk
    )

else:

    filtered[
        "revenue_risk_score"
    ] = 0


# -----------------------------------------------------------------------------
# Combined priority score
#
# 60% churn probability
# 40% revenue exposure
# -----------------------------------------------------------------------------

filtered[
    "priority_score"
] = (
    0.60
    * filtered[
        "churn_probability"
    ]
    + 0.40
    * filtered[
        "revenue_risk_score"
    ]
)


# -----------------------------------------------------------------------------
# Priority ranking
# -----------------------------------------------------------------------------

filtered[
    "priority_rank"
] = (
    filtered[
        "priority_score"
    ]
    .rank(
        method="first",
        ascending=False,
    )
    .astype(int)
)


# =============================================================================
# RETENTION ACTION LOGIC
# =============================================================================


revenue_risk_75th = (
    filtered[
        "revenue_at_risk"
    ].quantile(0.75)
)


median_mrr = (
    filtered["mrr"].median()
)


def assign_action(
    row: pd.Series,
) -> str:

    if (
        row["risk_tier"] == "high"
        and row["revenue_at_risk"]
        >= revenue_risk_75th
    ):

        return (
            "Immediate account intervention"
        )

    if row["risk_tier"] == "high":

        return (
            "Targeted retention campaign"
        )

    if (
        row["risk_tier"] == "medium"
        and row["mrr"] >= median_mrr
    ):

        return (
            "Customer success outreach"
        )

    if row["risk_tier"] == "medium":

        return (
            "Engagement campaign"
        )

    return "Monitor"


filtered[
    "recommended_action"
] = filtered.apply(
    assign_action,
    axis=1,
)


# =============================================================================
# PRIORITY QUEUE
# =============================================================================


priority_queue = (
    filtered
    .sort_values(
        [
            "priority_score",
            "revenue_at_risk",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .head(
        accounts_to_display
    )
    .copy()
)


priority_queue[
    "priority"
] = range(
    1,
    len(priority_queue) + 1,
)


priority_display = priority_queue[
    [
        "priority",
        "user_id",
        "risk_tier",
        "priority_score",
        "churn_probability",
        "mrr",
        "revenue_at_risk",
        "days_since_last_event",
        "customer_tenure_days",
        "plan_type",
        "industry",
        "acquisition_channel",
        "recommended_action",
    ]
].copy()


# -----------------------------------------------------------------------------
# Formatting
# -----------------------------------------------------------------------------

priority_display[
    "priority_score"
] = priority_display[
    "priority_score"
].map(
    lambda x: f"{x:.3f}"
)


priority_display[
    "churn_probability"
] = priority_display[
    "churn_probability"
].map(
    lambda x: f"{x:.1%}"
)


priority_display[
    "mrr"
] = priority_display[
    "mrr"
].map(
    lambda x: f"${x:,.0f}"
)


priority_display[
    "revenue_at_risk"
] = priority_display[
    "revenue_at_risk"
].map(
    lambda x: f"${x:,.0f}"
)


priority_display[
    "days_since_last_event"
] = priority_display[
    "days_since_last_event"
].round(
    0
).astype(int)


priority_display[
    "customer_tenure_days"
] = priority_display[
    "customer_tenure_days"
].round(
    0
).astype(int)


# -----------------------------------------------------------------------------
# Rename columns
# -----------------------------------------------------------------------------

priority_display = priority_display.rename(
    columns={
        "priority": "Priority",
        "user_id": "Customer",
        "risk_tier": "Risk",
        "priority_score": "Priority Score",
        "churn_probability": "Churn Probability",
        "mrr": "MRR",
        "revenue_at_risk": "Revenue at Risk",
        "days_since_last_event": "Days Since Activity",
        "customer_tenure_days": "Tenure Days",
        "plan_type": "Plan",
        "industry": "Industry",
        "acquisition_channel": "Acquisition",
        "recommended_action": "Recommended Action",
    }
)


st.dataframe(
    priority_display,
    use_container_width=True,
    hide_index=True,
)


st.divider()


# =============================================================================
# BUSINESS INSIGHTS
# =============================================================================

st.subheader(
    "Business Interpretation"
)


# -----------------------------------------------------------------------------
# Calculate high-risk revenue share
# -----------------------------------------------------------------------------

high_risk_revenue = filtered.loc[
    filtered["risk_tier"] == "high",
    "revenue_at_risk",
].sum()


medium_risk_revenue = filtered.loc[
    filtered["risk_tier"] == "medium",
    "revenue_at_risk",
].sum()


if total_revenue_at_risk > 0:

    high_risk_revenue_share = (
        high_risk_revenue
        / total_revenue_at_risk
    )

    medium_risk_revenue_share = (
        medium_risk_revenue
        / total_revenue_at_risk
    )

else:

    high_risk_revenue_share = 0

    medium_risk_revenue_share = 0


# -----------------------------------------------------------------------------
# Insight metrics
# -----------------------------------------------------------------------------

insight_col1, insight_col2, insight_col3 = st.columns(3)


with insight_col1:

    st.metric(
        "High-Risk Customers",
        f"{high_risk_count:,}",
    )


with insight_col2:

    st.metric(
        "High-Risk Revenue Share",
        f"{high_risk_revenue_share:.1%}",
    )


with insight_col3:

    st.metric(
        "Medium-Risk Revenue Share",
        f"{medium_risk_revenue_share:.1%}",
    )


# =============================================================================
# RETENTION STRATEGY
# =============================================================================


st.info(
    f"""
**Retention strategy**

Focus immediate intervention on the highest-ranked accounts
in the priority queue. These customers combine elevated predicted
churn probability with meaningful recurring-revenue exposure.

The current filtered population contains
**{high_risk_count:,} high-risk customers**.

Modeled revenue exposure is approximately
**${total_revenue_at_risk:,.0f}**
against
**${total_mrr:,.0f}**
of current MRR.

Revenue exposure should be treated as an
**expected-risk estimate**, not guaranteed revenue loss.
"""
)


# =============================================================================
# METHODOLOGY NOTE
# =============================================================================


with st.expander(
    "Model and methodology"
):

    st.markdown(
        """
### Prediction design

The churn model uses a fixed prediction cutoff of
**2025-07-01** and predicts whether an active paid customer
will churn within the following **180 days**.

### Behavioral features

The model uses:

- Days since last product activity
- Total events in the previous 90 days
- Distinct event types used
- Active days in the previous 90 days
- Customer tenure

### Model

A balanced logistic regression model is used as the
baseline predictive model.

### Revenue exposure

Modeled revenue exposure is calculated as:

**Current MRR × predicted churn probability**

This represents expected revenue exposure and should not
be interpreted as guaranteed future revenue loss.

### Important limitation

The underlying dataset is synthetic. Results demonstrate
the analytics workflow and methodology rather than
representing real-world customer behavior.

The model identifies predictive associations and should not
be interpreted as establishing causal relationships.
"""
    )
