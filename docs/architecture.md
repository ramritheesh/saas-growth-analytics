# SaaS Product Growth & Revenue Intelligence

## System Architecture

This project is an end-to-end SaaS analytics platform that transforms product, customer, experiment, and subscription data into actionable business intelligence.

### Data Flow

```text
Python Synthetic Data Generator
            |
            v
      Raw Parquet Data
            |
            v
          DuckDB
            |
            v
     Staging SQL Models
            |
            v
      Analytics Marts
            |
       +----+----+
       |         |
       v         v
   Analytics     ML
       |         |
       |     Churn Prediction
       |         |
       |     Revenue Risk
       |         |
       +----+----+
            |
            v
    Streamlit Dashboard
