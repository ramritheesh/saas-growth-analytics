CREATE OR REPLACE TABLE mart_customer_intelligence AS

WITH customer_events AS (
    SELECT
        user_id,
        COUNT(*) AS total_events,
        COUNT(DISTINCT event_name) AS distinct_event_types,
        COUNT(DISTINCT DATE(event_ts)) AS active_days,
        MIN(event_ts) AS first_event_ts,
        MAX(event_ts) AS last_event_ts
    FROM stg_events
    GROUP BY user_id
),

customer_features AS (
    SELECT
        u.user_id,
        u.signup_date,
        u.company_size,
        u.industry,
        u.acquisition_channel,
        u.plan_type,

        COALESCE(e.total_events, 0) AS total_events,
        COALESCE(e.distinct_event_types, 0) AS distinct_event_types,
        COALESCE(e.active_days, 0) AS active_days,

        e.first_event_ts,
        e.last_event_ts,

        COALESCE(s.mrr, 0) AS mrr,

        CASE
            WHEN s.cancel_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_churned,

        CASE
            WHEN s.paid_start_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_paid

    FROM stg_users u

    LEFT JOIN customer_events e
        ON u.user_id = e.user_id

    LEFT JOIN stg_subscriptions s
        ON u.user_id = s.user_id
),

customer_scoring AS (
    SELECT
        *,

        /*
        Engagement score:
        combines frequency, breadth of product usage,
        and consistency of activity.
        */

        LEAST(
            100,
            (
                LEAST(total_events, 50) / 50.0 * 40
                +
                LEAST(distinct_event_types, 8) / 8.0 * 30
                +
                LEAST(active_days, 20) / 20.0 * 30
            )
        ) AS engagement_score

    FROM customer_features
)

SELECT
    *,

    CASE
        WHEN is_churned = 1 THEN 'Churned'

        WHEN mrr > 0
             AND engagement_score >= 70
             AND active_days >= 15
            THEN 'High Value'

        WHEN mrr > 0
             AND engagement_score >= 45
            THEN 'Engaged'

        WHEN mrr > 0
             AND engagement_score < 45
            THEN 'At Risk'


        WHEN mrr = 0
             AND engagement_score >= 70
            THEN 'Growth Opportunity'

	WHEN mrr = 0
	     AND engagement_score >= 40
            THEN 'Nurture'

        ELSE 'Low Engagement'
    END AS customer_segment,

    CASE
        WHEN mrr >= 500 THEN 'High Revenue'
        WHEN mrr >= 200 THEN 'Medium Revenue'
        WHEN mrr > 0 THEN 'Low Revenue'
        ELSE 'Non-Paying'
    END AS revenue_segment,

    CASE
        WHEN engagement_score >= 70 THEN 'Highly Engaged'
        WHEN engagement_score >= 40 THEN 'Moderately Engaged'
        WHEN engagement_score > 0 THEN 'Low Engagement'
        ELSE 'Inactive'
    END AS engagement_segment

FROM customer_scoring;
