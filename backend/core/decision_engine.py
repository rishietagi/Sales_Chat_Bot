import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Computes Next-Best-Actions (NBA) for Business Development Officers.
    
    Priority ranking logic:
    P1 (Critical)  — Contracts expiring within 3 days with pending qty → Push dispatch urgently
    P2 (High)      — Deliveries arriving today → Inform dealer for receipt
    P3 (High)      — Contracts expiring within 7 days with pending qty → Call to push dispatch  
    P4 (Medium)    — High pending qty on active contracts (aging) → Follow up on dispatch
    P5 (Medium)    — Dormant dealers (in master, no active business) → Nudge for new sauda
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def get_top_5_actions(self, bdo_name: str) -> list:
        """Generates exactly 5 prioritized actions for the selected BDO."""
        bdo_df = self.df[self.df['bdo'] == bdo_name]
        if bdo_df.empty:
            return []

        scored_actions = []

        # ── P1: Contracts expiring in ≤3 days with pending qty (CRITICAL) ──
        sauda_df = bdo_df[bdo_df['contract_no'] != "Unknown"].drop_duplicates('contract_no')
        critical = sauda_df[
            (sauda_df['active_contract_flag'] == True) &
            (sauda_df['pending_qty'] > 0) &
            (sauda_df['days_to_contract_end'] <= 3) &
            (sauda_df['days_to_contract_end'] >= 0)
        ].sort_values('days_to_contract_end')

        for _, row in critical.iterrows():
            scored_actions.append({
                "score": 100 + row['pending_qty'],
                "action": f"URGENT: Push dispatch for {row['dealer_name']} — {row['material_desc']}",
                "reason": f"Contract expires in {int(row['days_to_contract_end'])} days with {int(row['pending_qty'])} qty still pending.",
                "priority": "Critical",
                "dealer": row['dealer_name'],
            })

        # ── P2: Deliveries arriving today (HIGH) ──
        deliveries = bdo_df[bdo_df['delivery_today_flag'] == 1].drop_duplicates(
            subset=['dealer_name', 'material_description_od']
        )
        for _, row in deliveries.iterrows():
            scored_actions.append({
                "score": 80,
                "action": f"Inform {row['dealer_name']} about today's delivery — {row['material_description_od']}",
                "reason": "Material is arriving today. Ensure dealer is ready for receipt.",
                "priority": "High",
                "dealer": row['dealer_name'],
            })

        # ── P3: Contracts expiring in 4-7 days with pending qty (HIGH) ──
        expiring_soon = sauda_df[
            (sauda_df['active_contract_flag'] == True) &
            (sauda_df['pending_qty'] > 0) &
            (sauda_df['days_to_contract_end'] > 3) &
            (sauda_df['days_to_contract_end'] <= 7)
        ].sort_values('days_to_contract_end')

        for _, row in expiring_soon.iterrows():
            scored_actions.append({
                "score": 60 + (7 - row['days_to_contract_end']) * 5,
                "action": f"Call {row['dealer_name']} to push dispatch for {row['material_desc']}",
                "reason": f"Contract expires in {int(row['days_to_contract_end'])} days. {int(row['pending_qty'])} qty pending.",
                "priority": "High",
                "dealer": row['dealer_name'],
            })

        # ── P4: Active contracts with high pending qty (MEDIUM) ──
        high_pending = sauda_df[
            (sauda_df['active_contract_flag'] == True) &
            (sauda_df['pending_qty'] > 0) &
            (sauda_df['days_to_contract_end'] > 7)
        ].sort_values('pending_qty', ascending=False)

        for _, row in high_pending.iterrows():
            scored_actions.append({
                "score": 40 + min(row['pending_qty'] / 100, 20),
                "action": f"Follow up with {row['dealer_name']} on pending {row['material_desc']}",
                "reason": f"{int(row['pending_qty'])} qty pending out of {int(row['contract_qty'])} total. {int(row['days_to_contract_end'])} days left on contract.",
                "priority": "Medium",
                "dealer": row['dealer_name'],
            })

        # ── P5: Dormant dealers — no active contract & no open DO (MEDIUM) ──
        active_codes = bdo_df[
            (bdo_df['contract_no'] != "Unknown") | (bdo_df['sales_document'] != "Unknown")
        ]['customer_code'].unique()
        all_dealers = bdo_df.drop_duplicates('customer_code')
        dormant = all_dealers[~all_dealers['customer_code'].isin(active_codes)]

        for _, row in dormant.iterrows():
            scored_actions.append({
                "score": 20,
                "action": f"Call {row['dealer_name']} ({row.get('city_town', '')}) for new sauda",
                "reason": "Dealer is in master but has no active contract or open delivery order.",
                "priority": "Medium",
                "dealer": row['dealer_name'],
            })

        # ── Step 1: Prioritize 1 action per unique dealer (highest score) ──
        scored_actions.sort(key=lambda x: x['score'], reverse=True)
        
        seen_dealers = set()
        unique_dealer_actions = []
        remaining_actions = []
        
        for a in scored_actions:
            if a['dealer'] not in seen_dealers:
                unique_dealer_actions.append(a)
                seen_dealers.add(a['dealer'])
            else:
                remaining_actions.append(a)

        # Combine: First unique dealers, then fill with remaining scored actions
        final_list = unique_dealer_actions + remaining_actions
        
        # ── Step 2: Take top 5 ──
        top5 = final_list[:5]

        # ── Step 3: Pad with generic tasks if still fewer than 5 ──
        if len(top5) < 5:
            # 1. Add pricing guidance check for most common oil type
            top5.append({
                "action": "Check pricing guidance for Sunflower and Soya oil",
                "reason": "Ensure basic rates in master are aligned with recent market median.",
                "priority": "Low",
                "dealer": "N/A"
            })
            
            # 2. Add pending payment review
            if len(top5) < 5:
                top5.append({
                    "action": "Review outstanding payments across all active accounts",
                    "reason": "Identify any payment blocks that might affect upcoming dispatches.",
                    "priority": "Low",
                    "dealer": "N/A"
                })
            
            # 3. Add contract aging check
            if len(top5) < 5:
                top5.append({
                    "action": "Audit contract aging for all Live Sauda",
                    "reason": "Review contracts that have been active for >30 days to check for slow movement.",
                    "priority": "Low",
                    "dealer": "N/A"
                })
            
            # 4. General data check
            if len(top5) < 5:
                top5.append({
                    "action": "Verify dealer contact details in master file",
                    "reason": "Ensure all phone numbers and addresses are current for emergency dispatch calls.",
                    "priority": "Low",
                    "dealer": "N/A"
                })

        # Format output
        result = []
        for i, a in enumerate(top5[:5], 1):
            result.append({
                "rank": i,
                "action": a['action'],
                "reason": a['reason'],
                "priority": a['priority'],
                "dealer": a['dealer'],
            })
        
        return result
