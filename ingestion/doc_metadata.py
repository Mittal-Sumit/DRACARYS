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
