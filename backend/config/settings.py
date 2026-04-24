import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME = "Dealer Operations Assistant"
    API_V1_STR = "/api"
    

    LLM_MODEL = "llama-3.1-8b-instant"
    
    DATA_PATH = os.path.join("data", "emami_flat_joined_dataset.xlsx")
    
    # Business Logic Thresholds
    DORMANT_DAYS = 30
    REACTIVATION_DAYS = 15
    HIGH_VALUE_QUANTILE = 0.8
    COLLECTIONS_THRESHOLD = 50000

settings = Settings()
