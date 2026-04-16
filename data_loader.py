import logging
import pandas as pd
from schema_registry import SCHEMA_DICT
from utils import parse_date

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads, validates, and cleans the sales dataset."""

    def __init__(self, file_path_or_buffer):
        self.source = file_path_or_buffer

    def load_and_clean(self) -> pd.DataFrame:
        """Loads CSV/Excel, standardises columns, parses dates, cleans values."""
        # --- Load --------------------------------------------------------
        try:
            if isinstance(self.source, str) and self.source.endswith(".xlsx"):
                df = pd.read_excel(self.source)
            else:
                df = pd.read_csv(self.source, encoding="ISO-8859-1")
        except Exception as e:
            raise ValueError(f"Error loading file: {e}")

        # --- Column names ------------------------------------------------
        df.columns = [str(c).strip().upper() for c in df.columns]

        # --- Schema validation -------------------------------------------
        missing = [c for c in SCHEMA_DICT if c not in df.columns]
        if missing:
            logger.warning("Missing canonical columns: %s", missing)

        # --- Date parsing ------------------------------------------------
        if "ORDERDATE" in df.columns:
            df["ORDERDATE"] = parse_date(df["ORDERDATE"])

        # --- Text normalisation ------------------------------------------
        if "STATUS" in df.columns:
            df["STATUS"] = df["STATUS"].astype(str).str.title().str.strip()
        if "DEALSIZE" in df.columns:
            df["DEALSIZE"] = df["DEALSIZE"].astype(str).str.title().str.strip()

        # --- Numeric coercion --------------------------------------------
        for col in ("QUANTITYORDERED", "PRICEEACH", "SALES"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # --- String safety -----------------------------------------------
        if "CUSTOMERNAME" in df.columns:
            df["CUSTOMERNAME"] = df["CUSTOMERNAME"].fillna("Unknown Dealer")

        return df
