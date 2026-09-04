"""
Executive Summary — SaaS growth, retention, experimentation, and revenue risk.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_app.utils.data_loader import (
    load_churn_scores,
    load_daily_growth,
)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Executive Summary",
    page_icon="📊",
    layout="wide",
)

st.title("Executive Summary")
st.caption(
    "A decision-oriented view of acquisition, activation, conversion, "
    "retention, experimentation, and revenue risk."
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"


def load_mart(filename: str) -> pd.DataFrame:
    """Load a processed parquet mart."""
    path = PROCESSED_DIR / filename

    if not path.exists():
        return pd.DataFrame()

    return pd.read_parquet(path)


def find_column(df: pd.DataFrame, candidates: list[str]):
    """Return the first matching column from a list of candidates."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def money_short(value: float) -> str:
    """Format currency for executive KPI cards."""
    if pd.isna(value):
        return "N/A"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"

    return f"${value:,.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

daily = load_daily_growth()

if daily.empty:
    st.error("Daily growth data could not be loaded.")
    st.stop()

daily = daily.copy()
daily["metric_date"] = pd.to_datetime(daily["metric_date"])
daily = daily.sort_values("metric_date")

last_30 = daily.tail(30)

latest = last_30.iloc[-1]

if len(last_30) >= 2:
    previous = last_30.iloc[-2]
else:
    previous = latest


churn = load_churn_scores()

if churn.empty:
    st.error("Churn prediction data could not be loaded.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS METRICS
# ─────────────────────────────────────────────────────────────────────────────

activation_rate = latest["activation_rate"]
trial_to_paid = latest["trial_to_paid_rate"]
d30_retention = latest["d30_retention_rate"]

latest_mrr = latest["mrr"]
previous_mrr = previous["mrr"]

activation_delta = latest["activation_rate"] - previous["activation_rate"]
trial_paid_delta = latest["trial_to_paid_rate"] - previous["trial_to_paid_rate"]
mrr_delta = latest_mrr - previous_mrr


risk_counts = (
    churn["risk_tier"]
    .value_counts()
    .reindex(["low", "medium", "high"], fill_value=0)
)

high_risk_customers = int(risk_counts.get("high", 0))

current_mrr = churn["mrr"].sum()
modeled_revenue_exposure = churn["revenue_at_risk"].sum()

high_risk_exposure = churn.loc[
    churn["risk_tier"] == "high",
    "revenue_at_risk",
].sum()

high_risk_revenue_share = (
    high_risk_exposure / modeled_revenue_exposure
    if modeled_revenue_exposure > 0
    else 0
)

actual_future_churn_rate = churn["churned_next_180d"].mean()


# ─────────────────────────────────────────────────────────────────────────────
# TOP KPI ROW
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Business Health")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Activation Rate",
    f"{activation_rate:.1%}",
    delta=f"{activation_delta:+.1%}",
)

k2.metric(
    "Trial → Paid",
    f"{trial_to_paid:.1%}",
    delta=f"{trial_paid_delta:+.1%}",
)

k3.metric(
    "D30 Retention",
    f"{d30_retention:.1%}"
    if pd.notna(d30_retention)
    else "N/A",
)

k4.metric(
    "High-Risk Customers",
    f"{high_risk_customers:,}",
)

k5.metric(
    "Current MRR",
    money_short(current_mrr),
    delta=money_short(mrr_delta),
)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# 30-DAY TRENDS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("30-Day Performance Trends")

trend_col1, trend_col2 = st.columns(2)


with trend_col1:

    fig_activation = px.line(
        last_30,
        x="metric_date",
        y="activation_rate",
        markers=True,
        title="Activation Rate",
    )

    fig_activation.update_layout(
        yaxis_tickformat=".0%",
        xaxis_title="",
        yaxis_title="",
        height=350,
    )

    st.plotly_chart(
        fig_activation,
        use_container_width=True,
    )


with trend_col2:

    fig_trial = px.line(
        last_30,
        x="metric_date",
        y="trial_to_paid_rate",
        markers=True,
        title="Trial → Paid Conversion",
    )

    fig_trial.update_layout(
        yaxis_tickformat=".0%",
        xaxis_title="",
        yaxis_title="",
        height=350,
    )

    st.plotly_chart(
        fig_trial,
        use_container_width=True,
    )


# Churn gets its own scale because it is much smaller than activation.
fig_churn = px.line(
    last_30,
    x="metric_date",
    y="churn_rate",
    markers=True,
    title="Daily Churn Rate",
)

fig_churn.update_layout(
    yaxis_tickformat=".0%",
    xaxis_title="",
    yaxis_title="",
    height=300,
)

st.plotly_chart(
    fig_churn,
    use_container_width=True,
)


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# GROWTH FUNNEL
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Growth Funnel Snapshot")

funnel = load_mart("mart_funnel.parquet")

if not funnel.empty:

    # The first row is the overall funnel summary.
    overall = funnel[funnel["acquisition_channel"].isna()]

    if overall.empty:
        overall = funnel.iloc[[0]]

    overall = overall.iloc[0]

    signup_users = int(overall["signup_users"])
    workspace_users = int(overall["workspace_users"])
    invite_users = int(overall["invite_users"])
    project_users = int(overall["project_users"])
    paid_users = int(overall["paid_users"])

    funnel_cols = st.columns(5)

    funnel_cols[0].metric(
        "Signup",
        f"{signup_users:,}",
    )

    funnel_cols[1].metric(
        "Workspace",
        f"{workspace_users:,}",
        delta=f"{workspace_users / signup_users:.1%} conversion",
    )

    funnel_cols[2].metric(
        "Invite",
        f"{invite_users:,}",
        delta=f"{invite_users / workspace_users:.1%} conversion",
    )

    funnel_cols[3].metric(
        "Project",
        f"{project_users:,}",
        delta=f"{project_users / invite_users:.1%} conversion",
    )

    funnel_cols[4].metric(
        "Paid",
        f"{paid_users:,}",
        delta=f"{paid_users / project_users:.1%} conversion",
    )

    # Identify the largest conversion drop.
    transitions = {
        "Signup → Workspace": float(
            overall["signup_to_workspace_rate"]
        ),
        "Workspace → Invite": float(
            overall["workspace_to_invite_rate"]
        ),
        "Invite → Project": float(
            overall["invite_to_project_rate"]
        ),
        "Project → Paid": float(
            overall["project_to_paid_rate"]
        ),
    }

    weakest_transition = min(
        transitions,
        key=transitions.get,
    )

    weakest_conversion = transitions[weakest_transition]
    weakest_dropoff = 1 - weakest_conversion

    st.warning(
        f"**Largest funnel leakage:** {weakest_transition} — "
        f"{weakest_dropoff:.1%} of users drop between these stages."
    )

else:

    st.warning("Funnel mart is unavailable.")




# ─────────────────────────────────────────────────────────────────────────────
# KEY BUSINESS FINDINGS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Key Business Findings")

finding1, finding2, finding3 = st.columns(3)


with finding1:

    st.markdown("### 🔴 Conversion Bottleneck")

    st.markdown(
        """
        The largest opportunity is at the lower end of the funnel,
        where users who have created a project still need to convert
        into paying customers.
        """
    )


with finding2:

    st.markdown("### 🟡 Revenue Risk")

    st.markdown(
        f"""
        **{high_risk_customers:,}** customers are classified as high risk.

        Modeled revenue exposure is approximately
        **{money_short(modeled_revenue_exposure)}**.
        """
    )


with finding3:

    st.markdown("### 🟢 Experimentation")

    st.markdown(
        """
        The onboarding experiment shows a positive activation lift,
        providing evidence that onboarding changes can materially
        influence activation in this synthetic test environment.
        """
    )


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# RETENTION & REVENUE RISK
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Retention & Revenue Risk")

risk1, risk2, risk3 = st.columns(3)

risk1.metric(
    "High-Risk Customers",
    f"{high_risk_customers:,}",
)

risk2.metric(
    "Modeled Revenue Exposure",
    money_short(modeled_revenue_exposure),
)

risk3.metric(
    "Exposure as % of Current MRR",
    f"{(modeled_revenue_exposure / current_mrr):.1%}"
    if current_mrr > 0
    else "N/A",
)

st.caption(
    "Revenue exposure is an expected-risk estimate "
    "(MRR × predicted churn probability), not guaranteed revenue loss."
)


# Risk distribution chart
risk_chart = (
    churn["risk_tier"]
    .value_counts()
    .reindex(["low", "medium", "high"], fill_value=0)
    .rename_axis("Risk Tier")
    .reset_index(name="Customers")
)

risk_chart["Risk Tier"] = risk_chart["Risk Tier"].str.title()

fig_risk = px.bar(
    risk_chart,
    x="Risk Tier",
    y="Customers",
    title="Customer Distribution by Risk Tier",
)

fig_risk.update_layout(
    xaxis_title="",
    yaxis_title="Customers",
    height=350,
)

st.plotly_chart(
    fig_risk,
    use_container_width=True,
)


st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENTATION SNAPSHOT
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Experimentation Snapshot")

experiment = load_mart("mart_experiment_results.parquet")

if not experiment.empty:

    # Keep the onboarding experiment explicit.
    onboarding = experiment[
        experiment["experiment_name"] == "onboarding_v2"
    ].copy()

    control = onboarding[
        onboarding["variant"].str.lower() == "control"
    ]

    treatment = onboarding[
        onboarding["variant"].str.lower() == "treatment"
    ]

    if not control.empty and not treatment.empty:

        control_users = int(control.iloc[0]["users"])
        control_activated = int(control.iloc[0]["activated_users"])
        control_rate = float(control.iloc[0]["activation_rate"])

        treatment_users = int(treatment.iloc[0]["users"])
        treatment_activated = int(
            treatment.iloc[0]["activated_users"]
        )
        treatment_rate = float(
            treatment.iloc[0]["activation_rate"]
        )

        # Absolute and relative lift.
        absolute_lift = treatment_rate - control_rate

        relative_lift = (
            absolute_lift / control_rate
            if control_rate > 0
            else 0
        )

        # Two-proportion z-test.
        from statsmodels.stats.proportion import proportions_ztest

        successes = [
            treatment_activated,
            control_activated,
        ]

        observations = [
            treatment_users,
            control_users,
        ]

        z_stat, p_value = proportions_ztest(
            successes,
            observations,
        )

        statistically_significant = p_value < 0.05

        # ── Experiment metrics ──────────────────────────────────────────────

        e1, e2, e3, e4 = st.columns(4)

        e1.metric(
            "Control Activation",
            f"{control_rate:.1%}",
        )

        e2.metric(
            "Treatment Activation",
            f"{treatment_rate:.1%}",
        )

        e3.metric(
            "Absolute Lift",
            f"{absolute_lift:+.1%}",
        )

        e4.metric(
            "Relative Lift",
            f"{relative_lift:+.1%}",
        )

        # ── Statistical result ──────────────────────────────────────────────

        st.markdown("#### Statistical Test")

        s1, s2, s3 = st.columns(3)

        s1.metric(
            "Z-Statistic",
            f"{z_stat:.2f}",
        )

        s2.metric(
            "P-Value",
            "< 0.001" if p_value < 0.001 else f"{p_value:.3f}",
        )

        s3.metric(
            "Result",
            "Significant" if statistically_significant else "Not Significant",
        )

        if statistically_significant:

            st.success(
                f"The treatment increased activation by "
                f"**{absolute_lift:.1%} ({absolute_lift * 100:.1f}pp)** "
                f"relative to control, and the observed difference is "
                f"statistically significant (p < 0.001)."
            )

        else:

            st.info(
                "The observed activation difference is not statistically "
                "significant at the 5% significance level."
            )

        st.caption(
            "Test: two-proportion z-test comparing treatment and control "
            "activation rates."
        )

    else:

        st.warning(
            "Control or treatment results were not found for onboarding_v2."
        )

else:

    st.warning("Experiment results mart is unavailable.")

# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDED ACTIONS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Recommended Business Actions")

a1, a2, a3 = st.columns(3)

with a1:

    st.markdown("### 1. Improve Paid Conversion")

    st.write(
        "Investigate the Project → Paid transition using the Funnel "
        "page and identify onboarding, pricing, or activation barriers."
    )


with a2:

    st.markdown("### 2. Prioritize Revenue Risk")

    st.write(
        "Use the Revenue Risk priority queue to focus customer-success "
        "efforts on high-risk accounts with meaningful revenue exposure."
    )


with a3:

    st.markdown("### 3. Scale Through Experimentation")

    st.write(
        "Continue validating onboarding improvements through controlled "
        "experiments before rolling changes out broadly."
    )


# ─────────────────────────────────────────────────────────────────────────────
# METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("Methodology & Important Limitations"):

    st.markdown(
        """
        **Data**

        The underlying SaaS event data is synthetic and was generated
        for analytics demonstration purposes.

        **Churn prediction**

        Churn is modeled using a temporal prediction setup. Customer
        behavior is measured using activity observed before the prediction
        cutoff, and the target represents churn during the subsequent
        180-day horizon.

        **Revenue exposure**

        Modeled revenue exposure is calculated as:

        `MRR × predicted churn probability`

        This represents expected-risk exposure rather than guaranteed
        future revenue loss.

        **Experimentation**

        The onboarding experiment is evaluated using treatment and control
        activation rates. Statistical significance is assessed separately
        in the experimentation analysis.

        **Interpretation**

        Because the dataset is synthetic, findings should be treated as
        analytical demonstrations and associations rather than causal
        claims about real customers.
        """
    )
