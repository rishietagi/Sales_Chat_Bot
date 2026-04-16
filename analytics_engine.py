import pandas as pd
import numpy as np

MAX_ROWS = 15


class AnalyticsEngine:
    """Deterministic pandas analytics — one method per intent family."""

    def __init__(
        self,
        raw_df: pd.DataFrame,
        dealer_metrics: pd.DataFrame,
        territory_metrics: pd.DataFrame,
    ):
        self.raw = raw_df
        self.dm = dealer_metrics
        self.tm = territory_metrics

    # ------------------------------------------------------------------ #
    # Public dispatcher                                                   #
    # ------------------------------------------------------------------ #
    def execute_query(self, intent: str, **kw) -> pd.DataFrame:
        dispatch = {
            "dealer_ranking":       self._dealer_ranking,
            "dormant_dealers":      self._dormant_dealers,
            "slowing_dealers":      self._slowing_dealers,
            "status_follow_up":     self._status_follow_up,
            "territory_performance": self._territory_performance,
            "product_analysis":     self._product_analysis,
            "time_trend":           self._time_trend,
            "contact_lookup":       self._contact_lookup,
        }
        fn = dispatch.get(intent, self._dealer_ranking)
        return fn(**kw).head(MAX_ROWS)

    # ------------------------------------------------------------------ #
    # Individual query functions                                          #
    # ------------------------------------------------------------------ #
    def _dealer_ranking(self, **_) -> pd.DataFrame:
        return self.dm.sort_values("total_sales", ascending=False)

    def _dormant_dealers(self, **kw) -> pd.DataFrame:
        threshold = kw.get("dormant_days", 15)
        df = self.dm[self.dm["days_since_last_order"] > threshold]
        return df.sort_values("days_since_last_order", ascending=False)

    def _slowing_dealers(self, **_) -> pd.DataFrame:
        df = self.dm[self.dm["sales_change_pct"] <= -20.0]
        return df.sort_values("sales_change_pct", ascending=True)

    def _status_follow_up(self, **_) -> pd.DataFrame:
        if "non_final_count" not in self.dm.columns:
            return pd.DataFrame()
        df = self.dm[self.dm["non_final_count"] > 0]
        return df.sort_values("non_final_count", ascending=False)

    def _territory_performance(self, **_) -> pd.DataFrame:
        return self.tm.sort_values("total_sales", ascending=False)

    def _product_analysis(self, **_) -> pd.DataFrame:
        if "PRODUCTLINE" not in self.raw.columns:
            return pd.DataFrame()
        return (
            self.raw.groupby("PRODUCTLINE")
            .agg(
                total_sales=("SALES", "sum"),
                order_count=("ORDERNUMBER", "nunique"),
                unique_dealers=("CUSTOMERNAME", "nunique"),
            )
            .reset_index()
            .sort_values("total_sales", ascending=False)
        )

    def _time_trend(self, **_) -> pd.DataFrame:
        needed = {"YEAR_ID", "QTR_ID", "MONTH_ID"}
        if not needed.issubset(self.raw.columns):
            return pd.DataFrame()
        ts = (
            self.raw.groupby(["YEAR_ID", "QTR_ID", "MONTH_ID"])
            .agg(total_sales=("SALES", "sum"), order_count=("ORDERNUMBER", "nunique"))
            .reset_index()
            .sort_values(["YEAR_ID", "QTR_ID", "MONTH_ID"])
        )
        # Add MoM delta
        ts["prev_sales"] = ts["total_sales"].shift(1)
        ts["mom_change_pct"] = np.where(
            ts["prev_sales"] > 0,
            ((ts["total_sales"] - ts["prev_sales"]) / ts["prev_sales"]) * 100,
            0,
        )
        return ts.tail(MAX_ROWS)

    def _contact_lookup(self, **kw) -> pd.DataFrame:
        """Returns dealer contact details, optionally filtered by name substring."""
        name = kw.get("dealer_name")
        cols = [
            "CUSTOMERNAME", "contact_name", "phone", "city", "country",
            "total_sales", "order_count", "days_since_last_order",
        ]
        available = [c for c in cols if c in self.dm.columns]
        df = self.dm[available].copy()

        if name:
            mask = df["CUSTOMERNAME"].str.contains(name, case=False, na=False)
            df = df[mask]

        return df.sort_values("total_sales", ascending=False)
