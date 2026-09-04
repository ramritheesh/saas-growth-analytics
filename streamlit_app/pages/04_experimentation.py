"""
Experimentation — A/B test analysis for onboarding_v2.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from python.src.analysis import analyze_experiment
from streamlit_app.utils.data_loader import load_experiment_results


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Experimentation",
    page_icon="🧪",
    layout="wide",
)

st.title("Experimentation")
st.caption(
    "Evaluate onboarding changes using activation lift, confidence intervals, "
    "and statistical significance."
)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

exp_df = load_experiment_results()

if exp_df.empty:
    st.error("Experiment data could not be loaded.")
    st.stop()

results = analyze_experiment(exp_df)

if results.empty:
    st.error("Experiment analysis returned no results.")
    st.stop()

r = results.iloc[0]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def proportion_ci(
    rate: float,
    n: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """
    Approximate 95% confidence interval for a single proportion.
    """

    if n <= 0:
        return np.nan, np.nan

    se = np.sqrt(rate * (1 - rate) / n)

    lower = max(0.0, rate - z * se)
    upper = min(1.0, rate + z * se)

    return lower, upper


def difference_ci(
    control_rate: float,
    treatment_rate: float,
    control_n: int,
    treatment_n: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """
    Approximate 95% confidence interval for the difference
    in two independent proportions.

    Difference is treatment - control.
    """

    if control_n <= 0 or treatment_n <= 0:
        return np.nan, np.nan

    standard_error = np.sqrt(
        (
            control_rate * (1 - control_rate)
            / control_n
        )
        +
        (
            treatment_rate * (1 - treatment_rate)
            / treatment_n
        )
    )

    difference = treatment_rate - control_rate

    margin = z * standard_error

    return (
        difference - margin,
        difference + margin,
    )


def format_p_value(p_value: float) -> str:
    """
    Human-readable p-value formatting.
    """

    if p_value < 0.001:
        return "<0.001"

    return f"{p_value:.3f}"


# ─────────────────────────────────────────────────────────────────────────────
# CORE METRICS
# ─────────────────────────────────────────────────────────────────────────────

control_rate = float(r["control_rate"])
treatment_rate = float(r["treatment_rate"])

control_users = int(r["control_users"])
treatment_users = int(r["treatment_users"])

control_activated = int(exp_df.loc[exp_df["variant"].str.lower() == "control", "activated_users"].iloc[0])
treatment_activated = int(exp_df.loc[exp_df["variant"].str.lower() == "treatment", "activated_users"].iloc[0])

absolute_lift = treatment_rate - control_rate

relative_lift = (
    absolute_lift / control_rate
    if control_rate > 0
    else np.nan
)

p_value = float(r["p_value"])

significant = bool(r["significant"])


# Confidence intervals.
control_lower, control_upper = proportion_ci(
    control_rate,
    control_users,
)

treatment_lower, treatment_upper = proportion_ci(
    treatment_rate,
    treatment_users,
)

lift_lower, lift_upper = difference_ci(
    control_rate,
    treatment_rate,
    control_users,
    treatment_users,
)


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENT STATUS
# ─────────────────────────────────────────────────────────────────────────────

if significant and absolute_lift > 0:

    st.success(
        f"**Treatment outperformed control.** "
        f"Activation increased by **{absolute_lift:.1%} "
        f"({absolute_lift * 100:.2f} percentage points)** "
        f"with p = **{format_p_value(p_value)}**."
    )

elif significant and absolute_lift < 0:

    st.error(
        f"**Treatment underperformed control.** "
        f"Activation decreased by **{abs(absolute_lift):.1%}** "
        f"with p = **{format_p_value(p_value)}**."
    )

else:

    st.warning(
        f"**No statistically significant difference detected.** "
        f"Observed activation lift was **{absolute_lift:.1%}** "
        f"with p = **{format_p_value(p_value)}**."
    )


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENT KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Experiment Overview")

c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Control Activation",
        f"{control_rate:.1%}",
        help=f"{control_activated:,} activated / {control_users:,} users",
    )


with c2:

    st.metric(
        "Treatment Activation",
        f"{treatment_rate:.1%}",
        help=f"{treatment_activated:,} activated / {treatment_users:,} users",
    )


with c3:

    st.metric(
        "Absolute Lift",
        f"{absolute_lift * 100:+.2f} pp",
    )


with c4:

    st.metric(
        "Relative Lift",
        f"{relative_lift * 100:+.2f}%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE SIZE
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Experiment Sample")

s1, s2, s3 = st.columns(3)


with s1:

    st.metric(
        "Control Users",
        f"{control_users:,}",
    )


with s2:

    st.metric(
        "Treatment Users",
        f"{treatment_users:,}",
    )


with s3:

    st.metric(
        "Total Experiment Users",
        f"{control_users + treatment_users:,}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVATION RATE CHART
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Activation Rate by Variant")

chart_df = pd.DataFrame(
    {
        "Variant": ["Control", "Treatment"],
        "Activation Rate": [
            control_rate,
            treatment_rate,
        ],
        "CI Lower": [
            control_lower,
            treatment_lower,
        ],
        "CI Upper": [
            control_upper,
            treatment_upper,
        ],
    }
)

error_lower = (
    chart_df["Activation Rate"]
    - chart_df["CI Lower"]
)

error_upper = (
    chart_df["CI Upper"]
    - chart_df["Activation Rate"]
)


fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=chart_df["Variant"],
        y=chart_df["Activation Rate"],
        error_y=dict(
            type="data",
            symmetric=False,
            array=error_upper,
            arrayminus=error_lower,
            visible=True,
        ),
        text=[
            f"{control_rate:.1%}",
            f"{treatment_rate:.1%}",
        ],
        textposition="outside",
        marker_color=[
            "#636EFA",
            "#00CC96",
        ],
    )
)

fig.update_layout(
    yaxis_tickformat=".0%",
    yaxis_title="Activation Rate",
    xaxis_title="",
    yaxis_range=[
        max(0, min(control_lower, treatment_lower) - 0.05),
        min(1, max(control_upper, treatment_upper) + 0.05),
    ],
    height=430,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# LIFT CONFIDENCE INTERVAL
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Treatment Lift")

lift_col1, lift_col2 = st.columns(2)


with lift_col1:

    st.metric(
        "Observed Lift",
        f"{absolute_lift * 100:+.2f} pp",
    )

    st.caption(
        "Treatment activation minus control activation."
    )


with lift_col2:

    if pd.notna(lift_lower) and pd.notna(lift_upper):

        st.metric(
            "95% Confidence Interval",
            f"[{lift_lower * 100:+.2f}, "
            f"{lift_upper * 100:+.2f}] pp",
        )

        st.caption(
            "Approximate confidence interval for the treatment-control difference."
        )

    else:

        st.metric(
            "95% Confidence Interval",
            "N/A",
        )


# ─────────────────────────────────────────────────────────────────────────────
# STATISTICAL INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Statistical Interpretation")

if significant and absolute_lift > 0:

    st.markdown(
        f"""
### Evidence of a positive treatment effect

The treatment activation rate was **{treatment_rate:.1%}** compared
with **{control_rate:.1%}** for control.

This corresponds to an observed lift of:

**{absolute_lift * 100:+.2f} percentage points**
or approximately **{relative_lift * 100:+.2f}% relative improvement**.

The test produced a p-value of **{format_p_value(p_value)}**,
which is below the conventional 0.05 significance threshold.

The approximate 95% confidence interval for the treatment-control
difference is **[{lift_lower * 100:+.2f}, {lift_upper * 100:+.2f}]**
percentage points.
"""
    )

elif significant:

    st.markdown(
        f"""
The experiment produced a statistically significant difference,
but the treatment performed worse than control.

Treatment activation was **{treatment_rate:.1%}** versus
**{control_rate:.1%}** for control.

The estimated treatment-control difference was
**{absolute_lift * 100:+.2f} percentage points**.
"""
    )

else:

    st.markdown(
        f"""
The observed treatment-control difference was
**{absolute_lift * 100:+.2f} percentage points**, but the result
was not statistically significant at the 5% level.

The experiment therefore does not provide sufficient statistical
evidence to conclude that the observed difference represents a
reliable treatment effect.
"""
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Variant-Level Results")

variant_table = pd.DataFrame(
    {
        "Variant": [
            "Control",
            "Treatment",
        ],
        "Users": [
            control_users,
            treatment_users,
        ],
        "Activated Users": [
            control_activated,
            treatment_activated,
        ],
        "Activation Rate": [
            control_rate,
            treatment_rate,
        ],
        "95% CI": [
            f"{control_lower:.1%} – {control_upper:.1%}",
            f"{treatment_lower:.1%} – {treatment_upper:.1%}",
        ],
    }
)

variant_table["Users"] = variant_table["Users"].map(
    lambda x: f"{x:,}"
)

variant_table["Activated Users"] = (
    variant_table["Activated Users"].map(
        lambda x: f"{x:,}"
    )
)

variant_table["Activation Rate"] = (
    variant_table["Activation Rate"].map(
        lambda x: f"{x:.1%}"
    )
)

st.dataframe(
    variant_table,
    use_container_width=True,
    hide_index=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS DECISION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Business Decision")

if significant and absolute_lift > 0:

    st.info(
        """
**Recommendation:** The treatment shows statistically significant
positive activation lift in this experiment.

For a real production experiment, the next step would be to validate
the result across additional cohorts and monitor downstream metrics
such as retention, conversion to paid, and revenue before a broad
rollout.
"""
    )

elif significant:

    st.warning(
        """
**Recommendation:** Do not roll out the treatment based on this
experiment. The treatment produced a statistically significant
negative result and should be investigated before further testing.
"""
    )

else:

    st.warning(
        """
**Recommendation:** Do not make a rollout decision from this test
alone. The observed difference was not statistically significant.
Consider additional sample size or a refined experiment design.
"""
    )


# ─────────────────────────────────────────────────────────────────────────────
# METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("Methodology & Limitations"):

    st.markdown(
        """
        **Experiment**

        The experiment compares activation between the control and
        treatment variants of `onboarding_v2`.

        **Primary metric**

        Activation rate:

        `Activated users / Experiment users`

        **Absolute lift**

        `Treatment activation rate − Control activation rate`

        This is reported in **percentage points**.

        **Relative lift**

        `Absolute lift / Control activation rate`

        **Statistical test**

        The experiment uses a two-proportion statistical test to assess
        whether the difference in activation rates is statistically
        significant.

        **Confidence intervals**

        The dashboard shows approximate 95% confidence intervals for
        individual activation rates and the treatment-control difference.

        **Important limitation**

        The underlying dataset is synthetic. Therefore, the experiment
        demonstrates an A/B testing workflow but should not be interpreted
        as evidence of a real-world causal product effect.

        Statistical significance also does not automatically imply that
        the treatment will improve retention, revenue, or other downstream
        business outcomes.
        """
    )
