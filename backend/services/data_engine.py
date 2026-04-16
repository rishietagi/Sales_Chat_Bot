import pandas as pd
import numpy as np
from datetime import datetime
import os

class DataEngine:
    def __init__(self, file_path):
        self.file_path = file_path
        self.raw_data = {}
        self.processed_df = None

    def load_data(self):
        """Loads all sheets from the Excel workbook."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Workbook not found at {self.file_path}")
        
        xl = pd.ExcelFile(self.file_path)
        for sheet in xl.sheet_names:
            self.raw_data[sheet] = pd.read_excel(self.file_path, sheet_name=sheet)
        
        return self.raw_data

    def standardize_and_merge(self):
        """Standardizes columns and merges sheets into a unified dealer-level dataset."""
        master = self.raw_data.get('Active Dealer Master')
        sales = self.raw_data.get('1Y Sauda Sales Data')
        open_orders = self.raw_data.get('Open Orders')
        pending_payments = self.raw_data.get('Pending Payments')

        if master is None or sales is None:
            raise ValueError("Missing critical sheets: Master or Sales")

        # Ensure date columns are datetime
        sales['Sauda Order Date'] = pd.to_datetime(sales['Sauda Order Date'])
        if 'Sauda Expiry Date' in sales.columns:
            sales['Sauda Expiry Date'] = pd.to_datetime(sales['Sauda Expiry Date'])
            
        if open_orders is not None:
             open_orders['Sauda Order Date'] = pd.to_datetime(open_orders['Sauda Order Date'])
             if 'Sauda Expiry Date' in open_orders.columns:
                 open_orders['Sauda Expiry Date'] = pd.to_datetime(open_orders['Sauda Expiry Date'])
                 
        if pending_payments is not None:
             pending_payments['Sauda Order Date'] = pd.to_datetime(pending_payments['Sauda Order Date'])
             pending_payments['Invoice Date'] = pd.to_datetime(pending_payments['Invoice Date'])
             
        today = datetime.now()

        # Aggregate Sales by Dealer
        sales['is_active_sauda'] = sales['Sauda Expiry Date'] >= today if 'Sauda Expiry Date' in sales.columns else False
        
        sales_agg = sales.groupby('Dealer Code').agg({
            'Order Value (INR)': 'sum',
            'Order Quantity (Cases)': 'sum',
            'Sauda Order Date': ['max', 'min', 'count'],
            'is_active_sauda': 'max',
            'SKU': 'nunique'
        })
        sales_agg.columns = ['total_revenue', 'total_quantity', 'last_order_date', 'first_order_date', 'order_count', 'has_active_sauda', 'sku_diversity']
        
        # Calculate derived metrics from sales
        sales_agg['days_since_last_order'] = (today - sales_agg['last_order_date']).dt.days
        sales_agg['avg_order_value'] = sales_agg['total_revenue'] / sales_agg['order_count']
        
        # Aggregate Open Orders
        if open_orders is not None:
            open_orders['pending_dispatch_qty'] = open_orders['Order Quantity (Cases)'] - open_orders['Dispatched Quantity']
            oo_agg = open_orders.groupby('Dealer Code').agg({
                'Order Value (INR)': 'sum',
                'Order Quantity (Cases)': 'sum',
                'Dispatched Quantity': 'sum',
                'pending_dispatch_qty': 'sum',
                'SKU': 'count'
            })
            oo_agg.columns = ['open_order_value', 'oo_total_qty', 'oo_dispatched_qty', 'pending_dispatch_qty', 'open_order_count']
            oo_agg['dispatch_ratio'] = oo_agg['oo_dispatched_qty'] / oo_agg['oo_total_qty']
            sales_agg = sales_agg.join(oo_agg, how='left')
        
        # Aggregate Pending Payments
        if pending_payments is not None:
            pp_agg = pending_payments.groupby('Dealer Code').agg({
                'Outstanding Amount (INR)': 'sum',
                'Amount Collected (INR)': 'sum',
                'Order Value (INR)': 'sum',
                'SKU': 'count'
            })
            pp_agg.columns = ['outstanding_amount', 'amount_collected', 'pp_total_order_value', 'pending_invoice_count']
            pp_agg['collection_ratio'] = pp_agg['amount_collected'] / (pp_agg['amount_collected'] + pp_agg['outstanding_amount'])
            pp_agg['pending_collection_pct'] = pp_agg['outstanding_amount'] / pp_agg['pp_total_order_value']
            sales_agg = sales_agg.join(pp_agg, how='left')

        # Join with Master
        self.processed_df = master.set_index('Dealer Code').join(sales_agg, how='left')
        self.processed_df = self.processed_df.reset_index()
        
        # Fill NaNs for operational metrics
        fill_cols = [
            'open_order_value', 'open_order_count', 'outstanding_amount', 
            'pending_invoice_count', 'dispatch_ratio', 'collection_ratio',
            'pending_dispatch_qty', 'pending_collection_pct', 'has_active_sauda'
        ]
        for col in fill_cols:
            if col in self.processed_df.columns:
                self.processed_df[col] = self.processed_df[col].fillna(0)
        
        return self.processed_df

    def get_sku_analytics(self):
        """Standardizes SKU analytics."""
        sales = self.raw_data.get('1Y Sauda Sales Data')
        if sales is None: return None
        
        sku_agg = sales.groupby('SKU').agg({
            'Order Value (INR)': 'sum',
            'Order Quantity (Cases)': 'sum',
            'Dealer Code': 'nunique'
        }).rename(columns={
            'Order Value (INR)': 'revenue',
            'Order Quantity (Cases)': 'quantity',
            'Dealer Code': 'dealer_reach'
        })
        return sku_agg.sort_values(by='revenue', ascending=False)
