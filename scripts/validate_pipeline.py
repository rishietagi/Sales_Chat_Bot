import pandas as pd
from backend.services.data_engine import DataEngine
from backend.services.rule_engine import RuleEngine
import os

def run_validation():
    print("--- Starting Validation Pipeline ---")
    data_path = "Emami_Direct_Dealer_Sauda_Data - Dummy Data.xlsx"
    
    # 1. Load and Standardize
    print(f"Loading workbook: {data_path}...")
    engine = DataEngine(data_path)
    engine.load_data()
    df = engine.standardize_and_merge()
    print(f"Data joined. Total records: {len(df)}")
    
    # 2. Apply Rules
    print("Applying action rules...")
    df_with_actions = RuleEngine.apply_rules(df)
    
    # 3. Validation Checks
    print("\n--- Summary Metrics ---")
    print(f"Total Revenue: {df_with_actions['total_revenue'].sum():,.2f}")
    print(f"Total Outstanding: {df_with_actions['outstanding_amount'].sum():,.2f}")
    print(f"Dormant Dealers: {df_with_actions['is_dormant'].sum()}")
    print(f"High Value Dealers: {df_with_actions['is_high_value'].sum()}")
    
    # 4. Save cleaned output
    output_path = "data/processed_dealer_metrics.csv"
    os.makedirs("data", exist_ok=True)
    df_with_actions.to_csv(output_path, index=False)
    print(f"\nProcessed data saved to {output_path}")
    
    print("\n--- Sample Next-Best-Actions ---")
    print(df_with_actions[['Dealer Name', 'priority_score', 'actions']].head(10))

if __name__ == "__main__":
    run_validation()
