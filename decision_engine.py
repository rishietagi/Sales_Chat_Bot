import pandas as pd
import numpy as np
from schema_registry import DEFAULT_THRESHOLDS


class DecisionEngine:
    """Rules-based NBA (Next Best Action) labelling with priority scoring
    and human-readable reason strings."""

    def __init__(self, thresholds: dict | None = None):
        self.t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    # ------------------------------------------------------------------ #
    # Label assignment                                                    #
    # ------------------------------------------------------------------ #
    def _label_row(self, row: pd.Series) -> list[dict]:
        """Returns a list of {label, reason, priority} dicts for one dealer."""
        actions: list[dict] = []
        days = row.get("days_since_last_order", 0)
        change = row.get("sales_change_pct", 0)
        nf = row.get("non_final_count", 0)
        orders = row.get("order_count", 0)
        sales = row.get("total_sales", 0)
        loyalty = row.get("product_loyalty_pct", 0)
        cycle = row.get("buying_cycle_days", None)
        top_pl = row.get("top_product_line", "")
        deals_large = row.get("deals_large", 0)

        # --- Dormancy ----------------------------------------------------
        if days > self.t["dormant_days_critical"]:
            actions.append({
                "label": "Dormant – high priority",
                "reason": f"No orders in {int(days)} days (threshold: {self.t['dormant_days_critical']})",
                "priority": 9,
            })
        elif days > self.t["dormant_days_warning"]:
            actions.append({
                "label": "Reactivation candidate",
                "reason": f"No orders in {int(days)} days",
                "priority": 7,
            })

        # --- Slowing down ------------------------------------------------
        if change <= self.t["slowing_pct"]:
            actions.append({
                "label": "Slowing down",
                "reason": f"Sales dropped {abs(change):.0f}% vs prior 90 days",
                "priority": 8,
            })

        # --- Status follow-up --------------------------------------------
        if nf > 0:
            actions.append({
                "label": "Status follow-up",
                "reason": f"{int(nf)} order(s) stuck in non-final status",
                "priority": 8,
            })

        # --- Re-contact due (buying cycle) -------------------------------
        if (
            cycle is not None
            and not np.isnan(cycle)
            and cycle > 0
            and days > cycle * self.t["recontact_cycle_multiplier"]
        ):
            actions.append({
                "label": "Re-contact due",
                "reason": (
                    f"Avg buying cycle is {cycle:.0f} days "
                    f"but last order was {int(days)} days ago"
                ),
                "priority": 7,
            })

        # --- Key account -------------------------------------------------
        if (
            orders >= self.t["key_account_min_orders"]
            and sales > self.t["key_account_min_sales"]
        ):
            actions.append({
                "label": "Key account",
                "reason": f"{int(orders)} orders totalling ${sales:,.0f}",
                "priority": 5,
            })

        # --- High-value active -------------------------------------------
        if deals_large >= 2 and days < self.t["dormant_days_warning"]:
            actions.append({
                "label": "High-value active",
                "reason": f"{int(deals_large)} large deals and ordered {int(days)} days ago",
                "priority": 4,
            })

        # --- Product loyalty ---------------------------------------------
        if loyalty >= self.t["product_loyalty_pct"]:
            actions.append({
                "label": "Product loyalty",
                "reason": f"{loyalty:.0f}% of sales in {top_pl}",
                "priority": 3,
            })

        # --- Fallback ----------------------------------------------------
        if not actions:
            actions.append({
                "label": "Monitor",
                "reason": "No urgent signals detected",
                "priority": 1,
            })

        return actions

    # ------------------------------------------------------------------ #
    # Batch processing                                                    #
    # ------------------------------------------------------------------ #
    def process_dealers(self, dealer_df: pd.DataFrame) -> pd.DataFrame:
        """Adds action labels, reasons, and a numeric priority to each row."""
        if dealer_df.empty or "days_since_last_order" not in dealer_df.columns:
            return dealer_df

        result = dealer_df.copy()
        raw_labels = result.apply(self._label_row, axis=1)

        result["action_labels"] = raw_labels.apply(
            lambda lst: [d["label"] for d in lst]
        )
        result["recommended_actions"] = result["action_labels"].apply(
            lambda lst: ", ".join(lst)
        )
        result["action_reasons"] = raw_labels.apply(
            lambda lst: " | ".join(d["reason"] for d in lst)
        )
        result["priority_score"] = raw_labels.apply(
            lambda lst: max(d["priority"] for d in lst)
        )

        # Sort by priority descending so most urgent appear first
        result = result.sort_values("priority_score", ascending=False)
        return result
