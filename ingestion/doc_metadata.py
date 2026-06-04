"""
Metadata for documents in docs/.
Add an entry here whenever a new document is added.

ChromaDB metadata values must be scalars (str, int, float, bool).
Lists are stored as comma-separated strings.
"""

_DOC_METADATA = {
    "CocaCola_DemandForecasting_CaseStudy.pdf": {
        "client": "Coca-Cola",
        "display_name": "Coca-Cola Demand Forecasting",
        "industry": "FMCG / Beverage",
        "services": "Demand Forecasting, AI/ML, Analytics",
        "cloud": "AWS",
        "technologies": "Amazon Forecast, SageMaker, S3",
    },
    "Nestle_DataWarehouse_CaseStudy.pdf": {
        "client": "Nestle",
        "display_name": "Nestle Global Data Warehouse",
        "industry": "FMCG / Food & Beverage",
        "services": "Data Warehouse, Analytics, Business Intelligence",
        "cloud": "Azure",
        "technologies": "Azure Synapse, Microsoft Fabric, Power BI",
    },
    "PG_DataWarehouse_CaseStudy.pdf": {
        "client": "P&G",
        "display_name": "P&G Trade Analytics Platform",
        "industry": "FMCG / Consumer Goods",
        "services": "Data Warehouse, Trade Analytics, Supply Chain",
        "cloud": "AWS",
        "technologies": "AWS Glue, S3, Lake Formation, Tableau",
    },
    "Cipla_BI_DataEngineering_CaseStudy.pdf": {
        "client": "Cipla",
        "display_name": "Cipla BI & Data Engineering",
        "industry": "Pharmaceuticals",
        "services": "Business Intelligence, Data Engineering, Analytics",
        "cloud": "Unknown",
        "technologies": "Power BI, SQL, ETL Pipelines",
    },
    "HSBC_AzureDataPlatform_CaseStudy.pdf": {
        "client": "HSBC",
        "display_name": "HSBC Azure Data Platform",
        "industry": "Banking / Financial Services",
        "services": "Data Platform, Cloud Migration, Analytics",
        "cloud": "Azure",
        "technologies": "Azure Data Factory, Azure Synapse, Power BI",
    },
    "Jaguar_MicrosoftFabric_CaseStudy.pdf": {
        "client": "Jaguar Land Rover",
        "display_name": "Jaguar Microsoft Fabric Analytics",
        "industry": "Automotive",
        "services": "Analytics, Data Platform, BI",
        "cloud": "Azure",
        "technologies": "Microsoft Fabric, Power BI, Azure",
    },
    "Philips_Healthcare_PredictiveMaintenance_POC.pdf": {
        "client": "Philips",
        "display_name": "Philips Healthcare Predictive Maintenance POC",
        "industry": "Healthcare / Medical Devices",
        "services": "Predictive Maintenance, IoT Analytics, AI/ML",
        "cloud": "Unknown",
        "technologies": "Python, Machine Learning, IoT",
    },
    "Siemens_Healthineers_CaseStudy.pdf": {
        "client": "Siemens Healthineers",
        "display_name": "Siemens Healthineers Data Analytics",
        "industry": "Healthcare / Medical Technology",
        "services": "Data Analytics, Business Intelligence, Reporting",
        "cloud": "Unknown",
        "technologies": "Power BI, SQL, Data Warehouse",
    },
    "SunPharma_GCP_DE_ReactNode_CaseStudy.pdf": {
        "client": "Sun Pharma",
        "display_name": "Sun Pharma GCP Data Engineering",
        "industry": "Pharmaceuticals",
        "services": "Data Engineering, Web Development, Cloud",
        "cloud": "GCP",
        "technologies": "GCP, BigQuery, React, Node.js, Cloud Dataflow",
    },
    "Ganit_Corporate_Profile_RAG_Optimized.pdf": {
        "client": "Ganit",
        "display_name": "Ganit Corporate Profile",
        "industry": "Data & Analytics Consulting",
        "services": "Data Engineering, Business Intelligence, AI/ML, Cloud Analytics, Data Governance, Pre-sales",
        "cloud": "AWS, Azure, GCP",
        "technologies": "Azure Synapse, Power BI, Databricks, Snowflake, AWS Glue, BigQuery, Python, dbt",
    },
}

_DEFAULTS = {
    "client": "Unknown",
    "display_name": "",
    "industry": "Unknown",
    "services": "",
    "cloud": "Unknown",
    "technologies": "",
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
