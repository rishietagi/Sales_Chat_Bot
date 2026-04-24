# schema_registry.py
"""Canonical schema dictionary — single source of truth for column definitions for Himani Best Choice."""

SCHEMA_DICT = {
    "customer_code": "Unique code for the dealer/customer.",
    "dealer_name": "Full name of the dealer.",
    "city_town": "City or town of the dealer.",
    "region_descr": "Region description for the dealer.",
    "bdo": "Business Development Officer assigned to the dealer.",
    "contract_no": "Unique identifier for the pending sauda / contract.",
    "contract_valid_from": "Start date of the contract.",
    "contract_valid_to": "Expiry date of the contract.",
    "active_contract_flag": "Boolean flag indicating if the contract is currently active.",
    "contract_qty": "Total quantity booked in the contract.",
    "despatch_qty_sauda": "Quantity already dispatched against the contract.",
    "pending_qty": "Remaining quantity to be dispatched.",
    "pending_qty_mt": "Pending quantity in Metric Tons.",
    "basic_rate": "The basic rate agreed in the contract.",
    "oil_type": "The type of oil (e.g., Sunflower, Mustard).",
    "material_desc": "Description of the material/product in the contract.",
    "delivery_date": "Scheduled delivery date for open DO.",
    "delivery_today_flag": "Boolean flag indicating if delivery is scheduled for today.",
    "order_quantity_item": "Quantity in the open delivery order.",
    "material_description_od": "Description of the material in the open DO.",
    "overall_status_description": "Current status of the delivery order.",
    "sauda_priority": "Priority assigned to the sauda/contract.",
}

# Mapping of business terms to column names
COLUMN_MAPPING = {
    "dealer": "dealer_name",
    "customer": "dealer_name",
    "contract": "contract_no",
    "sauda": "contract_no",
    "product": "material_desc",
    "material": "material_desc",
    "pending_quantity": "pending_qty",
    "dispatched_quantity": "despatch_qty_sauda",
    "rate": "basic_rate",
    "oil": "oil_type",
    "expiry": "contract_valid_to",
}

# Action labels and types
ACTION_TYPES = {
    "PUSH_DISPATCH": "Call to push dispatch",
    "INFORM_DELIVERY": "Inform delivery today",
    "NUDGE_NEW_SAUDA": "Nudge for new sauda",
    "CHECK_EXPIRY": "Check contract expiry",
    "PRICING_GUIDANCE": "Provide pricing guidance",
}

PRIORITIES = ["High", "Medium", "Low"]
