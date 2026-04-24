import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Builds BDO-focused derived metrics for Himani Best Choice from the flat joined dataset."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def get_bdo_metrics(self, bdo_name: str) -> dict:
        """Computes summary KPIs for a specific BDO."""
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        if bdo_df.empty:
            return {
                "total_dealers": 0,
                "active_dealers": 0,
                "total_contracts": 0,
                "active_contracts": 0,
                "total_booked_revenue": 0,
                "total_received_revenue": 0
            }

        # Total unique dealers
        total_dealers = bdo_df['customer_code'].nunique()

        # Active dealers: have a non-Unknown contract_no OR sales_document
        active_codes = bdo_df[
            (bdo_df['contract_no'] != "Unknown") | (bdo_df['sales_document'] != "Unknown")
        ]['customer_code'].unique()
        active_dealers = len(active_codes)

        # Sauda records (unique contract_no)
        sauda_df = bdo_df[bdo_df['contract_no'] != "Unknown"].drop_duplicates('contract_no')
        total_contracts = sauda_df.shape[0]
        active_contracts = sauda_df[sauda_df['active_contract_flag'] == True].shape[0]

        # Total Booked Revenue = sum(contract_value_est)
        total_booked_revenue = sauda_df['contract_value_est'].sum() if 'contract_value_est' in sauda_df.columns else 0

        # Total Received Revenue = sum(dispatch_value_est)
        total_received_revenue = sauda_df['dispatch_value_est'].sum() if 'dispatch_value_est' in sauda_df.columns else 0

        return {
            "total_dealers": total_dealers,
            "active_dealers": active_dealers,
            "total_contracts": total_contracts,
            "active_contracts": active_contracts,
            "total_booked_revenue": round(float(total_booked_revenue), 2),
            "total_received_revenue": round(float(total_received_revenue), 2)
        }

    def get_contract_data(self, bdo_name: str) -> pd.DataFrame:
        """Returns unique contract records for a BDO."""
        return self.df[(self.df['bdo'] == bdo_name) & (self.df['contract_no'] != "Unknown")].drop_duplicates('contract_no')

    def get_dispatch_data(self, bdo_name: str) -> pd.DataFrame:
        """Returns open DO records for a BDO."""
        return self.df[(self.df['bdo'] == bdo_name) & (self.df['sales_document'] != "Unknown")]

    def get_pricing_stats(self) -> pd.DataFrame:
        """Computes comprehensive rate stats by oil type including guidance and outliers."""
        # Filter for rows with valid rates first to avoid losing data during deduplication
        sauda_df = self.df[(self.df['contract_no'] != "Unknown") & 
                           (self.df['basic_rate'].notna()) & 
                           (self.df['basic_rate'] > 0)]
        
        # Deduplicate based on contract and rate to keep unique pricing points per contract
        sauda_df = sauda_df.drop_duplicates(subset=['contract_no', 'basic_rate'])
        
        if sauda_df.empty:
            return pd.DataFrame()
        
        stats = sauda_df.groupby('oil_type')['basic_rate'].agg(
            ['count', 'mean', 'median', 'min', 'max', 'std']
        ).reset_index()
        stats.columns = ['oil_type', 'contract_count', 'mean_rate', 'median_rate', 
                         'min_rate', 'max_rate', 'std_rate']
        
        # Round values
        for col in ['mean_rate', 'median_rate', 'min_rate', 'max_rate', 'std_rate']:
            stats[col] = stats[col].round(2)
        stats['std_rate'] = stats['std_rate'].fillna(0)
        
        # Add Q1, Q3, and recommended guidance range
        q1_vals, q3_vals = [], []
        guidance_low, guidance_high = [], []
        outlier_counts, outlier_details = [], []
        
        for oil in stats['oil_type']:
            rates = sauda_df[sauda_df['oil_type'] == oil]['basic_rate'].dropna()
            if len(rates) >= 3:
                q1 = round(rates.quantile(0.25), 2)
                q3 = round(rates.quantile(0.75), 2)
                iqr = q3 - q1
                low_fence = round(q1 - 1.5 * iqr, 2)
                high_fence = round(q3 + 1.5 * iqr, 2)
                outliers = rates[(rates < low_fence) | (rates > high_fence)]
                
                q1_vals.append(q1)
                q3_vals.append(q3)
                # Guidance: Use Q1-Q3 as the "safe" range for BDO negotiations
                guidance_low.append(q1)
                guidance_high.append(q3)
                outlier_counts.append(len(outliers))
                outlier_details.append(outliers.tolist()[:5])
            else:
                q1_vals.append(rates.min() if len(rates) > 0 else 0)
                q3_vals.append(rates.max() if len(rates) > 0 else 0)
                guidance_low.append(rates.min() if len(rates) > 0 else 0)
                guidance_high.append(rates.max() if len(rates) > 0 else 0)
                outlier_counts.append(0)
                outlier_details.append([])
        
        stats['q1_rate'] = q1_vals
        stats['q3_rate'] = q3_vals
        stats['guidance_low'] = guidance_low
        stats['guidance_high'] = guidance_high
        stats['outlier_count'] = outlier_counts
        stats['outlier_rates'] = outlier_details
        
        return stats

    def get_inactive_dealers(self, bdo_name: str) -> pd.DataFrame:
        """Identifies dealers in Master but with no active Sauda or Open DO."""
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        
        # A dealer is active if they have a non-Unknown contract_no OR a non-Unknown sales_document
        active_dealers = bdo_df[(bdo_df['contract_no'] != "Unknown") | 
                                (bdo_df['sales_document'] != "Unknown")]['customer_code'].unique()
        
        all_dealers = bdo_df['customer_code'].unique()
        inactive_codes = [c for c in all_dealers if c not in active_dealers]
        
        return bdo_df[bdo_df['customer_code'].isin(inactive_codes)].drop_duplicates('customer_code')
