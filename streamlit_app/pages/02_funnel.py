"""
Funnel Analysis — conversion, drop-off, channel performance, and opportunities.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from python.src.analysis import analyze_funnel
from streamlit_app.utils.data_loader import load_funnel


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Funnel Analysis",
    page_icon="🔎",
    layout="wide",
)

st.title("Funnel Analysis")
st.caption(
    "Identify conversion bottlenecks and compare funnel performance "
    "across acquisition channels."
)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

funnel_raw = load_funnel()

if funnel_raw.empty:
    st.error("Funnel data could not be loaded.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# CHANNEL FILTER
# ─────────────────────────────────────────────────────────────────────────────

channels = sorted(
    funnel_raw["acquisition_channel"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected = st.selectbox(
    "Acquisition Channel",
    ["All", *channels],
)


# ─────────────────────────────────────────────────────────────────────────────
# BUILD FUNNEL DATA
# ─────────────────────────────────────────────────────────────────────────────

if selected == "All":

    overall = funnel_raw[
        funnel_raw["acquisition_channel"].isna()
    ]

    if overall.empty:
        overall = funnel_raw.iloc[[0]]

else:

    selected_rows = funnel_raw[
        funnel_raw["acquisition_channel"].astype(str) == selected
    ]

    if selected_rows.empty:
        st.error(f"No funnel data found for {selected}.")
        st.stop()

    overall = selected_rows


overall = overall.iloc[0]


# Create the five funnel stages.
funnel = analyze_funnel(
    funnel_raw
    if selected == "All"
    else funnel_raw[
        funnel_raw["acquisition_channel"].isna()
        | (
            funnel_raw["acquisition_channel"].astype(str) == selected
        )
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# FUNNEL OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Conversion Funnel")

fig = go.Figure(
    go.Funnel(
        y=funnel["step"],
        x=funnel["users"],
        textinfo="value+percent initial",
        marker=dict(
            color=[
                "#636EFA",
                "#EF553B",
                "#00CC96",
                "#AB63FA",
                "#FFA15A",
            ]
        ),
        connector=dict(
            line=dict(
                color="rgba(255,255,255,0.25)",
                width=1,
            )
        ),
    )
)

fig.update_layout(
    funnelmode="stack",
    height=430,
    margin=dict(l=20, r=20, t=30, b=20),
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# STEP-BY-STEP CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Step-by-Step Conversion")

metric_cols = st.columns(len(funnel))

for i, (_, row) in enumerate(funnel.iterrows()):

    with metric_cols[i]:

        st.metric(
            row["step"].title(),
            f"{int(row['users']):,}",
        )

        if i > 0:

            st.caption(
                f"Conversion: {row['step_rate']:.1%}"
            )

            st.caption(
                f"Drop-off: {row['drop_off']:.1%}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# BOTTLENECK ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

step_rates = funnel["step_rate"].iloc[1:].astype(float)
step_names = funnel["step"].iloc[1:].tolist()

weakest_index = step_rates.idxmin()

weakest_stage = funnel.loc[
    weakest_index,
    "step",
]

weakest_rate = float(
    funnel.loc[weakest_index, "step_rate"]
)

weakest_dropoff = 1 - weakest_rate


st.warning(
    f"**Primary conversion bottleneck:** "
    f"{weakest_stage.title()} — only **{weakest_rate:.1%}** "
    f"of users progress from the previous stage, representing "
    f"a **{weakest_dropoff:.1%} drop-off**."
)


# ─────────────────────────────────────────────────────────────────────────────
# CHANNEL PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

if selected == "All":

    st.divider()

    st.subheader("Channel Performance")

    channel_df = funnel_raw.dropna(
        subset=["acquisition_channel"]
    ).copy()

    channel_df["acquisition_channel"] = (
        channel_df["acquisition_channel"]
        .astype(str)
        .str.replace("_", " ")
        .str.title()
    )

    # ── Channel KPI cards ───────────────────────────────────────────────────

    best_channel_row = channel_df.loc[
        channel_df["overall_conversion_rate"].idxmax()
    ]

    best_channel = best_channel_row[
        "acquisition_channel"
    ]

    best_conversion = float(
        best_channel_row["overall_conversion_rate"]
    )

    worst_channel_row = channel_df.loc[
        channel_df["overall_conversion_rate"].idxmin()
    ]

    worst_channel = worst_channel_row[
        "acquisition_channel"
    ]

    worst_conversion = float(
        worst_channel_row["overall_conversion_rate"]
    )

    channel_gap = best_conversion - worst_conversion

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Best Overall Channel",
        best_channel,
        delta=f"{best_conversion:.1%} signup → paid",
    )

    c2.metric(
        "Lowest Overall Channel",
        worst_channel,
        delta=f"{worst_conversion:.1%} signup → paid",
    )

    c3.metric(
        "Best-to-Worst Gap",
        f"{channel_gap:.2%}",
    )


    # ── Conversion comparison ───────────────────────────────────────────────

    chart_col1, chart_col2 = st.columns(2)


    with chart_col1:

        fig_channel = px.bar(
            channel_df,
            x="acquisition_channel",
            y="overall_conversion_rate",
            text="overall_conversion_rate",
            title="Signup → Paid Conversion by Channel",
        )

        fig_channel.update_traces(
            texttemplate="%{text:.1%}",
            textposition="outside",
        )

        fig_channel.update_layout(
            xaxis_title="",
            yaxis_title="Conversion Rate",
            yaxis_tickformat=".0%",
            showlegend=False,
            height=400,
        )

        st.plotly_chart(
            fig_channel,
            use_container_width=True,
        )


    # ── Step conversion matrix ──────────────────────────────────────────────

    with chart_col2:

        matrix = channel_df[
            [
                "acquisition_channel",
                "signup_to_workspace_rate",
                "workspace_to_invite_rate",
                "invite_to_project_rate",
                "project_to_paid_rate",
            ]
        ].copy()

        matrix = matrix.rename(
            columns={
                "signup_to_workspace_rate": "Signup → Workspace",
                "workspace_to_invite_rate": "Workspace → Invite",
                "invite_to_project_rate": "Invite → Project",
                "project_to_paid_rate": "Project → Paid",
            }
        )

        matrix = matrix.set_index(
            "acquisition_channel"
        )

        fig_heatmap = px.imshow(
            matrix,
            text_auto=".1%",
            aspect="auto",
            title="Stage Conversion by Channel",
            labels={
                "x": "Funnel Stage",
                "y": "Acquisition Channel",
                "color": "Conversion",
            },
        )

        fig_heatmap.update_layout(
            height=400,
        )

        st.plotly_chart(
            fig_heatmap,
            use_container_width=True,
        )


    # ── Detailed channel table ──────────────────────────────────────────────

    st.markdown("#### Channel Conversion Detail")

    detail = channel_df[
        [
            "acquisition_channel",
            "total_users",
            "signup_to_workspace_rate",
            "workspace_to_invite_rate",
            "invite_to_project_rate",
            "project_to_paid_rate",
            "overall_conversion_rate",
        ]
    ].copy()

    detail = detail.rename(
        columns={
            "acquisition_channel": "Channel",
            "total_users": "Users",
            "signup_to_workspace_rate": "Signup → Workspace",
            "workspace_to_invite_rate": "Workspace → Invite",
            "invite_to_project_rate": "Invite → Project",
            "project_to_paid_rate": "Project → Paid",
            "overall_conversion_rate": "Signup → Paid",
        }
    )

    percentage_columns = [
        "Signup → Workspace",
        "Workspace → Invite",
        "Invite → Project",
        "Project → Paid",
        "Signup → Paid",
    ]

    for column in percentage_columns:
        detail[column] = detail[column].map(
            lambda x: f"{x:.1%}"
        )

    detail["Users"] = detail["Users"].map(
        lambda x: f"{int(x):,}"
    )

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
    )


    # ─────────────────────────────────────────────────────────────────────────
    # CHANNEL INTERPRETATION
    # ─────────────────────────────────────────────────────────────────────────

    st.subheader("Channel Interpretation")

    # Determine how close the channels are.
    conversion_rates = channel_df[
        "overall_conversion_rate"
    ].astype(float)

    relative_spread = (
        conversion_rates.max() - conversion_rates.min()
    )

    if relative_spread <= 0.01:

        st.info(
            f"Overall signup-to-paid conversion is tightly clustered "
            f"across channels, ranging from "
            f"**{conversion_rates.min():.1%} to "
            f"{conversion_rates.max():.1%}**. "
            "This suggests the primary growth opportunity is likely "
            "downstream in the product funnel rather than simply "
            "shifting acquisition spend between channels."
        )

    else:

        st.info(
            f"Signup-to-paid conversion varies across acquisition "
            f"channels from **{conversion_rates.min():.1%} to "
            f"{conversion_rates.max():.1%}**. "
            "Channel-level differences should be investigated alongside "
            "user volume and downstream funnel behavior before reallocating "
            "acquisition investment."
        )


# ─────────────────────────────────────────────────────────────────────────────
# OPPORTUNITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

st.subheader("Opportunity Analysis")

op1, op2 = st.columns(2)


with op1:

    st.markdown("### 🔴 Biggest Conversion Bottleneck")

    st.markdown(
        f"""
        **{weakest_stage.title()}** has the weakest step conversion
        at **{weakest_rate:.1%}**.

        That means approximately **{weakest_dropoff:.1%}** of users
        reaching the previous stage do not progress.
        """
    )

    st.write(
        "Investigate the user experience, onboarding friction, "
        "pricing, value communication, and product activation signals "
        "around this transition."
    )


with op2:

    st.markdown("### 📈 Overall Funnel Opportunity")

    overall_conversion = float(
        overall["overall_conversion_rate"]
    )

    st.markdown(
        f"""
        Current signup-to-paid conversion is **{overall_conversion:.1%}**.

        The funnel currently converts approximately
        **{int(overall["signup_users"]):,} signups into "
        f"{int(overall["paid_users"]):,} paying customers**.
        """
    )

    st.write(
        "Improving downstream conversion can create additional paid "
        "customers without requiring a proportional increase in top-of-"
        "funnel acquisition."
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Business Interpretation")

st.markdown(
    f"""
**Primary finding:** the largest leakage occurs at
**{weakest_stage.title()}**, where the step conversion rate is only
**{weakest_rate:.1%}**.

**Overall funnel:** signup-to-paid conversion is
**{overall_conversion:.1%}**, meaning the majority of acquired users
do not reach the paid stage.

**Recommended focus:** prioritize analysis of the downstream conversion
experience before assuming that increasing acquisition volume alone will
solve the growth problem.
"""
)


# ─────────────────────────────────────────────────────────────────────────────
# METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("Methodology & Limitations"):

    st.markdown(
        """
        **Funnel definition**

        The funnel follows users through:

        `Signup → Workspace → Invite → Project → Paid`

        **Step conversion**

        Each step conversion rate is calculated relative to the immediately
        preceding stage.

        **Overall conversion**

        Signup-to-paid conversion is calculated as:

        `Paid users / Signup users`

        **Channel analysis**

        Acquisition channels are compared using stage-level and
        signup-to-paid conversion rates.

        **Interpretation**

        The underlying dataset is synthetic. Funnel differences should
        therefore be interpreted as analytical demonstrations rather than
        causal evidence about real acquisition channels or customer behavior.
        """
    )
