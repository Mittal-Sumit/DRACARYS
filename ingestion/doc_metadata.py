"""
Metadata for documents in docs/.
Add an entry here whenever a new document is added.

ChromaDB metadata values must be scalars (str, int, float, bool).
Lists are stored as comma-separated strings.
"""

_DOC_METADATA = {
    # ── Healthcare & Pharma ──────────────────────────────────────────────────
    "Abbott_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Abbott",
        "display_name": "Abbott GCP Data Engineering & BI Analytics",
        "industry": "Healthcare / Pharmaceuticals / Diagnostics",
        "services": "Data Engineering, Business Intelligence, Self-Serve Analytics",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Composer, Pub/Sub, GCS, Dataproc, Vertex AI, Cloud Run, Looker, Power BI, React.js, Node.js",
        "solution_patterns": "cloud data warehouse, BI dashboards, data engineering, data lake",
    },
    "Cipla_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Cipla",
        "display_name": "Cipla BI & Data Engineering",
        "industry": "Healthcare / Pharmaceuticals",
        "services": "Business Intelligence, Data Engineering, Analytics",
        "cloud": "Azure",
        "technologies": "Power BI, SQL, ETL Pipelines, ADF, Databricks, Azure Synapse",
        "solution_patterns": "BI dashboards, ETL pipelines, data engineering, cloud data warehouse",
    },
    "SunPharma_GCP_DE_ReactNode_CaseStudy.pdf": {
        "client": "Sun Pharma",
        "display_name": "Sun Pharma GCP Data Engineering",
        "industry": "Healthcare / Pharmaceuticals",
        "services": "Data Engineering, Web Development, Cloud",
        "cloud": "GCP",
        "technologies": "GCP, BigQuery, Looker, React, Node.js, Cloud Dataflow",
        "solution_patterns": "data engineering, cloud data warehouse, web application",
    },
    "Philips_Healthcare_PredictiveMaintenance_POC.pdf": {
        "client": "Philips",
        "display_name": "Philips Healthcare Predictive Maintenance POC",
        "industry": "Healthcare / Manufacturing",
        "services": "Predictive Maintenance, IoT Analytics, AI/ML",
        "cloud": "Unknown",
        "technologies": "Python, Machine Learning, IoT",
        "solution_patterns": "predictive maintenance, IoT analytics, ML/AI",
    },
    "Siemens_Healthineers_CaseStudy.pdf": {
        "client": "Siemens Healthineers",
        "display_name": "Siemens Healthineers Data Analytics",
        "industry": "Healthcare / Manufacturing",
        "services": "Data Analytics, Business Intelligence, Reporting",
        "cloud": "Azure",
        "technologies": "Power BI, SQL, PySpark, Databricks, ADLS Gen2, Azure Data Factory (ADF), Azure Machine Learning, Azure Synapse, Azure Event Hubs, Azure Key Vault",
        "solution_patterns": "data lake,BI dashboards, data analytics, machine learning, reporting, cloud data warehouse",
    },
    # ── FMCG & Retail ────────────────────────────────────────────────────────
    "CocaCola_DemandForecasting_CaseStudy.pdf": {
        "client": "Coca-Cola",
        "display_name": "Coca-Cola Demand Forecasting",
        "industry": "FMCG / Beverage",
        "services": "Demand Forecasting, AI/ML, Analytics",
        "cloud": "AWS",
        "technologies": "Amazon Forecast, SageMaker, AmazonS3, Redshift, QuickSight, AWS Glue, MWAA (Airflow)",
        "solution_patterns": "demand forecasting, ML/AI, predictive analytics, cloud data warehouse, data lake",
    },
    "Nestle_DataWarehouse_CaseStudy.pdf": {
        "client": "Nestle",
        "display_name": "Nestle Global Data Warehouse",
        "industry": "FMCG / Food & Beverage",
        "services": "Data Warehouse, Analytics, Business Intelligence",
        "cloud": "Azure",
        "technologies": "Azure Synapse, Power BI, ADLS Gen2, Azure Data Factory (ADF)",
        "solution_patterns": "cloud data warehouse, BI dashboards, data engineering",
    },
    "PG_DataWarehouse_CaseStudy.pdf": {
        "client": "P&G",
        "display_name": "P&G Supply Chain Analytics Platform",
        "industry": "FMCG / Consumer Goods",
        "services": "Data Warehouse, Supply Chain Analytics, Business Intelligence",
        "cloud": "AWS",
        "technologies": "AWS Glue, Amazon S3, Lake Formation, Tableau, MWAA (Airflow), Redshift, AWS Lambda",
        "solution_patterns": "data lake, cloud data warehouse, supply chain analytics, BI dashboards",
    },
    "Decathlon_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Decathlon",
        "display_name": "Decathlon GCP Data Warehouse",
        "industry": "Retail / Sports",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Pub/Sub, Google Cloud Storage (GCS), Looker, Dataplex",
        "solution_patterns": "cloud data warehouse, BI dashboards, data lake, retail analytics",
    },
    "IKEA_GCP_Tableau_CaseStudy.pdf": {
        "client": "IKEA",
        "display_name": "IKEA GCP Data Warehouse & Reporting",
        "industry": "Retail / Home & Furniture",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Data Fusion ETL, Google Cloud Storage (GCS), Tableau Server,Tableau Prep, Cloud Pub/Sub",
        "solution_patterns": "data lake, cloud data warehouse, BI dashboards, retail analytics, supply chain analytics",
    },
    "Starbucks_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Starbucks",
        "display_name": "Starbucks BI & Data Engineering on Azure",
        "industry": "Food & Beverage / QSR",
        "services": "Business Intelligence, Data Engineering, Cloud Analytics",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Databricks, Azure Synapse, Azure Data Lake Gen2, Power BI, Data Build Tool (DBT), Azure Event Hubs, Azure Purview",
        "solution_patterns": "data lake,cloud data warehouse, BI dashboards, data engineering, real-time analytics, data lake",
    },
    "Walmart_AWS_Tableau_CaseStudy.pdf": {
        "client": "Walmart",
        "display_name": "Walmart AWS Data Warehouse & Tableau BI",
        "industry": "Retail",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "AWS",
        "technologies": "Amazon S3, AWS Glue, Amazon Redshift, Tableau Server, Tableau Prep, AWS Lambda, Eventbridge,",
        "solution_patterns": "data lake, medallion architecture, cloud data warehouse, BI dashboards, retail analytics, supply chain analytics",
    },
    # ── BFSI (Banking, Financial Services, Insurance) ────────────────────────
    "HSBC_AzureDataPlatform_CaseStudy.pdf": {
        "client": "HSBC",
        "display_name": "HSBC Azure Data Platform",
        "industry": "BFSI / Banking / Financial Services",
        "services": "Data Lake Development, Data Analytics, Cloud Data Warehouse",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Azure Synapse, Power BI, Azure Data Lake Gen2, Azure Databricks, Azure Purview, Azure Key Vault",
        "solution_patterns": "cloud data warehouse, data lake, BI dashboards, financial analytics, real-time analytics",
    },
    "HDFC_Life_KnowledgeBot_CaseStudy.pdf": {
        "client": "HDFC Life",
        "display_name": "HDFC Life GenAI Knowledge Bot",
        "industry": "Insurance / BFSI",
        "services": "GenAI, RAG, Knowledge Management, Chatbot",
        "cloud": "AWS",
        "technologies": "Claude Sonnet 3.5, OpenAI, AWS Lambda, API Gateway, DynamoDB, Cognito, React, RAG",
        "solution_patterns": "NLP/LLM, RAG, knowledge management, chatbot, GenAI",
    },
    "JPMorgan_IndexGPT_CaseStudy.pdf": {
        "client": "JPMorgan Chase",
        "display_name": "JPMorgan IndexGPT — AI Thematic Investment",
        "industry": "Banking / Investment / BFSI",
        "services": "GenAI, Thematic Indexing, Investment Intelligence",
        "cloud": "AWS",
        "technologies": "Claude Sonnet 3, NLP, Agentic AI Pipeline, Amazoon Bedrock, AWS Lambda, Amazon EC2",
        "solution_patterns": "NLP/LLM, GenAI, agentic AI, financial analytics",
    },
    "MAX_Life_GCP_Migration_Case_Study.pdf": {
        "client": "MAX Life Insurance",
        "display_name": "MAX Life On-Prem to GCP Migration",
        "industry": "Insurance / BFSI",
        "services": "Cloud Migration, Data Engineering, Compliance",
        "cloud": "GCP",
        "technologies": "BigQuery, Cloud Composer, Datastream, Google Cloud Storage (GCS), Cloud SQL, Dataproc, Data Catalog, VPC-SC, DLP API, Airflow, Vertex AI",
        "solution_patterns": "cloud migration, data lake, medallion architecture, data governance, compliance, data engineering, PII Detection",
    },
    "Paytm_BFSI_Snowflake_QuickSight_CaseStudy.pdf": {
        "client": "Paytm",
        "display_name": "Paytm BFSI Snowflake & QuickSight Analytics",
        "industry": "Fintech / BFSI",
        "services": "Data Warehouse, BI, Financial Analytics",
        "cloud": "AWS",
        "technologies": "Snowflake, Amazon QuickSight, Kafka, Snowpipe, Data Build Tool (DBT), Airflow, Amazon S3",
        "solution_patterns": "cloud data warehouse, BI dashboards, real-time analytics, streaming data, financial analytics",
    },
    "NovaPay_AzureDataPlatform_CaseStudy.pdf": {
        "client": "NovaPay",
        "display_name": "NovaPay Azure Data Platform — Payments & Fraud",
        "industry": "Fintech / Digital Payments / BFSI",
        "services": "Data Platform, Fraud Detection, Compliance Analytics",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Databricks, ADLS Gen2, Azure Synapse, Power BI, Purview, Event Hubs",
        "solution_patterns": "data platform, fraud detection, real-time analytics, compliance, data governance, financial analytics",
    },
    "Zerodha_Azure_to_AWS_Migration_Case_Study.pdf": {
        "client": "Zerodha",
        "display_name": "Zerodha Azure to AWS Cloud Migration",
        "industry": "Fintech / Stock Trading / BFSI",
        "services": "Cloud Migration, Data Engineering, Platform Modernization",
        "cloud": "AWS",
        "technologies": "AWS EMR, EC2, S3, Amazon MSK (Kafka), MWAA (Airflow), RDS, Databricks on AWS",
        "solution_patterns": "cloud migration, data engineering, platform modernization, streaming data",
    },
    # ── Food & Beverage / QSR ────────────────────────────────────────────────
    "EatClub_DynamicPricing_CaseStudy.pdf": {
        "client": "EatClub Brands (Box8 & Mojo Pizza)",
        "display_name": "EatClub Dynamic Pricing & Demand Forecasting",
        "industry": "QSR / Cloud Kitchen",
        "services": "Dynamic Pricing, Demand Forecasting, ML/AI",
        "cloud": "AWS",
        "technologies": "ML Algorithms, Kafka Streaming, Ruby on Rails, AWS, PostreSQL, Redis, Redshift",
        "solution_patterns": "dynamic pricing, demand forecasting, ML/AI, real-time analytics, streaming data",
    },
    "PizzaHut_VoC_Sentiment_CaseStudy.pdf": {
        "client": "Pizza Hut",
        "display_name": "Pizza Hut Voice of Customer Sentiment Analytics",
        "industry": "QSR / Food & Beverage",
        "services": "Sentiment Analysis, NLP, Voice of Customer, Brand Intelligence",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Azure Data Lake, NLP Deep Learning, Power BI, Power Automate, Web Scraping",
        "solution_patterns": "sentiment analysis, NLP/LLM, customer analytics, real-time analytics, BI dashboards",
    },
    # ── Manufacturing & Automotive ───────────────────────────────────────────
    "Grasim_LLM_SalesInsights_CaseStudy.pdf": {
        "client": "Grasim (Aditya Birla Group)",
        "display_name": "Grasim LLM-Powered Sales Insights",
        "industry": "Manufacturing / Cement",
        "services": "GenAI, Natural Language Analytics, Sales Intelligence",
        "cloud": "GCP",
        "technologies": "Vertex AI, Anthropic Claude, BigQuery, Cloud Run, Cloud Functions, Python Plotly",
        "solution_patterns": "NLP/LLM, GenAI, self-service analytics, natural language query, sales analytics",
    },
    "Jaquar_MicrosoftFabric_CaseStudy.pdf": {
        "client": "Jaquar",
        "display_name": "Jaquar Microsoft Fabric Sales & Distribution Analytics",
        "industry": "Bathware / Manufacturing",
        "services": "Analytics, Data Platform, BI, Sales & Distribution",
        "cloud": "Azure",
        "technologies": "Microsoft Fabric, OneLake, Fabric Data Factory, Dataflows Gen2, Power BI, Purview",
        "solution_patterns": "data platform, BI dashboards, self-service analytics, data lake, sales analytics",
    },
    # ── Logistics ────────────────────────────────────────────────────────────
    "Fedex-Case Study.pdf": {
        "client": "FedEx",
        "display_name": "FedEx Azure to AWS Data Migration",
        "industry": "Logistics / Supply Chain",
        "services": "Cloud Migration, Data Engineering, Cost Optimization",
        "cloud": "AWS",
        "technologies": "AWS Databricks, AWS DataSync, Amazon EMR, Amazon S3, Cloudwatch",
        "solution_patterns": "cloud migration, data engineering, cost optimization, data validation",
    },
    # ── Retail / Sports (Cloud Migration) ────────────────────────────────────
    "Nike_Azure_to_AWS_Migration_Case_Study_Final.pdf": {
        "client": "Nike",
        "display_name": "Nike Azure to AWS Enterprise Cloud Migration",
        "industry": "Retail / Sports",
        "services": "Cloud Migration, Data Engineering, Platform Modernization",
        "cloud": "AWS",
        "technologies": "AWS Databricks, Amazon S3, Amazon MSK (Kafka), MWAA (Airflow), RDS, EKS",
        "solution_patterns": "cloud migration, platform modernization, data engineering, containerization",
    },
    # ── Cross-Industry (AI / Call Analytics) ─────────────────────────────────
    "CallAuditSystem_CaseStudy.pdf": {
        "client": "BFSI Client (Insurance & Banking)",
        "display_name": "AI-Powered Call Audit System",
        "industry": "Insurance / Banking / BFSI",
        "services": "AI Call Auditing, Fraud Detection, Sentiment Analysis, Agent Performance",
        "cloud": "AWS",
        "technologies": "AWS Transcribe, AWS Bedrock LLM, S3, SQS, Lambda, RDS, QuickSight, CloudWatch",
        "solution_patterns": "NLP/LLM, GenAI, fraud detection, sentiment analysis, real-time analytics, call analytics",
    },
}

_DEFAULTS = {
    "client": "",
    "display_name": "",
    "industry": "",
    "services": "",
    "cloud": "",
    "technologies": "",
    "solution_patterns": "",
}


def get_doc_metadata(filename: str) -> dict:
    """Return metadata for a document filename. Falls back to defaults for unknown files."""
    meta = {**_DEFAULTS, **_DOC_METADATA.get(filename, {})}
    if not meta["display_name"]:
        meta["display_name"] = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    return meta


def get_filename_by_display_name(display_name: str) -> str | None:
    """Reverse lookup: display name → original filename."""
    for filename, meta in _DOC_METADATA.items():
        if meta.get("display_name") == display_name:
            return filename
    return None
