# Dealer Operations Assistant Knowledge Base

## 1. Data Source Overview
**Workbook Name:** `Emami_Direct_Dealer_Sauda_Data - Dummy Data.xlsx`

### Sheet 1: Active Dealer Master
- **Dealer Code**: Unique dealer identifier.
- **Dealer Name**: Name of the dealer/retailer.
- **State**: Geographic state.
- **City**: Geographic city.
- **Credit Days**: Allowed credit period.
- **Active Status**: Current status (Active/Inactive).

### Sheet 2: 1Y Sauda Sales Data
- **Dealer Code**: Foreign key to Dealer Master.
- **SKU**: Product identifier.
- **Sauda Order Date**: Date of order.
- **Order Quantity (Cases)**: Quantity ordered.
- **Agreed Rate (INR)**: Price per unit.
- **Order Value (INR)**: Total order value.

### Sheet 3: Open Orders
- **Dealer Code**: Foreign key to Dealer Master.
- **SKU**: Product identifier.
- **Order Quantity (Cases)**: Quantity ordered.
- **Dispatched Quantity**: Quantity already sent.
- **Order Status**: Status (Expected: 'Open').

### Sheet 4: Pending Payments
- **Dealer Code**: Foreign key to Dealer Master.
- **Invoice Date**: Date of billing.
- **Amount Collected (INR)**: Paid amount.
- **Outstanding Amount (INR)**: Remaining balance.
- **Payment Status**: Status (Expected: 'Pending').

## 2. Join Logic
- **Primary Key**: `Dealer Code`.
- **Base Table**: `1Y Sauda Sales Data` aggregated at the dealer level.
- **Enrichment**:
    - Left join `Active Dealer Master` for attributes.
    - Left join aggregated `Open Orders` (sum of value/count).
    - Left join aggregated `Pending Payments` (sum of outstanding/count).

## 3. Core Derived Metrics
| Metric | Definition |
| :--- | :--- |
| `last_order_date` | Max of `Sauda Order Date` |
| `days_since_last_order` | Current Date - `last_order_date` |
| `order_frequency` | Total order count / Active span (or per month) |
| `total_order_value` | Sum of `Order Value (INR)` from Sales |
| `open_order_value` | Sum of `Order Value (INR)` from Open Orders |
| `dispatch_ratio` | `Dispatched Quantity` / `Order Quantity` |
| `outstanding_amount` | Sum of `Outstanding Amount (INR)` |
| `collection_ratio` | `Amount Collected` / (`Amount Collected` + `Outstanding Amount`) |

## 4. Next-Best-Action Rules
- **Reactivation Candidate**: `days_since_last_order` > 15
- **Dormant (High Priority)**: `days_since_last_order` > 30
- **Key Account**: Top 20% by `total_order_value` AND high frequency.
- **Open Order Follow-up**: `open_order_value` > 0.
- **Fulfillment Gap**: `dispatch_ratio` < 0.8.
- **Collections Follow-up**: `outstanding_amount` > threshold.
- **Slowing Down**: Recent 30d revenue < Previous 30d revenue by > 20%.

## 5. Supported Queries
- "Which dealers should I call this week?"
- "Show me high-value dealers in [City/State]."
- "List all open orders with low fulfillment."
- "Which SKUs are performing best in [State]?"
- "Who are my top risky debtors?"
