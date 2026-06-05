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
        "industry": "Healthcare / Diagnostics",
        "services": "Data Engineering, Business Intelligence, Self-Serve Analytics",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Composer, Pub/Sub, GCS, Dataproc, Vertex AI, Cloud Run, Looker, Power BI, React.js, Node.js",
        "solution_patterns": "cloud data warehouse, BI dashboards, self-service analytics, data engineering, data lake",
    },
    "Cipla_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Cipla",
        "display_name": "Cipla BI & Data Engineering",
        "industry": "Pharmaceuticals",
        "services": "Business Intelligence, Data Engineering, Analytics",
        "cloud": "Unknown",
        "technologies": "Power BI, SQL, ETL Pipelines",
        "solution_patterns": "BI dashboards, ETL pipelines, data engineering",
    },
    "SunPharma_GCP_DE_ReactNode_CaseStudy.pdf": {
        "client": "Sun Pharma",
        "display_name": "Sun Pharma GCP Data Engineering",
        "industry": "Pharmaceuticals",
        "services": "Data Engineering, Web Development, Cloud",
        "cloud": "GCP",
        "technologies": "GCP, BigQuery, React, Node.js, Cloud Dataflow",
        "solution_patterns": "data engineering, cloud data warehouse, web application",
    },
    "Philips_Healthcare_PredictiveMaintenance_POC.pdf": {
        "client": "Philips",
        "display_name": "Philips Healthcare Predictive Maintenance POC",
        "industry": "Healthcare / Medical Devices",
        "services": "Predictive Maintenance, IoT Analytics, AI/ML",
        "cloud": "Unknown",
        "technologies": "Python, Machine Learning, IoT",
        "solution_patterns": "predictive maintenance, IoT analytics, ML/AI",
    },
    "Siemens_Healthineers_CaseStudy.pdf": {
        "client": "Siemens Healthineers",
        "display_name": "Siemens Healthineers Data Analytics",
        "industry": "Healthcare / Medical Technology",
        "services": "Data Analytics, Business Intelligence, Reporting",
        "cloud": "Unknown",
        "technologies": "Power BI, SQL, Data Warehouse",
        "solution_patterns": "BI dashboards, data analytics, reporting",
    },
    # ── FMCG & Retail ────────────────────────────────────────────────────────
    "CocaCola_DemandForecasting_CaseStudy.pdf": {
        "client": "Coca-Cola",
        "display_name": "Coca-Cola Demand Forecasting",
        "industry": "FMCG / Beverage",
        "services": "Demand Forecasting, AI/ML, Analytics",
        "cloud": "AWS",
        "technologies": "Amazon Forecast, SageMaker, S3",
        "solution_patterns": "demand forecasting, ML/AI, predictive analytics",
    },
    "Nestle_DataWarehouse_CaseStudy.pdf": {
        "client": "Nestle",
        "display_name": "Nestle Global Data Warehouse",
        "industry": "FMCG / Food & Beverage",
        "services": "Data Warehouse, Analytics, Business Intelligence",
        "cloud": "Azure",
        "technologies": "Azure Synapse, Microsoft Fabric, Power BI",
        "solution_patterns": "cloud data warehouse, BI dashboards, data engineering",
    },
    "PG_DataWarehouse_CaseStudy.pdf": {
        "client": "P&G",
        "display_name": "P&G Trade Analytics Platform",
        "industry": "FMCG / Consumer Goods",
        "services": "Data Warehouse, Trade Analytics, Supply Chain",
        "cloud": "AWS",
        "technologies": "AWS Glue, S3, Lake Formation, Tableau",
        "solution_patterns": "cloud data warehouse, supply chain analytics, BI dashboards, trade analytics",
    },
    "Decathlon_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Decathlon",
        "display_name": "Decathlon GCP Data Warehouse & Looker BI",
        "industry": "Retail / Sports",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Pub/Sub, GCS, Looker, Dataplex",
        "solution_patterns": "cloud data warehouse, BI dashboards, self-service analytics, data lake, retail analytics",
    },
    "IKEA_GCP_Tableau_CaseStudy.pdf": {
        "client": "IKEA",
        "display_name": "IKEA GCP Data Warehouse & Tableau BI",
        "industry": "Retail / Home & Furniture",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "GCP",
        "technologies": "BigQuery, Dataflow, Cloud Data Fusion, GCS, Tableau Server",
        "solution_patterns": "cloud data warehouse, BI dashboards, self-service analytics, retail analytics, supply chain analytics",
    },
    "Starbucks_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Starbucks",
        "display_name": "Starbucks BI & Data Engineering on Azure",
        "industry": "F&B / Retail / QSR",
        "services": "Business Intelligence, Data Engineering, Cloud Analytics",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Databricks, Azure Synapse, Azure Data Lake Gen2, Power BI, dbt, Azure Event Hubs",
        "solution_patterns": "cloud data warehouse, BI dashboards, data engineering, real-time analytics, data lake",
    },
    "Walmart_AWS_Tableau_CaseStudy.pdf": {
        "client": "Walmart",
        "display_name": "Walmart AWS Data Warehouse & Tableau BI",
        "industry": "Retail / Omnichannel",
        "services": "Data Engineering, Business Intelligence, Cloud Data Warehouse",
        "cloud": "AWS",
        "technologies": "Amazon S3, AWS Glue, Amazon Redshift, Tableau Server",
        "solution_patterns": "cloud data warehouse, BI dashboards, self-service analytics, retail analytics, supply chain analytics",
    },
    # ── BFSI (Banking, Financial Services, Insurance) ────────────────────────
    "HSBC_AzureDataPlatform_CaseStudy.pdf": {
        "client": "HSBC",
        "display_name": "HSBC Azure Data Platform",
        "industry": "Banking / Financial Services",
        "services": "Data Platform, Cloud Migration, Analytics",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Azure Synapse, Power BI",
        "solution_patterns": "cloud data warehouse, data platform, BI dashboards, financial analytics",
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
        "cloud": "Unknown",
        "technologies": "GPT-4, OpenAI, NLP, Agentic AI Pipeline",
        "solution_patterns": "NLP/LLM, GenAI, agentic AI, financial analytics",
    },
    "MAX_Life_GCP_Migration_Case_Study.pdf": {
        "client": "MAX Life Insurance",
        "display_name": "MAX Life On-Prem to GCP Migration",
        "industry": "Insurance / BFSI",
        "services": "Cloud Migration, Data Engineering, Compliance",
        "cloud": "GCP",
        "technologies": "BigQuery, Cloud Composer, Datastream, GCS, Cloud SQL, Dataproc, Data Catalog, VPC-SC, DLP API",
        "solution_patterns": "cloud migration, data lake, data governance, compliance, data engineering",
    },
    "Paytm_BFSI_Snowflake_QuickSight_CaseStudy.pdf": {
        "client": "Paytm",
        "display_name": "Paytm BFSI Snowflake & QuickSight Analytics",
        "industry": "Fintech / BFSI",
        "services": "Data Warehouse, BI, Financial Analytics",
        "cloud": "AWS",
        "technologies": "Snowflake, Amazon QuickSight, Kafka, Snowpipe, dbt, Airflow, S3",
        "solution_patterns": "cloud data warehouse, BI dashboards, real-time analytics, streaming data, financial analytics",
    },
    "NovaPay_AzureDataPlatform_CaseStudy.pdf": {
        "client": "NovaPay",
        "display_name": "NovaPay Azure Data Platform — Payments & Fraud",
        "industry": "Fintech / Digital Payments",
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
        "industry": "Food Tech / Cloud Kitchen",
        "services": "Dynamic Pricing, Demand Forecasting, ML/AI",
        "cloud": "AWS",
        "technologies": "ML Algorithms, Kafka Streaming, Ruby on Rails, AWS",
        "solution_patterns": "dynamic pricing, demand forecasting, ML/AI, real-time analytics, streaming data",
    },
    "PizzaHut_VoC_Sentiment_CaseStudy.pdf": {
        "client": "Pizza Hut",
        "display_name": "Pizza Hut Voice of Customer Sentiment Analytics",
        "industry": "QSR / F&B",
        "services": "Sentiment Analysis, NLP, Voice of Customer, Brand Intelligence",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Azure Data Lake, NLP Deep Learning, Power BI, Web Scraping",
        "solution_patterns": "sentiment analysis, NLP/LLM, customer analytics, real-time analytics, BI dashboards",
    },
    # ── Manufacturing & Automotive ───────────────────────────────────────────
    "Grasim_LLM_SalesInsights_CaseStudy.pdf": {
        "client": "Grasim (Aditya Birla Group)",
        "display_name": "Grasim LLM-Powered Sales Insights",
        "industry": "Manufacturing / Textiles",
        "services": "GenAI, Natural Language Analytics, Sales Intelligence",
        "cloud": "GCP",
        "technologies": "Vertex AI, Anthropic Claude, BigQuery, Cloud Run, Cloud Functions, Python Plotly",
        "solution_patterns": "NLP/LLM, GenAI, self-service analytics, natural language query, sales analytics",
    },
    "Jaquar_MicrosoftFabric_CaseStudy.pdf": {
        "client": "Jaquar",
        "display_name": "Jaquar Microsoft Fabric Sales & Distribution Analytics",
        "industry": "Automotive / Manufacturing",
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
        "technologies": "AWS Databricks, AWS DataSync, EMR, S3",
        "solution_patterns": "cloud migration, data engineering, cost optimization, data validation",
    },
    # ── Retail / Sports (Cloud Migration) ────────────────────────────────────
    "Nike_Azure_to_AWS_Migration_Case_Study_Final.pdf": {
        "client": "Nike",
        "display_name": "Nike Azure to AWS Enterprise Cloud Migration",
        "industry": "Retail / Sports / E-Commerce",
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
    "client": "Unknown",
    "display_name": "",
    "industry": "Unknown",
    "services": "",
    "cloud": "Unknown",
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
