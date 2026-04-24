# Dealer Operations Assistant Knowledge Base

## 1. Data Source Overview
**Dataset:** `emami_flat_joined_dataset.xlsx` (Centralized Flat Dataset)

### Key Columns
- **Dealer Info**: `dealer_name`, `customer_code`, `city_town`, `region_descr`, `bdo`.
- **Contracts (Sauda)**: `contract_no`, `contract_valid_to`, `active_contract_flag`, `contract_qty`, `pending_qty`, `basic_rate`, `oil_type`, `material_desc`.
- **Open Deliveries (DO)**: `sales_document`, `delivery_date`, `delivery_today_flag`, `material_description_od`, `overall_status_description`.
- **Estimated Values**: `contract_value_est`, `dispatch_value_est`, `pending_value_est`.

## 2. Analytical Logic
The system uses a deterministic approach to calculate metrics before passing them to the AI.

### Business Rules
- **Active Dealer**: A dealer is considered **Active** if they have at least one non-Unknown `contract_no` OR one non-Unknown `sales_document`.
- **Dormant Dealer**: A dealer is **Dormant** if they exist in the master file but have zero active contracts and zero open delivery orders.
- **Contract Expiry**: "Expiring Soon" is defined as `days_to_contract_end` ≤ 7 days.
- **Aging**: Calculated via the `aging_by_days` column for active contracts with pending quantity.

### Next-Best-Action (NBA) Priorities
1. **Critical (P1)**: Contracts expiring in ≤ 3 days with pending quantity.
2. **High (P2)**: Materials arriving today (inform dealer).
3. **High (P3)**: Contracts expiring in 4-7 days with pending quantity.
4. **Medium (P4)**: Aging active contracts with high pending quantity.
5. **Medium (P5)**: Dormant dealers (nudge for new business).

## 3. Architecture & Methodology
For detailed architecture, workflow, and tech stack information, refer to:
- [Project Documentation](file:///c:/Users/rishi/Desktop/AI%20chatbot%20for%20sales/docs/project_doc.md)
- [Tech Stack Overview](file:///c:/Users/rishi/Desktop/AI%20chatbot%20for%20sales/TECH_STACK.md)

## 4. Supported Intent Families
- **contract**: Sauda status, expiry, aging, pending quantity.
- **dispatch**: Open deliveries, items arriving today, scheduled dates.
- **new_business**: Nudging dormant or inactive dealers.
- **collection**: Booked vs. Dispatched revenue analysis (pending payments).
- **pricing**: Guidance on basic rates by oil type (Mean/Median/Min/Max), new contract negotiation ranges, and outlier pricing detection.
- **daily_actions**: Ranked top 5 prioritized tasks for the BDO.
