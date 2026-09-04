"""
Cohort Retention — cohort heatmap, retention curves, and cohort performance.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from python.src.analysis import build_cohort_heatmap
from streamlit_app.utils.data_loader import load_cohort_retention


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cohort Retention",
    page_icon="📈",
    layout="wide",
)

st.title("Cohort Retention")
st.caption(
    "Measure how user retention evolves across signup cohorts "
    "and identify changes in long-term engagement."
)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

cohort_df = load_cohort_retention()

if cohort_df.empty:
    st.error("Cohort retention data could not be loaded.")
    st.stop()

heatmap = build_cohort_heatmap(cohort_df)

if heatmap.empty:
    st.error("Unable to construct the cohort retention matrix.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# CONTROLS
# ─────────────────────────────────────────────────────────────────────────────

max_cohorts = len(heatmap)

default_cohorts = min(20, max_cohorts)

num_cohorts = st.slider(
    "Number of cohorts to display",
    min_value=5 if max_cohorts >= 5 else 1,
    max_value=max_cohorts,
    value=default_cohorts,
)


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DATA
# ─────────────────────────────────────────────────────────────────────────────

display = heatmap.head(num_cohorts).copy()


# ─────────────────────────────────────────────────────────────────────────────
# RETENTION CHECKPOINTS
# ─────────────────────────────────────────────────────────────────────────────

def get_checkpoint(matrix, week):
    """
    Return the average retention for cohorts that have reached
    the requested week.
    """

    if week not in matrix.columns:
        return None

    values = pd.to_numeric(
        matrix[week],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return values.mean()


w1_retention = get_checkpoint(display, "W1")
w2_retention = get_checkpoint(display, "W2")
w4_retention = get_checkpoint(display, "W4")


# Latest mature cohort for W4.
mature_w4 = heatmap["W4"].dropna() if "W4" in heatmap.columns else pd.Series(dtype=float)

if not mature_w4.empty:

    latest_mature_cohort = mature_w4.index[-1]

    latest_w4_retention = mature_w4.iloc[-1]

else:

    latest_mature_cohort = "N/A"
    latest_w4_retention = None


# ─────────────────────────────────────────────────────────────────────────────
# RETENTION OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Retention Overview")

k1, k2, k3, k4 = st.columns(4)


with k1:

    st.metric(
        "W1 Retention",
        f"{w1_retention:.1%}" if w1_retention is not None else "N/A",
    )


with k2:

    st.metric(
        "W2 Retention",
        f"{w2_retention:.1%}" if w2_retention is not None else "N/A",
    )


with k3:

    st.metric(
        "W4 Retention",
        f"{w4_retention:.1%}" if w4_retention is not None else "N/A",
    )


with k4:

    st.metric(
        "Latest Mature W4",
        (
            f"{latest_w4_retention:.1%}"
            if latest_w4_retention is not None
            else "N/A"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Retention Heatmap")

st.caption(
    "Each cell shows the percentage of a signup cohort that remained "
    "active at that week after signup. Blank cells indicate cohorts "
    "that have not yet reached that retention period."
)


fig_heatmap = px.imshow(
    display.values,
    x=display.columns.tolist(),
    y=display.index.tolist(),
    color_continuous_scale="Blues",
    zmin=0,
    zmax=1,
    text_auto=".0%",
    aspect="auto",
)

fig_heatmap.update_layout(
    xaxis_title="Weeks Since Signup",
    yaxis_title="Signup Cohort Week",
    height=max(450, num_cohorts * 30),
    margin=dict(l=20, r=20, t=30, b=20),
)

st.plotly_chart(
    fig_heatmap,
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# RETENTION CURVE
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Average Retention Curve")

st.caption(
    "Average retention across the displayed cohorts. "
    "Each week is calculated only from cohorts that have reached that week."
)


curve_values = []

for week in heatmap.columns:

    values = pd.to_numeric(
        heatmap[week],
        errors="coerce",
    ).dropna()

    if not values.empty:

        curve_values.append(
            {
                "Week": week,
                "Retention": values.mean(),
                "Cohorts": len(values),
            }
        )


curve_df = pd.DataFrame(curve_values)


if not curve_df.empty:

    fig_curve = px.line(
        curve_df,
        x="Week",
        y="Retention",
        markers=True,
        text="Retention",
    )

    fig_curve.update_traces(
        texttemplate="%{text:.1%}",
        textposition="top center",
    )

    fig_curve.update_layout(
        xaxis_title="Weeks Since Signup",
        yaxis_title="Average Retention",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1],
        height=430,
    )

    st.plotly_chart(
        fig_curve,
        use_container_width=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# COHORT PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Cohort Performance")

performance = heatmap.copy()

performance.index = performance.index.astype(str)

performance_table = pd.DataFrame(
    {
        "Cohort": performance.index,
        "W1 Retention": (
            performance["W1"]
            if "W1" in performance.columns
            else None
        ),
        "W2 Retention": (
            performance["W2"]
            if "W2" in performance.columns
            else None
        ),
        "W4 Retention": (
            performance["W4"]
            if "W4" in performance.columns
            else None
        ),
    }
)


# Only rank cohorts that have W4 data.
if "W4" in performance.columns:

    mature = performance.dropna(
        subset=["W4"]
    ).copy()

else:

    mature = pd.DataFrame()


if not mature.empty:

    best_idx = mature["W4"].idxmax()
    worst_idx = mature["W4"].idxmin()

    best_cohort = str(best_idx)
    best_retention = float(
        mature.loc[best_idx, "W4"]
    )

    worst_cohort = str(worst_idx)
    worst_retention = float(
        mature.loc[worst_idx, "W4"]
    )

else:

    best_cohort = "N/A"
    best_retention = None

    worst_cohort = "N/A"
    worst_retention = None


p1, p2, p3 = st.columns(3)


with p1:

    st.metric(
        "Best Mature Cohort",
        best_cohort,
        (
            f"{best_retention:.1%} W4 retention"
            if best_retention is not None
            else None
        ),
    )


with p2:

    st.metric(
        "Lowest Mature Cohort",
        worst_cohort,
        (
            f"{worst_retention:.1%} W4 retention"
            if worst_retention is not None
            else None
        ),
    )


with p3:

    if best_retention is not None and worst_retention is not None:

        cohort_gap = best_retention - worst_retention

        st.metric(
            "Best-to-Worst W4 Gap",
            f"{cohort_gap:.1%}",
        )

    else:

        st.metric(
            "Best-to-Worst W4 Gap",
            "N/A",
        )


# ─────────────────────────────────────────────────────────────────────────────
# COHORT TABLE
# ─────────────────────────────────────────────────────────────────────────────

formatted_table = performance_table.copy()

for column in [
    "W1 Retention",
    "W2 Retention",
    "W4 Retention",
]:

    if column in formatted_table.columns:

        formatted_table[column] = formatted_table[column].map(
            lambda x: f"{x:.1%}" if pd.notna(x) else "—"
        )


st.dataframe(
    formatted_table,
    use_container_width=True,
    hide_index=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# EARLY RETENTION DROP
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Retention Opportunity")

if (
    w1_retention is not None
    and w4_retention is not None
):

    early_drop = w1_retention - w4_retention

    st.warning(
        f"**Early retention decline:** average retention falls from "
        f"**{w1_retention:.1%} at W1** to **{w4_retention:.1%} at W4**, "
        f"a decline of approximately **{early_drop:.1%}**."
    )

    st.write(
        "This makes the first few weeks after signup an important "
        "area for product and lifecycle analysis. Potential areas "
        "to investigate include onboarding completion, activation "
        "behavior, time-to-value, and repeat product usage."
    )

else:

    st.info(
        "There is not enough mature cohort data to calculate the "
        "W1-to-W4 retention decline."
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Business Interpretation")

if (
    w1_retention is not None
    and w4_retention is not None
):

    st.markdown(
        f"""
**Retention pattern:** users experience the largest retention loss
during the early weeks after signup.

Average retention is **{w1_retention:.1%} at W1** and
**{w4_retention:.1%} at W4** across the displayed cohorts.

**Product implication:** improving early user activation and
time-to-value could be a higher-priority retention opportunity than
trying to optimize already-established users.

**Cohort comparison:** mature cohorts should be compared using the
same retention horizon. Recent cohorts are excluded from W4
comparisons when they have not yet accumulated four weeks of data.
"""
    )

else:

    st.markdown(
        """
**Retention analysis:** cohort retention varies by week since signup.

Recent cohorts may not yet have enough observation time to evaluate
longer-term retention. Cohorts should therefore be compared only
when they have reached the same retention horizon.
"""
    )


# ─────────────────────────────────────────────────────────────────────────────
# METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("Methodology & Limitations"):

    st.markdown(
        """
        **Cohort definition**

        Users are grouped by their signup week.

        **Retention**

        Retention represents the percentage of users from each signup
        cohort who remain active at a given number of weeks after signup.

        **Retention checkpoints**

        Because the underlying dataset is organized at weekly granularity,
        this dashboard uses:

        - W1 — approximately one week after signup
        - W2 — approximately two weeks after signup
        - W4 — approximately four weeks after signup

        These should not be interpreted as exact daily D7, D14, or D30
        retention measurements.

        **Maturity**

        Recent cohorts may not have reached later weeks yet. Those cells
        remain blank and are excluded from calculations for that week.

        **Interpretation**

        The underlying SaaS event dataset is synthetic. Retention patterns
        should therefore be treated as analytical demonstrations rather
        than causal evidence about real customer behavior.
        """
    )
