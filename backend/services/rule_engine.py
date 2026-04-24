import pandas as pd

class RuleEngine:
    @staticmethod
    def apply_rules(df):
        """Applies business rules to derive action labels and prioritization."""
        if df is None: return None
        
        # 1. Dormant Detection (Exclude dealers with active/open orders)
        has_active_orders = df.get('open_order_count', 0) > 0
        df['is_dormant'] = (df['days_since_last_order'] > 30) & ~has_active_orders
        df['is_reactivation_candidate'] = (df['days_since_last_order'] > 15) & (df['days_since_last_order'] <= 30) & ~has_active_orders

        # 2. High Value Dealer (Top 20% by revenue)
        if 'total_revenue' in df.columns:
            threshold = df['total_revenue'].quantile(0.8)
            df['is_high_value'] = df['total_revenue'] >= threshold
        
        # 3. Action Labels
        def get_actions(row):
            actions = []
            if row.get('is_dormant'):
                actions.append("Call dealer")
            elif row.get('is_reactivation_candidate'):
                actions.append("Monitor")
            
            if row.get('outstanding_amount', 0) > 0 and row.get('pending_collection_pct', 0) > 0.2:
                actions.append("Follow up for collection")
            
            if row.get('pending_dispatch_qty', 0) > 0 and row.get('dispatch_ratio', 1) < 0.8:
                actions.append("Contact Warehouse for dispatch")
                
            if row.get('has_active_sauda') and (row.get('days_since_last_order', 0) > 20):
                actions.append("Renew / extend sauda")
                
            if getattr(row, 'collection_gap', 0) > 100000:
                actions.append("Escalate")
                
            return actions

        df['actions'] = df.apply(get_actions, axis=1)
        
        # 4. Priority Score (Higher is more urgent)
        def get_priority(row):
            score = 0
            if row.get('is_dormant'): score += 50
            if row.get('is_reactivation_candidate'): score += 10
            if row.get('outstanding_amount', 0) > 0: score += (row['outstanding_amount'] / 10000)
            if row.get('pending_dispatch_qty', 0) > 0: score += 20 * (1 - row.get('dispatch_ratio', 1))
            if row.get('is_high_value'): score += 20
            if "Escalate" in row.get('actions', []): score += 100
            return score

        df['priority_score'] = df.apply(get_priority, axis=1)
        
        return df.sort_values(by='priority_score', ascending=False)
