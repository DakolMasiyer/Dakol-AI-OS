from dataclasses import dataclass

@dataclass(frozen=True)
class AppCapability:
    name: str
    description: str

CAPABILITIES = {
    # SYNCMASTER_AI
    "metadata_analysis": AppCapability("metadata_analysis", "Analyze track metadata"),
    "catalog_search": AppCapability("catalog_search", "Search catalog"),
    "recommendation_generation": AppCapability("recommendation_generation", "Generate recommendations"),
    
    # LISTENING_FARM_AI
    "ingestion": AppCapability("ingestion", "Ingest music metadata"),
    "crawling": AppCapability("crawling", "Crawl trend data"),
    "trend_analysis": AppCapability("trend_analysis", "Analyze music trends"),
    "scoring": AppCapability("scoring", "Score tracks"),
    
    # MIDAS_AI
    "financial_workflows": AppCapability("financial_workflows", "Financial operations"),
    "transaction_analysis": AppCapability("transaction_analysis", "Transaction analysis"),
    "fraud_checks": AppCapability("fraud_checks", "Fraud checks"),
}
