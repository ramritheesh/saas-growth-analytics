CREATE OR REPLACE TABLE mart_revenue_risk AS

WITH customer_data AS (

    SELECT
        user_id,
        company_size,
        industry,
        acquisition_channel,
        plan_type,
        mrr,
        is_churned,
        customer_segment,
        active_days,
        total_events

    FROM mart_customer_intelligence
),

risk_model AS (

    SELECT
        *,

        CASE

            WHEN is_churned = 1 THEN 1.00

            WHEN customer_segment = 'At Risk'
                 AND active_days <= 2
                THEN 0.70

            WHEN customer_segment = 'At Risk'
                THEN 0.50

            WHEN customer_segment = 'Engaged'
                 AND active_days <= 5
                THEN 0.30

            ELSE 0.10

        END AS estimated_churn_probability

    FROM customer_data
)

SELECT

    *,

    ROUND(
        mrr * estimated_churn_probability,
        2
    ) AS revenue_at_risk,

    CASE

        WHEN mrr * estimated_churn_probability >= 100
            THEN 'High'

        WHEN mrr * estimated_churn_probability >= 30
            THEN 'Medium'

        ELSE 'Low'

    END AS revenue_risk_tier

FROM risk_model;
