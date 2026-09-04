"""
Core analysis functions for the SaaS Product Growth & Revenue Intelligence project.

Includes:
    1. Funnel analysis
    2. Cohort retention analysis
    3. A/B experiment analysis
    4. Temporal churn-risk modeling
    5. Revenue-at-risk estimation

Can be run with:

    python -m python.src.analysis

or imported by Streamlit pages.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from statsmodels.stats.proportion import proportions_ztest


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = ROOT / "data" / "processed"

RAW_DIR = ROOT / "data" / "raw"


# =============================================================================
# FUNNEL ANALYSIS
# =============================================================================


def analyze_funnel(funnel_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reshape mart_funnel into a step-by-step conversion table.

    Returns one row per funnel step with:
        - users
        - conversion_rate
        - step_rate
        - drop_off

    Uses the overall ROLLUP row where acquisition_channel IS NULL.
    """

    overall = funnel_df[
        funnel_df["acquisition_channel"].isna()
    ].iloc[0]

    steps = [
        "signup",
        "workspace",
        "invite",
        "project",
        "paid",
    ]

    columns = [
        "signup_users",
        "workspace_users",
        "invite_users",
        "project_users",
        "paid_users",
    ]

    rows = []

    for i, (step, column) in enumerate(
        zip(steps, columns, strict=True)
    ):
        users = int(overall[column])

        previous_users = (
            int(overall[columns[i - 1]])
            if i > 0
            else users
        )

        rows.append(
            {
                "step": step,
                "users": users,
                "conversion_rate": (
                    users / int(overall["total_users"])
                    if overall["total_users"]
                    else 0
                ),
                "step_rate": (
                    users / previous_users
                    if previous_users
                    else 0
                ),
                "drop_off": (
                    1 - (users / previous_users)
                    if previous_users
                    else 0
                ),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# COHORT RETENTION
# =============================================================================


def build_cohort_heatmap(
    cohort_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert mart_cohort_retention into a heatmap-ready matrix.

    Rows:
        cohort_week

    Columns:
        W0, W1, W2, ...

    Values:
        retention_rate
    """

    pivot = cohort_df.pivot_table(
        index="cohort_week",
        columns="weeks_since_signup",
        values="retention_rate",
        aggfunc="first",
    )

    pivot.index = pivot.index.astype(str)

    pivot.columns = [
        f"W{int(column)}"
        for column in pivot.columns
    ]

    return pivot


# =============================================================================
# A/B EXPERIMENT ANALYSIS
# =============================================================================


def analyze_experiment(
    experiment_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run a two-proportion z-test on experiment results.

    Returns:
        - control users
        - treatment users
        - control activation rate
        - treatment activation rate
        - absolute lift
        - relative lift
        - z-statistic
        - p-value
        - significance flag
    """

    control = experiment_df[
        experiment_df["variant"] == "control"
    ].iloc[0]

    treatment = experiment_df[
        experiment_df["variant"] == "treatment"
    ].iloc[0]

    successes = np.array(
        [
            treatment["activated_users"],
            control["activated_users"],
        ]
    )

    observations = np.array(
        [
            treatment["users"],
            control["users"],
        ]
    )

    z_stat, p_value = proportions_ztest(
        successes,
        observations,
    )

    lift = (
        treatment["activation_rate"]
        - control["activation_rate"]
    )

    relative_lift = (
        lift / control["activation_rate"]
        if control["activation_rate"]
        else 0
    )

    return pd.DataFrame(
        {
            "control_users": [
                int(control["users"])
            ],
            "treatment_users": [
                int(treatment["users"])
            ],
            "control_rate": [
                control["activation_rate"]
            ],
            "treatment_rate": [
                treatment["activation_rate"]
            ],
            "absolute_lift": [
                round(lift, 4)
            ],
            "relative_lift": [
                round(relative_lift, 4)
            ],
            "z_statistic": [
                round(z_stat, 4)
            ],
            "p_value": [
                round(p_value, 6)
            ],
            "significant": [
                p_value < 0.05
            ],
        }
    )


# =============================================================================
# TEMPORAL CHURN RISK MODEL
# =============================================================================


def score_churn_risk() -> pd.DataFrame:
    """
    Predict 180-day customer churn risk using information
    available at a fixed prediction cutoff.

    Prediction design
    -----------------

    Prediction cutoff:
        2025-07-01

    Prediction horizon:
        180 days after cutoff

    Customer population:
        Customers who were actively paying at the cutoff.

    Behavioral window:
        Previous 90 days.

    ML features:
        - days_since_last_event
        - total_events
        - distinct_events
        - active_days
        - customer_tenure_days

    NOT used as ML features:
        - mrr
        - plan_type
        - industry
        - acquisition_channel
        - cancel_date

    The customer attributes are retained for:
        - dashboard filters
        - segmentation
        - business analysis

    Revenue at risk:
        current MRR × predicted churn probability

    This represents modeled expected revenue exposure,
    not guaranteed revenue loss.
    """

    # -------------------------------------------------------------------------
    # 1. LOAD RAW DATA
    # -------------------------------------------------------------------------

    users = pd.read_parquet(
        RAW_DIR / "dim_users.parquet"
    )

    events = pd.read_parquet(
        RAW_DIR / "fact_events.parquet"
    )

    subs = pd.read_parquet(
        RAW_DIR / "fact_subscriptions.parquet"
    )

    # -------------------------------------------------------------------------
    # 2. DEFINE TEMPORAL PREDICTION WINDOW
    # -------------------------------------------------------------------------

    cutoff = pd.Timestamp(
        "2025-07-01"
    )

    horizon = (
        cutoff
        + pd.Timedelta(days=180)
    )

    recent_start = (
        cutoff
        - pd.Timedelta(days=90)
    )

    print("\n" + "=" * 70)
    print("TEMPORAL CHURN RISK MODEL")
    print("=" * 70)

    print(
        f"Prediction cutoff : {cutoff.date()}"
    )

    print(
        f"Prediction horizon: {horizon.date()}"
    )

    print(
        f"Behavior window   : "
        f"{recent_start.date()} to {cutoff.date()}"
    )

    # -------------------------------------------------------------------------
    # 3. SELECT ACTIVE PAID CUSTOMERS AT CUTOFF
    #
    # We only want customers who were active paid customers
    # when the prediction was made.
    #
    # This prevents already-churned customers from entering
    # the prediction population.
    # -------------------------------------------------------------------------

    customers = subs[
        subs["paid_start_date"].notna()
        & (
            subs["paid_start_date"]
            <= cutoff
        )
        & (
            subs["cancel_date"].isna()
            | (
                subs["cancel_date"]
                > cutoff
            )
        )
    ].copy()

    print(
        f"\nActive paid customers at cutoff: "
        f"{len(customers):,}"
    )

    # -------------------------------------------------------------------------
    # 4. ADD CUSTOMER ATTRIBUTES
    #
    # These are NOT ML features.
    #
    # They are included so the dashboard can answer questions such as:
    #
    #   Which plan has the highest risk?
    #   Which industry has the highest revenue exposure?
    #   Which acquisition channel has the most at-risk customers?
    # -------------------------------------------------------------------------

    customer_attributes = users[
        [
            "user_id",
            "plan_type",
            "industry",
            "acquisition_channel",
        ]
    ].copy()

    customers = customers.merge(
        customer_attributes,
        on="user_id",
        how="left",
    )

    # -------------------------------------------------------------------------
    # 5. SELECT EVENTS FROM PREVIOUS 90 DAYS
    # -------------------------------------------------------------------------

    recent_events = events[
        (events["event_ts"] >= recent_start)
        & (events["event_ts"] <= cutoff)
    ].copy()

    print(
        f"Events in behavior window: "
        f"{len(recent_events):,}"
    )

    # -------------------------------------------------------------------------
    # 6. BUILD BEHAVIORAL FEATURES
    # -------------------------------------------------------------------------

    event_features = (
        recent_events
        .groupby("user_id")
        .agg(
            last_event_ts=(
                "event_ts",
                "max",
            ),
            total_events=(
                "event_id",
                "count",
            ),
            distinct_events=(
                "event_name",
                "nunique",
            ),
            active_days=(
                "event_ts",
                lambda x: x.dt.date.nunique(),
            ),
        )
        .reset_index()
    )

    # -------------------------------------------------------------------------
    # 7. MERGE BEHAVIORAL FEATURES
    # -------------------------------------------------------------------------

    customers = customers.merge(
        event_features,
        on="user_id",
        how="left",
    )

    # -------------------------------------------------------------------------
    # 8. HANDLE CUSTOMERS WITH NO RECENT EVENTS
    # -------------------------------------------------------------------------

    for column in [
        "total_events",
        "distinct_events",
        "active_days",
    ]:
        customers[column] = (
            customers[column]
            .fillna(0)
        )

    # -------------------------------------------------------------------------
    # 9. CALCULATE ACTIVITY RECENCY
    # -------------------------------------------------------------------------

    customers[
        "days_since_last_event"
    ] = (
        cutoff
        - customers["last_event_ts"]
    ).dt.total_seconds() / 86400

    # Customers with no events in the
    # behavioral window receive 999.
    customers[
        "days_since_last_event"
    ] = (
        customers[
            "days_since_last_event"
        ]
        .fillna(999)
    )

    # -------------------------------------------------------------------------
    # 10. CALCULATE CUSTOMER TENURE
    # -------------------------------------------------------------------------

    customers[
        "customer_tenure_days"
    ] = (
        cutoff
        - customers["paid_start_date"]
    ).dt.total_seconds() / 86400

    # -------------------------------------------------------------------------
    # 11. CREATE FUTURE CHURN TARGET
    #
    # Target = 1 when cancellation happens:
    #
    #       AFTER the prediction cutoff
    #
    #       AND within the next 180 days
    #
    # This is what makes the problem a forward-looking
    # churn prediction task.
    # -------------------------------------------------------------------------

    customers[
        "churned_next_180d"
    ] = (
        customers["cancel_date"].notna()
        & (
            customers["cancel_date"]
            > cutoff
        )
        & (
            customers["cancel_date"]
            <= horizon
        )
    ).astype(int)

    # -------------------------------------------------------------------------
    # 12. DEFINE ML FEATURES
    #
    # IMPORTANT:
    #
    # MRR is excluded.
    # Cancel date is excluded.
    # Customer segmentation fields are excluded.
    #
    # Only information known at prediction time is used.
    # -------------------------------------------------------------------------

    feature_cols = [
        "days_since_last_event",
        "total_events",
        "distinct_events",
        "active_days",
        "customer_tenure_days",
    ]

    X = customers[
        feature_cols
    ].copy()

    y = customers[
        "churned_next_180d"
    ].copy()

    # -------------------------------------------------------------------------
    # 13. DATASET DIAGNOSTICS
    # -------------------------------------------------------------------------

    print("\nModel population:")
    print(
        f"Customers    : {len(customers):,}"
    )

    print(
        f"Future churners: {y.sum():,}"
    )

    print(
        f"Future churn rate: {y.mean():.2%}"
    )

    print("\nML features:")

    for feature in feature_cols:
        print(
            f"  - {feature}"
        )

    # -------------------------------------------------------------------------
    # 14. TRAIN / TEST SPLIT
    # -------------------------------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y,
        )
    )

    # -------------------------------------------------------------------------
    # 15. SCALE FEATURES
    #
    # Fit scaler ONLY on training data.
    # -------------------------------------------------------------------------

    scaler = StandardScaler()

    X_train_scaled = (
        scaler.fit_transform(X_train)
    )

    X_test_scaled = (
        scaler.transform(X_test)
    )

    # -------------------------------------------------------------------------
    # 16. TRAIN LOGISTIC REGRESSION
    #
    # class_weight="balanced" handles class imbalance.
    # -------------------------------------------------------------------------

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

    model.fit(
        X_train_scaled,
        y_train,
    )

    # -------------------------------------------------------------------------
    # 17. MODEL EVALUATION
    # -------------------------------------------------------------------------

    test_probabilities = (
        model.predict_proba(
            X_test_scaled
        )[:, 1]
    )

    test_predictions = (
        test_probabilities >= 0.50
    ).astype(int)

    roc_auc = roc_auc_score(
        y_test,
        test_probabilities,
    )

    pr_aus = average_precision_score(
        y_test,
        test_probabilities,
    )

    precision = precision_score(
        y_test,
        test_predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        test_predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        test_predictions,
        zero_division=0,
    )

    cm = confusion_matrix(
        y_test,
        test_predictions,
    )

    # -------------------------------------------------------------------------
    # 18. PRINT MODEL PERFORMANCE
    # -------------------------------------------------------------------------

    print("\nModel performance:")

    print(
        f"ROC-AUC : {roc_auc:.4f}"
    )

    print(
        f"PR-AUC  : {pr_aus:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1 Score : {f1:.4f}"
    )

    print("\nConfusion Matrix:")
    print(cm)

    # -------------------------------------------------------------------------
    # 19. SCORE ALL ELIGIBLE CUSTOMERS
    # -------------------------------------------------------------------------

    all_scaled = scaler.transform(X)

    customers[
        "churn_probability"
    ] = (
        model.predict_proba(
            all_scaled
        )[:, 1]
    )

    # -------------------------------------------------------------------------
    # 20. BUSINESS-DRIVEN RISK TIERS
    #
    # Bottom 70%  -> Low
    # Next 20%    -> Medium
    # Top 10%     -> High
    #
    # rank(method="first") avoids qcut problems
    # when multiple customers have identical probabilities.
    # -------------------------------------------------------------------------

    customers["risk_tier"] = pd.qcut(
        customers[
            "churn_probability"
        ].rank(
            method="first"
        ),
        q=[
            0,
            0.70,
            0.90,
            1.00,
        ],
        labels=[
            "low",
            "medium",
            "high",
        ],
    )

    # -------------------------------------------------------------------------
    # 21. CALCULATE REVENUE AT RISK
    #
    # Revenue at risk =
    #
    #       MRR × predicted churn probability
    #
    # This is an expected-risk estimate.
    # It is NOT guaranteed revenue loss.
    # -------------------------------------------------------------------------

    customers[
        "revenue_at_risk"
    ] = (
        customers["mrr"]
        * customers["churn_probability"]
    ).round(2)

    # -------------------------------------------------------------------------
    # 22. ADD PREDICTION DATE
    # -------------------------------------------------------------------------

    customers[
        "prediction_date"
    ] = cutoff

    # -------------------------------------------------------------------------
    # 23. TOP-DECILE RISK CAPTURE
    #
    # This tells us how many actual test-set churners
    # were captured inside the highest 10% predicted-risk group.
    # -------------------------------------------------------------------------

    test_results = pd.DataFrame(
        {
            "actual": y_test.values,
            "probability": test_probabilities,
        }
    )

    top_decile_threshold = (
        test_results[
            "probability"
        ].quantile(0.90)
    )

    top_decile = test_results[
        test_results[
            "probability"
        ]
        >= top_decile_threshold
    ]

    total_test_churners = (
        test_results["actual"].sum()
    )

    top_decile_churners = (
        top_decile["actual"].sum()
    )

    if total_test_churners > 0:
        top_decile_churn_capture = (
            top_decile_churners
            / total_test_churners
        )
    else:
        top_decile_churn_capture = 0

    if len(top_decile) > 0:
        top_decile_churn_rate = (
            top_decile["actual"].mean()
        )
    else:
        top_decile_churn_rate = 0

    print(
        "\nTop-decile risk performance:"
    )

    print(
        f"Customers in top 10%: "
        f"{len(top_decile):,}"
    )

    print(
        f"Actual churners captured: "
        f"{top_decile_churners:,} / "
        f"{total_test_churners:,}"
    )

    print(
        f"Churn capture: "
        f"{top_decile_churn_capture:.2%}"
    )

    print(
        f"Top-decile churn rate: "
        f"{top_decile_churn_rate:.2%}"
    )

    # -------------------------------------------------------------------------
    # 24. RISK DISTRIBUTION
    # -------------------------------------------------------------------------

    risk_distribution = (
        customers[
            "risk_tier"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nRisk distribution:"
    )

    for tier, count in (
        risk_distribution.items()
    ):
        print(
            f"{str(tier).capitalize():<8}: "
            f"{count:,}"
        )

    # -------------------------------------------------------------------------
    # 25. REVENUE EXPOSURE BY RISK TIER
    # -------------------------------------------------------------------------

    revenue_summary = (
        customers
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
        )
        .reset_index()
    )

    print(
        "\nRevenue exposure by risk tier:"
    )

    print(
        revenue_summary.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # 26. OVERALL REVENUE EXPOSURE
    # -------------------------------------------------------------------------

    total_mrr = customers[
        "mrr"
    ].sum()

    total_revenue_at_risk = (
        customers[
            "revenue_at_risk"
        ].sum()
    )

    if total_mrr > 0:
        revenue_exposure_rate = (
            total_revenue_at_risk
            / total_mrr
        )
    else:
        revenue_exposure_rate = 0

    print(
        "\nRevenue exposure:"
    )

    print(
        f"Current MRR: "
        f"${total_mrr:,.2f}"
    )

    print(
        f"Modeled revenue exposure: "
        f"${total_revenue_at_risk:,.2f}"
    )

    print(
        f"Exposure as % of MRR: "
        f"{revenue_exposure_rate:.2%}"
    )

    # -------------------------------------------------------------------------
    # 27. FINAL OUTPUT COLUMNS
    #
    # Customer attributes are included so Streamlit can use them
    # for filtering and segmentation.
    # -------------------------------------------------------------------------

    output_cols = [
        "user_id",
        "prediction_date",
        "plan_type",
        "industry",
        "acquisition_channel",
        "churn_probability",
        "risk_tier",
        "customer_tenure_days",
        "days_since_last_event",
        "total_events",
        "distinct_events",
        "active_days",
        "mrr",
        "revenue_at_risk",
        "churned_next_180d",
    ]

    predictions = customers[
        output_cols
    ].copy()

    # -------------------------------------------------------------------------
    # 28. SAVE PREDICTIONS
    # -------------------------------------------------------------------------

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / "churn_predictions.parquet"
    )

    predictions.to_parquet(
        output_path,
        index=False,
    )

    print(
        "\nPrediction file saved:"
    )

    print(
        output_path
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "CHURN MODEL COMPLETE"
    )

    print(
        "=" * 70
    )

    return predictions


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    """
    Run all analysis components from the command line.
    """

    print("=" * 60)

    print(
        "SaaS Growth Analytics — Analysis Results"
    )

    print("=" * 60)

    # -------------------------------------------------------------------------
    # Funnel
    # -------------------------------------------------------------------------

    funnel_df = pd.read_parquet(
        PROCESSED_DIR
        / "mart_funnel.parquet"
    )

    funnel = analyze_funnel(
        funnel_df
    )

    print(
        "\n── Funnel Conversion ──"
    )

    print(
        funnel.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Cohort retention
    # -------------------------------------------------------------------------

    cohort_df = pd.read_parquet(
        PROCESSED_DIR
        / "mart_cohort_retention.parquet"
    )

    heatmap = build_cohort_heatmap(
        cohort_df
    )

    print(
        "\n── Cohort Retention "
        "(first 5 cohorts) ──"
    )

    print(
        heatmap.head().to_string()
    )

    # -------------------------------------------------------------------------
    # A/B experiment
    # -------------------------------------------------------------------------

    exp_df = pd.read_parquet(
        PROCESSED_DIR
        / "mart_experiment_results.parquet"
    )

    exp_results = analyze_experiment(
        exp_df
    )

    print(
        "\n── A/B Test: onboarding_v2 ──"
    )

    print(
        exp_results.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Churn model
    # -------------------------------------------------------------------------

    print(
        "\n── Churn Risk Scoring ──"
    )

    churn = score_churn_risk()

    print(
        "\nRisk tier distribution:"
    )

    print(
        churn[
            "risk_tier"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nMean churn probability: "
        f"{churn['churn_probability'].mean():.3f}"
    )

    print(
        "\nDone."
    )


# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    main()
