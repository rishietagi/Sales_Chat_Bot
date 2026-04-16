import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME = "Dealer Operations Assistant"
    API_V1_STR = "/api"
    

    LLM_MODEL = "llama-3.1-8b-instant"
    
    DATA_PATH = "Emami_Direct_Dealer_Sauda_Data_Enriched_With_Zones.xlsx"
    
    # Business Logic Thresholds
    DORMANT_DAYS = 30
    REACTIVATION_DAYS = 15
    HIGH_VALUE_QUANTILE = 0.8
    COLLECTIONS_THRESHOLD = 50000

settings = Settings()
