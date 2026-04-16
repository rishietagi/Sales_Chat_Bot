# schema_registry.py
"""Canonical schema dictionary — single source of truth for column definitions."""

SCHEMA_DICT = {
    "ORDERNUMBER": "Unique ID of each order.",
    "QUANTITYORDERED": "Number of units ordered in the order.",
    "PRICEEACH": "Price of one unit.",
    "SALES": "Total sales value (profit from the order).",
    "ORDERDATE": "Date when the order was placed.",
    "STATUS": "Order status: Cancelled, Disputed, In Process, Resolved, On Hold, Shipped.",
    "QTR_ID": "Quarter of the year (1–4).",
    "MONTH_ID": "Month of the year (1–12).",
    "YEAR_ID": "Year the order was placed.",
    "PRODUCTLINE": "Product category (Classic Cars, Vintage Cars, Motorcycles, Planes, Ships, Trains, Trucks and Buses).",
    "PRODUCTCODE": "Unique code for the product type.",
    "CUSTOMERNAME": "Name of the retailer / dealer / account.",
    "PHONE": "Phone number of the dealer.",
    "CITY": "City of the dealer.",
    "STATE": "State of the dealer (may be blank for non-US).",
    "COUNTRY": "Country of the dealer.",
    "CONTACTLASTNAME": "Contact person last name.",
    "CONTACTFIRSTNAME": "Contact person first name.",
    "DEALSIZE": "Size of the deal: Small, Medium, or Large.",
}

STATUS_FINAL = {"Shipped", "Resolved"}
STATUS_NON_FINAL = {"In Process", "On Hold", "Cancelled", "Disputed"}

# Default thresholds (can be overridden from the sidebar)
DEFAULT_THRESHOLDS = {
    "dormant_days_warning": 15,
    "dormant_days_critical": 30,
    "slowing_pct": -20.0,
    "key_account_min_orders": 2,
    "key_account_min_sales": 30_000,
    "product_loyalty_pct": 70.0,
    "recontact_cycle_multiplier": 1.5,
}
