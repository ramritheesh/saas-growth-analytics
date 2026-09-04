"""
Customer Intelligence — segmentation, engagement, revenue, and growth opportunities.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_app.utils.data_loader import load_customer_intelligence


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Customer Intelligence",
    page_icon="👥",
    layout="wide",
)

st.title("Customer Intelligence")
st.caption(
    "Understand customer segments through engagement, revenue, "
    "lifecycle stage, and acquisition source."
)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

df = load_customer_intelligence()

if df.empty:
    st.error("Customer intelligence data could not be loaded.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.header("Filters")

segment_options = sorted(
    df["customer_segment"]
    .dropna()
    .unique()
    .tolist()
)

plan_options = sorted(
    df["plan_type"]
    .dropna()
    .unique()
    .tolist()
)

industry_options = sorted(
    df["industry"]
    .dropna()
    .unique()
    .tolist()
)

channel_options = sorted(
    df["acquisition_channel"]
    .dropna()
    .unique()
    .tolist()
)


selected_segments = st.sidebar.multiselect(
    "Customer Segment",
    segment_options,
    default=segment_options,
)

selected_plans = st.sidebar.multiselect(
    "Plan Type",
    plan_options,
    default=plan_options,
)

selected_industries = st.sidebar.multiselect(
    "Industry",
    industry_options,
    default=industry_options,
)

selected_channels = st.sidebar.multiselect(
    "Acquisition Channel",
    channel_options,
    default=channel_options,
)


filtered = df[
    df["customer_segment"].isin(selected_segments)
    & df["plan_type"].isin(selected_plans)
    & df["industry"].isin(selected_industries)
    & df["acquisition_channel"].isin(selected_channels)
].copy()


if filtered.empty:
    st.warning("No customers match the selected filters.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# CORE KPIs
# ─────────────────────────────────────────────────────────────────────────────

total_customers = len(filtered)

paying_customers = int(
    (filtered["mrr"] > 0).sum()
)

total_mrr = filtered["mrr"].sum()

avg_engagement = filtered["engagement_score"].mean()

growth_opportunities = int(
    (
        filtered["customer_segment"]
        == "Growth Opportunity"
    ).sum()
)

high_value_customers = int(
    (
        filtered["customer_segment"]
        == "High Value"
    ).sum()
)

at_risk_customers = int(
    (
        filtered["customer_segment"]
        == "At Risk"
    ).sum()
)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Customer Overview")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Customers",
    f"{total_customers:,}",
)

k2.metric(
    "Paying Customers",
    f"{paying_customers:,}",
)

k3.metric(
    "Current MRR",
    (
        f"${total_mrr / 1_000_000:.2f}M"
        if total_mrr >= 1_000_000
        else f"${total_mrr / 1_000:.1f}K"
    ),
)

k4.metric(
    "Avg. Engagement",
    f"{avg_engagement:.1f}",
)

k5.metric(
    "Growth Opportunities",
    f"{growth_opportunities:,}",
)


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Customer Segmentation")

segment_summary = (
    filtered.groupby("customer_segment")
    .agg(
        customers=("user_id", "count"),
        mrr=("mrr", "sum"),
        avg_engagement=("engagement_score", "mean"),
        avg_active_days=("active_days", "mean"),
    )
    .reset_index()
)


segment_summary["mrr_share"] = (
    segment_summary["mrr"]
    / segment_summary["mrr"].sum()
    if segment_summary["mrr"].sum() > 0
    else 0
)


segment_chart_col, revenue_chart_col = st.columns(2)


with segment_chart_col:

    fig_segments = px.bar(
        segment_summary.sort_values(
            "customers",
            ascending=False,
        ),
        x="customer_segment",
        y="customers",
        text="customers",
        title="Customer Distribution",
    )

    fig_segments.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )

    fig_segments.update_layout(
        xaxis_title="",
        yaxis_title="Customers",
        height=420,
        showlegend=False,
    )

    st.plotly_chart(
        fig_segments,
        use_container_width=True,
    )


with revenue_chart_col:

    revenue_segments = segment_summary[
        segment_summary["mrr"] > 0
    ].sort_values(
        "mrr",
        ascending=False,
    )

    fig_revenue = px.bar(
        revenue_segments,
        x="customer_segment",
        y="mrr",
        text="mrr",
        title="MRR by Customer Segment",
    )

    fig_revenue.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )

    fig_revenue.update_layout(
        xaxis_title="",
        yaxis_title="MRR ($)",
        height=420,
        showlegend=False,
    )

    st.plotly_chart(
        fig_revenue,
        use_container_width=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT TABLE
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("#### Segment Performance")

segment_table = segment_summary.copy()

segment_table = segment_table.rename(
    columns={
        "customer_segment": "Segment",
        "customers": "Customers",
        "mrr": "MRR",
        "avg_engagement": "Avg Engagement",
        "avg_active_days": "Avg Active Days",
        "mrr_share": "MRR Share",
    }
)

segment_table["Customers"] = segment_table[
    "Customers"
].map(lambda x: f"{int(x):,}")

segment_table["MRR"] = segment_table[
    "MRR"
].map(lambda x: f"${x:,.0f}")

segment_table["Avg Engagement"] = segment_table[
    "Avg Engagement"
].map(lambda x: f"{x:.1f}")

segment_table["Avg Active Days"] = segment_table[
    "Avg Active Days"
].map(lambda x: f"{x:.1f}")

segment_table["MRR Share"] = segment_table[
    "MRR Share"
].map(lambda x: f"{x:.1%}")


st.dataframe(
    segment_table,
    use_container_width=True,
    hide_index=True,
)


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# ENGAGEMENT VS REVENUE
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Engagement vs Revenue")

scatter_df = filtered.copy()

# Avoid plotting an unnecessarily large number of points.
if len(scatter_df) > 10_000:

    scatter_df = scatter_df.sample(
        10_000,
        random_state=42,
    )


fig_scatter = px.scatter(
    scatter_df,
    x="engagement_score",
    y="mrr",
    color="customer_segment",
    hover_data=[
        "plan_type",
        "industry",
        "acquisition_channel",
        "active_days",
        "total_events",
    ],
    title="Customer Engagement vs MRR",
    opacity=0.65,
)

fig_scatter.update_layout(
    xaxis_title="Engagement Score",
    yaxis_title="MRR ($)",
    height=500,
)

st.plotly_chart(
    fig_scatter,
    use_container_width=True,
)


st.info(
    "This view helps identify customers who combine strong product "
    "engagement with meaningful revenue, as well as highly engaged "
    "non-paying users who may represent conversion opportunities."
)


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# ACQUISITION CHANNEL ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Customer Segments by Acquisition Channel")

channel_summary = (
    filtered.groupby(
        [
            "acquisition_channel",
            "customer_segment",
        ]
    )
    .size()
    .reset_index(name="customers")
)


channel_pivot = channel_summary.pivot(
    index="acquisition_channel",
    columns="customer_segment",
    values="customers",
).fillna(0)


fig_channel = px.bar(
    channel_pivot,
    barmode="stack",
    title="Customer Segment Mix by Acquisition Channel",
)

fig_channel.update_layout(
    xaxis_title="Acquisition Channel",
    yaxis_title="Customers",
    height=450,
)

st.plotly_chart(
    fig_channel,
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# GROWTH OPPORTUNITIES
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Growth Opportunity Analysis")

growth_df = filtered[
    filtered["customer_segment"]
    == "Growth Opportunity"
].copy()


g1, g2, g3 = st.columns(3)


g1.metric(
    "Highly Engaged Non-Paying Users",
    f"{len(growth_df):,}",
)


if not growth_df.empty:

    growth_avg_score = growth_df[
        "engagement_score"
    ].mean()

    growth_avg_events = growth_df[
        "total_events"
    ].mean()

    g2.metric(
        "Avg. Engagement Score",
        f"{growth_avg_score:.1f}",
    )

    g3.metric(
        "Avg. Events",
        f"{growth_avg_events:.1f}",
    )

else:

    g2.metric(
        "Avg. Engagement Score",
        "N/A",
    )

    g3.metric(
        "Avg. Events",
        "N/A",
    )


if not growth_df.empty:

    growth_channel = (
        growth_df["acquisition_channel"]
        .value_counts()
        .rename_axis("Channel")
        .reset_index(name="Users")
    )

    fig_growth = px.bar(
        growth_channel,
        x="Channel",
        y="Users",
        text="Users",
        title="Growth Opportunity Users by Acquisition Channel",
    )

    fig_growth.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )

    fig_growth.update_layout(
        xaxis_title="",
        yaxis_title="Users",
        height=400,
    )

    st.plotly_chart(
        fig_growth,
        use_container_width=True,
    )

    st.success(
        f"There are **{len(growth_df):,} highly engaged non-paying "
        "users** in the selected population. These users represent "
        "a potential conversion audience and should be investigated "
        "through lifecycle messaging, product prompts, or pricing "
        "experiments."
    )

else:

    st.info(
        "No Growth Opportunity customers are present under the "
        "current filters."
    )


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE & RETENTION
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Revenue & Retention Signals")

r1, r2, r3 = st.columns(3)


at_risk_mrr = filtered.loc[
    filtered["customer_segment"] == "At Risk",
    "mrr",
].sum()

high_value_mrr = filtered.loc[
    filtered["customer_segment"] == "High Value",
    "mrr",
].sum()

churned_customers = int(
    (
        filtered["customer_segment"]
        == "Churned"
    ).sum()
)


r1.metric(
    "At-Risk MRR",
    f"${at_risk_mrr:,.0f}",
)

r2.metric(
    "High-Value MRR",
    f"${high_value_mrr:,.0f}",
)

r3.metric(
    "Churned Customers",
    f"{churned_customers:,}",
)


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Business Interpretation")

interpretation_cols = st.columns(3)


with interpretation_cols[0]:

    st.markdown("### 💰 Revenue")

    st.write(
        "Engaged and High Value customers account for the majority "
        "of current MRR. These populations should be protected through "
        "retention and customer-success efforts."
    )


with interpretation_cols[1]:

    st.markdown("### 📈 Growth")

    st.write(
        "Highly engaged non-paying users represent a potential "
        "conversion audience. Their behavior suggests product usage "
        "without corresponding paid revenue."
    )


with interpretation_cols[2]:

    st.markdown("### ⚠️ Retention")

    st.write(
        "At-risk customers combine paid status with weaker engagement. "
        "They can be prioritized alongside the model-based Revenue Risk "
        "queue for targeted intervention."
    )


# ─────────────────────────────────────────────────────────────────────────────
# METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("Methodology & Limitations"):

    st.markdown(
        """
        **Engagement score**

        The engagement score combines:

        - Event frequency
        - Number of distinct product event types
        - Number of active days

        The score is normalized to a 0–100 scale.

        **Customer segmentation**

        Paying and non-paying customers are segmented differently so that
        highly engaged non-paying users can be separated as potential
        growth opportunities.

        **Revenue**

        MRR represents the current monthly recurring revenue associated
        with customers in the selected population.

        **Growth Opportunity**

        Growth Opportunity represents highly engaged non-paying users.
        It is a potential conversion audience, not a prediction that
        these users will necessarily become paying customers.

        **Interpretation**

        The underlying dataset is synthetic. Segment relationships and
        observed patterns should therefore be treated as analytical
        demonstrations rather than causal evidence.
        """
    )
