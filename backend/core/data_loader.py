import logging
import pandas as pd
from .schema_registry import SCHEMA_DICT

logger = logging.getLogger(__name__)

class DataLoader:
    """Loads, validates, and cleans the Himani Best Choice flat joined dataset."""

    def __init__(self, file_path_or_buffer):
        self.source = file_path_or_buffer

    def load_and_clean(self) -> pd.DataFrame:
        """Loads Excel with only essential columns to save memory."""
        essential_cols = [
            'bdo', 'dealer_name', 'customer_code', 'city_town', 'region_descr',
            'contract_no', 'contract_valid_to', 'active_contract_flag', 
            'contract_qty', 'despatch_qty_sauda', 'pending_qty', 'basic_rate', 
            'oil_type', 'material_desc', 'sales_document', 'delivery_date', 
            'delivery_today_flag', 'material_description_od', 'overall_status_description',
            'contract_value_est', 'dispatch_value_est', 'pending_value_est',
            'days_to_contract_end', 'aging_by_days'
        ]
        try:
            # Use usecols to only load what we need
            df = pd.read_excel(self.source, usecols=lambda c: c in essential_cols)
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            raise ValueError(f"Error loading file: {e}")

        # --- Column names ------------------------------------------------
        # We keep the column names as they are in the flat file, but strip spaces
        df.columns = [str(c).strip() for c in df.columns]

        # --- Date parsing ------------------------------------------------
        date_cols = [
            'contract_valid_from', 'contract_valid_to', 
            'sauda_date', 'creation_date_ps', 
            'created_on_od', 'document_date', 'delivery_date', 
            'goods_issue_date', 'material_availability_date'
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # --- Numeric coercion --------------------------------------------
        numeric_cols = [
            'contract_qty', 'despatch_qty_sauda', 'pending_qty', 
            'pending_qty_mt', 'basic_rate', 'order_quantity_item'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # --- String safety -----------------------------------------------
        string_cols = ['dealer_name', 'bdo', 'material_desc', 'oil_type', 'material_description_od']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna("Unknown").replace("nan", "Unknown")

        return df
