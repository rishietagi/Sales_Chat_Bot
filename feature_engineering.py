import pandas as pd
import numpy as np
from schema_registry import STATUS_NON_FINAL


class FeatureEngineer:
    """Builds all derived metrics from the cleaned raw dataset."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    # ------------------------------------------------------------------ #
    # Territory                                                           #
    # ------------------------------------------------------------------ #
    def add_territory(self) -> pd.DataFrame:
        """Creates a virtual TERRITORY column from CITY / STATE / COUNTRY."""

        def _territory(row):
            parts = []
            for col in ("CITY", "STATE", "COUNTRY"):
                val = row.get(col, "")
                if pd.notna(val) and str(val).strip().lower() not in ("", "nan"):
                    parts.append(str(val).strip())
            return ", ".join(parts) if parts else "Unknown"

        self.df["TERRITORY"] = self.df.apply(_territory, axis=1)
        return self.df

    # ------------------------------------------------------------------ #
    # Dealer‑level metrics                                                #
    # ------------------------------------------------------------------ #
    def compute_dealer_metrics(self, current_date=None) -> pd.DataFrame:
        """Computes RFM, trends, deal-size mix, buying cycle, product
        diversity, non-final counts, and top product line per dealer."""

        if self.df.empty or "CUSTOMERNAME" not in self.df.columns:
            return pd.DataFrame()

        if current_date is None:
            current_date = self.df["ORDERDATE"].max()

        grp = self.df.groupby("CUSTOMERNAME")

        # --- Base aggregates ---------------------------------------------
        metrics = grp.agg(
            last_order_date=("ORDERDATE", "max"),
            order_count=("ORDERNUMBER", "nunique"),
            total_sales=("SALES", "sum"),
            avg_order_value=("SALES", "mean"),
            contact_first=("CONTACTFIRSTNAME", "first"),
            contact_last=("CONTACTLASTNAME", "first"),
            phone=("PHONE", "first"),
            city=("CITY", "first"),
            country=("COUNTRY", "first"),
        ).reset_index()

        # --- Recency -----------------------------------------------------
        metrics["days_since_last_order"] = (
            (current_date - metrics["last_order_date"]).dt.days
        )

        # --- Contact name ------------------------------------------------
        metrics["contact_name"] = (
            metrics["contact_first"].fillna("") + " " + metrics["contact_last"].fillna("")
        ).str.strip()

        # --- Non-final order count ---------------------------------------
        nf = self.df[self.df["STATUS"].isin(STATUS_NON_FINAL)]
        nf_counts = (
            nf.groupby("CUSTOMERNAME")["ORDERNUMBER"]
            .nunique()
            .reset_index(name="non_final_count")
        )
        metrics = metrics.merge(nf_counts, on="CUSTOMERNAME", how="left")
        metrics["non_final_count"] = metrics["non_final_count"].fillna(0).astype(int)

        # --- 90-day trend comparison -------------------------------------
        def _window_sales(start_days: int, end_days: int) -> pd.DataFrame:
            days = (current_date - self.df["ORDERDATE"]).dt.days
            mask = (days >= start_days) & (days < end_days)
            return (
                self.df.loc[mask]
                .groupby("CUSTOMERNAME")["SALES"]
                .sum()
                .reset_index()
            )

        recent = _window_sales(0, 90).rename(columns={"SALES": "recent_sales_90d"})
        prior = _window_sales(90, 180).rename(columns={"SALES": "past_sales_90d"})

        metrics = metrics.merge(recent, on="CUSTOMERNAME", how="left")
        metrics = metrics.merge(prior, on="CUSTOMERNAME", how="left")
        metrics["recent_sales_90d"] = metrics["recent_sales_90d"].fillna(0)
        metrics["past_sales_90d"] = metrics["past_sales_90d"].fillna(0)

        metrics["sales_change_pct"] = np.where(
            metrics["past_sales_90d"] > 0,
            ((metrics["recent_sales_90d"] - metrics["past_sales_90d"])
             / metrics["past_sales_90d"]) * 100.0,
            0.0,
        )

        # --- Deal-size mix -----------------------------------------------
        if "DEALSIZE" in self.df.columns:
            deal_pivot = (
                self.df.groupby(["CUSTOMERNAME", "DEALSIZE"])["ORDERNUMBER"]
                .nunique()
                .unstack(fill_value=0)
            )
            for size in ("Small", "Medium", "Large"):
                col = f"deals_{size.lower()}"
                deal_pivot[col] = deal_pivot.get(size, 0)
            deal_cols = [c for c in deal_pivot.columns if c.startswith("deals_")]
            metrics = metrics.merge(
                deal_pivot[deal_cols].reset_index(), on="CUSTOMERNAME", how="left"
            )
            for c in deal_cols:
                metrics[c] = metrics[c].fillna(0).astype(int)

        # --- Product diversity -------------------------------------------
        if "PRODUCTLINE" in self.df.columns:
            pdiv = (
                self.df.groupby("CUSTOMERNAME")["PRODUCTLINE"]
                .nunique()
                .reset_index(name="product_diversity")
            )
            metrics = metrics.merge(pdiv, on="CUSTOMERNAME", how="left")

            # Top product line
            fav = (
                self.df.groupby(["CUSTOMERNAME", "PRODUCTLINE"])["SALES"]
                .sum()
                .reset_index()
                .sort_values(["CUSTOMERNAME", "SALES"], ascending=[True, False])
                .drop_duplicates("CUSTOMERNAME")
                .rename(columns={"PRODUCTLINE": "top_product_line"})
                [["CUSTOMERNAME", "top_product_line"]]
            )
            metrics = metrics.merge(fav, on="CUSTOMERNAME", how="left")

            # Product loyalty % (share of top product line)
            top_sales = (
                self.df.groupby(["CUSTOMERNAME", "PRODUCTLINE"])["SALES"]
                .sum()
                .reset_index()
                .sort_values(["CUSTOMERNAME", "SALES"], ascending=[True, False])
                .drop_duplicates("CUSTOMERNAME")
                .rename(columns={"SALES": "top_pl_sales"})
                [["CUSTOMERNAME", "top_pl_sales"]]
            )
            metrics = metrics.merge(top_sales, on="CUSTOMERNAME", how="left")
            metrics["product_loyalty_pct"] = np.where(
                metrics["total_sales"] > 0,
                (metrics["top_pl_sales"] / metrics["total_sales"]) * 100.0,
                0.0,
            )

        # --- Buying cycle (median days between orders) -------------------
        order_dates = (
            self.df.groupby("CUSTOMERNAME")["ORDERDATE"]
            .apply(lambda s: s.sort_values().diff().dt.days.median())
            .reset_index(name="buying_cycle_days")
        )
        metrics = metrics.merge(order_dates, on="CUSTOMERNAME", how="left")

        return metrics

    # ------------------------------------------------------------------ #
    # Territory‑level metrics                                             #
    # ------------------------------------------------------------------ #
    def compute_territory_metrics(self, dealer_metrics: pd.DataFrame = None) -> pd.DataFrame:
        """Territory rollups including dormancy and deal-size breakdown."""

        if "TERRITORY" not in self.df.columns:
            self.add_territory()

        grp = self.df.groupby("TERRITORY")
        metrics = grp.agg(
            total_sales=("SALES", "sum"),
            order_count=("ORDERNUMBER", "nunique"),
            active_dealers=("CUSTOMERNAME", "nunique"),
        ).reset_index()

        # --- Dormant dealer count per territory --------------------------
        if dealer_metrics is not None and not dealer_metrics.empty:
            if "TERRITORY" not in self.df.columns:
                self.add_territory()
            # Map dealer → territory via first city/country occurrence
            dt_map = (
                self.df.drop_duplicates("CUSTOMERNAME")[["CUSTOMERNAME", "TERRITORY"]]
            )
            dm = dealer_metrics.merge(dt_map, on="CUSTOMERNAME", how="left")
            dormant = (
                dm[dm["days_since_last_order"] > 30]
                .groupby("TERRITORY")["CUSTOMERNAME"]
                .nunique()
                .reset_index(name="dormant_dealers")
            )
            metrics = metrics.merge(dormant, on="TERRITORY", how="left")
            metrics["dormant_dealers"] = metrics["dormant_dealers"].fillna(0).astype(int)

            # --- Non-final order count per territory ---------------------
            nf_terr = (
                dm[dm["non_final_count"] > 0]
                .groupby("TERRITORY")["non_final_count"]
                .sum()
                .reset_index(name="blocked_orders")
            )
            metrics = metrics.merge(nf_terr, on="TERRITORY", how="left")
            metrics["blocked_orders"] = metrics["blocked_orders"].fillna(0).astype(int)

        # --- Deal-size % per territory -----------------------------------
        if "DEALSIZE" in self.df.columns:
            deal_t = (
                self.df.groupby(["TERRITORY", "DEALSIZE"])["ORDERNUMBER"]
                .nunique()
                .unstack(fill_value=0)
            )
            total = deal_t.sum(axis=1)
            for size in ("Small", "Medium", "Large"):
                col = f"pct_{size.lower()}"
                deal_t[col] = np.where(total > 0, (deal_t.get(size, 0) / total) * 100, 0)
            pct_cols = [c for c in deal_t.columns if c.startswith("pct_")]
            metrics = metrics.merge(
                deal_t[pct_cols].reset_index(), on="TERRITORY", how="left"
            )

        return metrics

    # ------------------------------------------------------------------ #
    # Product‑level trend (QoQ)                                           #
    # ------------------------------------------------------------------ #
    def compute_product_trends(self) -> pd.DataFrame:
        """Sales per PRODUCTLINE per quarter — detects slowing product lines."""
        if "PRODUCTLINE" not in self.df.columns:
            return pd.DataFrame()
        return (
            self.df.groupby(["PRODUCTLINE", "YEAR_ID", "QTR_ID"])
            .agg(total_sales=("SALES", "sum"), order_count=("ORDERNUMBER", "nunique"))
            .reset_index()
            .sort_values(["PRODUCTLINE", "YEAR_ID", "QTR_ID"])
        )
