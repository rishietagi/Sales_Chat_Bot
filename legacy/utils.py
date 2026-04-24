import pandas as pd
import numpy as np
import re
import html
import logging

logger = logging.getLogger(__name__)


def safe_percentage(numerator: float, denominator: float) -> float:
    """Safely calculates percentage without division by zero."""
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def normalize_text(text) -> str:
    """Normalizes text by stripping whitespace and converting to uppercase."""
    if pd.isna(text):
        return ""
    return str(text).strip().upper()


def parse_date(date_series: pd.Series) -> pd.Series:
    """Parses date column safely via pandas."""
    return pd.to_datetime(date_series, errors="coerce")


def format_currency(value: float) -> str:
    """Formats float value as currency."""
    if pd.isna(value):
        return "–"
    return f"${value:,.2f}"


def sanitise_user_input(text: str) -> str:
    """Strips HTML / script tags and escapes dangerous characters
    before the string is sent to the LLM or used in rendering."""
    if not text:
        return ""
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Escape remaining HTML entities
    cleaned = html.escape(cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_number_from_query(query: str, default: int = 15) -> int:
    """Extracts the first integer from a query string.
    Used to pull thresholds like '30' from 'last 30 days'."""
    match = re.search(r"\b(\d{1,3})\b", query)
    if match:
        return int(match.group(1))
    return default
