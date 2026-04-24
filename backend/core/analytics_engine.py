import pandas as pd
import logging
import json
from .feature_engineering import FeatureEngineer
from .decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Deterministic analytics for BDO queries - Himani Best Choice."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.fe = FeatureEngineer(df)
        self.de = DecisionEngine(df)

    def execute_query(self, intent_family: str, bdo_name: str, **kwargs) -> dict:
        """Executes a query based on intent family and returns structured data."""
        try:
            if intent_family == "contract":
                return self._handle_contracts(bdo_name, **kwargs)
            elif intent_family == "dispatch":
                return self._handle_dispatch(bdo_name, **kwargs)
            elif intent_family == "new_business":
                return self._handle_new_business(bdo_name, **kwargs)
            elif intent_family == "dormant":
                return self._handle_dormant(bdo_name)
            elif intent_family == "active_dealers":
                return self._handle_active_dealers(bdo_name)
            elif intent_family == "collection":
                return self._handle_collection(bdo_name)
            elif intent_family == "pricing":
                return self._handle_pricing(**kwargs)
            elif intent_family == "daily_actions":
                return self._handle_actions(bdo_name)
            else:
                return {"summary": self.fe.get_bdo_metrics(bdo_name)}
        except Exception as e:
            logger.error(f"Error in AnalyticsEngine execute_query: {e}")
            return {"error": str(e)}

    # ── Contract Queries ─────────────────────────────────────────────
    def _handle_contracts(self, bdo_name, **kwargs):
        contracts = self.fe.get_contract_data(bdo_name)
        subtype = kwargs.get("subtype", "all")
        
        if subtype == "expiring":
            # Contracts expiring within 7 days that are still active
            contracts = contracts[
                (contracts['days_to_contract_end'] <= 7) &
                (contracts['active_contract_flag'] == True) &
                (contracts['days_to_contract_end'] >= 0)
            ].sort_values('days_to_contract_end')
        elif subtype == "active":
            contracts = contracts[contracts['active_contract_flag'] == True]
        elif subtype == "high_pending":
            # Per-dealer pending qty breakdown
            contracts = contracts[contracts['pending_qty'] > 0].sort_values('pending_qty', ascending=False)
        elif subtype == "aging":
            # Contracts that have been active for a long time with pending qty
            contracts = contracts[
                (contracts['active_contract_flag'] == True) &
                (contracts['pending_qty'] > 0)
            ]
            if 'aging_by_days' in contracts.columns:
                contracts = contracts.sort_values('aging_by_days', ascending=False)
            else:
                contracts = contracts.sort_values('days_to_contract_end')
        
        # Select relevant columns for LLM context
        display_cols = ['dealer_name', 'contract_no', 'material_desc', 'oil_type',
                        'contract_qty', 'despatch_qty_sauda', 'pending_qty', 
                        'basic_rate', 'days_to_contract_end', 'active_contract_flag']
        available_cols = [c for c in display_cols if c in contracts.columns]
        
        result = json.loads(contracts[available_cols].head(15).to_json(orient='records', date_format='iso'))
        
        return {
            "data": result,
            "total_count": len(contracts),
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── Dispatch / Delivery Queries ──────────────────────────────────
    def _handle_dispatch(self, bdo_name, **kwargs):
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        subtype = kwargs.get("subtype", "all")
        
        if subtype == "today":
            dispatch = bdo_df[bdo_df['delivery_today_flag'] == 1]
        else:
            dispatch = bdo_df[bdo_df['sales_document'] != "Unknown"]
        
        # Select relevant columns
        display_cols = ['dealer_name', 'material_description_od', 'delivery_date',
                        'order_quantity_item', 'overall_status_description', 'sales_document']
        available_cols = [c for c in display_cols if c in dispatch.columns]
        
        result = json.loads(dispatch[available_cols].head(15).to_json(orient='records', date_format='iso'))
        
        return {
            "data": result,
            "total_count": len(dispatch),
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── New Business ─────────────────────────────────────────────────
    def _handle_new_business(self, bdo_name, **kwargs):
        inactive = self.fe.get_inactive_dealers(bdo_name)
        inactive_list = []
        for _, row in inactive.iterrows():
            inactive_list.append({
                "dealer_name": row.get('dealer_name', 'Unknown'),
                "customer_code": row.get('customer_code', ''),
                "city_town": row.get('city_town', ''),
                "region": row.get('region_descr', ''),
            })
        return {
            "data": inactive_list,
            "total_count": len(inactive_list),
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── Dormant Dealers ──────────────────────────────────────────────
    def _handle_dormant(self, bdo_name):
        """Dormant dealers: in master but have NO active contract AND NO open delivery order."""
        dormant = self.fe.get_inactive_dealers(bdo_name)
        dormant_list = []
        for _, row in dormant.iterrows():
            dormant_list.append({
                "dealer_name": row.get('dealer_name', 'Unknown'),
                "customer_code": row.get('customer_code', ''),
                "city_town": row.get('city_town', ''),
                "region": row.get('region_descr', ''),
            })
        return {
            "data": dormant_list,
            "total_dormant": len(dormant_list),
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── Active Dealers ───────────────────────────────────────────────
    def _handle_active_dealers(self, bdo_name):
        """Active dealers: have at least one active contract OR one open delivery order."""
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        active_codes = bdo_df[
            (bdo_df['contract_no'] != "Unknown") | (bdo_df['sales_document'] != "Unknown")
        ]['customer_code'].unique()
        active_df = bdo_df[bdo_df['customer_code'].isin(active_codes)].drop_duplicates('customer_code')
        
        active_list = []
        for _, row in active_df.iterrows():
            active_list.append({
                "dealer_name": row.get('dealer_name', 'Unknown'),
                "customer_code": row.get('customer_code', ''),
                "city_town": row.get('city_town', ''),
                "region": row.get('region_descr', ''),
            })
        return {
            "data": active_list,
            "total_active": len(active_list),
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── Collection / Pending Payments ────────────────────────────────
    def _handle_collection(self, bdo_name):
        """Collection metrics with per-dealer breakdown."""
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        sauda_df = bdo_df[bdo_df['contract_no'] != "Unknown"].drop_duplicates('contract_no')
        
        total_booked = sauda_df['contract_value_est'].sum() if 'contract_value_est' in sauda_df.columns else 0
        total_dispatched = sauda_df['dispatch_value_est'].sum() if 'dispatch_value_est' in sauda_df.columns else 0
        total_pending = sauda_df['pending_value_est'].sum() if 'pending_value_est' in sauda_df.columns else 0
        dispatched_pct = (total_dispatched / total_booked * 100) if total_booked > 0 else 0
        pending_pct = (total_pending / total_booked * 100) if total_booked > 0 else 0
        
        dealer_agg = sauda_df.groupby('dealer_name').agg(
            booked_value=('contract_value_est', 'sum'),
            dispatched_value=('dispatch_value_est', 'sum'),
            pending_value=('pending_value_est', 'sum'),
            contracts=('contract_no', 'count')
        ).reset_index()
        dealer_agg = dealer_agg[dealer_agg['pending_value'] > 0].sort_values('pending_value', ascending=False)
        
        dealer_list = []
        for _, row in dealer_agg.iterrows():
            pct = (row['pending_value'] / row['booked_value'] * 100) if row['booked_value'] > 0 else 0
            dealer_list.append({
                "dealer_name": row['dealer_name'],
                "booked_value": round(float(row['booked_value']), 2),
                "dispatched_value": round(float(row['dispatched_value']), 2),
                "pending_value": round(float(row['pending_value']), 2),
                "pending_pct": round(pct, 1),
                "contracts": int(row['contracts']),
            })
        
        return {
            "data": dealer_list,
            "totals": {
                "total_booked_value": round(float(total_booked), 2),
                "total_dispatched_value": round(float(total_dispatched), 2),
                "total_pending_value": round(float(total_pending), 2),
                "dispatched_pct": round(dispatched_pct, 1),
                "pending_pct": round(pending_pct, 1),
                "dealers_with_pending": len(dealer_list),
            },
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }

    # ── Pricing ──────────────────────────────────────────────────────
    def _handle_pricing(self, **kwargs):
        stats = self.fe.get_pricing_stats()
        if stats.empty:
            return {"data": [], "message": "No pricing data available."}
        
        oil_type = kwargs.get("oil_type")
        if oil_type:
            stats = stats[stats['oil_type'].str.contains(oil_type, case=False, na=False)]
        
        pricing_data = []
        outlier_oils = []
        for _, row in stats.iterrows():
            entry = {
                "oil_type": row['oil_type'],
                "contract_count": int(row['contract_count']),
                "mean_rate": float(row['mean_rate']),
                "median_rate": float(row['median_rate']),
                "min_rate": float(row['min_rate']),
                "max_rate": float(row['max_rate']),
                "std_rate": float(row['std_rate']),
                "guidance_range": f"₹{row['guidance_low']} - ₹{row['guidance_high']}",
                "guidance_low": float(row['guidance_low']),
                "guidance_high": float(row['guidance_high']),
                "outlier_count": int(row['outlier_count']),
            }
            if row['outlier_count'] > 0:
                entry["outlier_rates"] = row['outlier_rates']
                outlier_oils.append(row['oil_type'])
            pricing_data.append(entry)
        
        return {
            "data": pricing_data,
            "oils_with_outliers": outlier_oils,
        }

    # ── Daily Actions ────────────────────────────────────────────────
    def _handle_actions(self, bdo_name):
        actions = self.de.get_top_5_actions(bdo_name)
        return {
            "actions": actions,
            "summary": self.fe.get_bdo_metrics(bdo_name)
        }
