import streamlit as st
import pandas as pd

# ------------------------------------------------------------------ #
# Column display maps: intent → [(internal_col, display_name)]       #
# ------------------------------------------------------------------ #
DISPLAY_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "dealer_ranking": [
        ("CUSTOMERNAME", "Dealer"),
        ("contact_name", "Contact"),
        ("phone", "Phone"),
        ("total_sales", "Total Sales ($)"),
        ("order_count", "Orders"),
        ("recommended_actions", "Action"),
        ("action_reasons", "Why"),
    ],
    "dormant_dealers": [
        ("CUSTOMERNAME", "Dealer"),
        ("contact_name", "Contact"),
        ("phone", "Phone"),
        ("days_since_last_order", "Days Inactive"),
        ("total_sales", "Total Sales ($)"),
        ("recommended_actions", "Action"),
        ("action_reasons", "Why"),
    ],
    "slowing_dealers": [
        ("CUSTOMERNAME", "Dealer"),
        ("contact_name", "Contact"),
        ("phone", "Phone"),
        ("recent_sales_90d", "Recent 90d ($)"),
        ("past_sales_90d", "Prior 90d ($)"),
        ("sales_change_pct", "Change (%)"),
        ("recommended_actions", "Action"),
    ],
    "status_follow_up": [
        ("CUSTOMERNAME", "Dealer"),
        ("contact_name", "Contact"),
        ("phone", "Phone"),
        ("non_final_count", "Stuck Orders"),
        ("total_sales", "Total Sales ($)"),
        ("recommended_actions", "Action"),
        ("action_reasons", "Why"),
    ],
    "territory_performance": [
        ("TERRITORY", "Territory"),
        ("total_sales", "Total Sales ($)"),
        ("order_count", "Orders"),
        ("active_dealers", "Active Dealers"),
        ("dormant_dealers", "Dormant"),
        ("blocked_orders", "Blocked Orders"),
    ],
    "product_analysis": [
        ("PRODUCTLINE", "Product Line"),
        ("total_sales", "Total Sales ($)"),
        ("order_count", "Orders"),
        ("unique_dealers", "Dealers"),
    ],
    "time_trend": [
        ("YEAR_ID", "Year"),
        ("QTR_ID", "Qtr"),
        ("MONTH_ID", "Month"),
        ("total_sales", "Total Sales ($)"),
        ("order_count", "Orders"),
        ("mom_change_pct", "MoM Change (%)"),
    ],
    "contact_lookup": [
        ("CUSTOMERNAME", "Dealer"),
        ("contact_name", "Contact"),
        ("phone", "Phone"),
        ("city", "City"),
        ("country", "Country"),
        ("total_sales", "Total Sales ($)"),
        ("days_since_last_order", "Days Inactive"),
    ],
}


def select_display_columns(intent: str, df: pd.DataFrame) -> pd.DataFrame:
    """Picks only the important columns for a given intent and renames them."""
    col_map = DISPLAY_COLUMNS.get(intent)
    if not col_map:
        return df

    available = [(src, dst) for src, dst in col_map if src in df.columns]
    if not available:
        return df

    src_cols, dst_cols = zip(*available)
    slim = df[list(src_cols)].copy()
    slim.columns = list(dst_cols)

    # Format currency and percentage columns
    for col in slim.columns:
        if "($)" in col:
            slim[col] = slim[col].apply(
                lambda v: f"${v:,.0f}" if pd.notna(v) else "–"
            )
        elif "(%)" in col:
            slim[col] = slim[col].apply(
                lambda v: f"{v:+.1f}%" if pd.notna(v) else "–"
            )

    return slim


def render_chat_response(
    explanation: str, result_df: pd.DataFrame, intent: str, msg_idx: int = 0
):
    """Renders the AI response inside a chat bubble with an expandable table."""
    st.markdown(explanation)

    if not result_df.empty:
        display_df = select_display_columns(intent, result_df)
        with st.expander("📊 View Data Table", expanded=False):
            st.dataframe(
                display_df, use_container_width=True, hide_index=True,
                key=f"table_{intent}_{msg_idx}",
            )
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV", csv, "results.csv", "text/csv",
                key=f"dl_{intent}_{msg_idx}",
            )


def render_dataset_summary(df: pd.DataFrame):
    """Small summary chips above the chat area showing what data is loaded."""
    cols = st.columns(4)
    cols[0].metric("Dealers", f"{df['CUSTOMERNAME'].nunique()}" if "CUSTOMERNAME" in df.columns else "–")
    cols[1].metric("Orders", f"{df['ORDERNUMBER'].nunique():,}" if "ORDERNUMBER" in df.columns else "–")
    total = df["SALES"].sum() if "SALES" in df.columns else 0
    cols[2].metric("Total Revenue", f"${total:,.0f}")
    if "ORDERDATE" in df.columns:
        mn = df["ORDERDATE"].min()
        mx = df["ORDERDATE"].max()
        cols[3].metric("Date Range", f"{mn:%b %Y} – {mx:%b %Y}" if pd.notna(mn) else "–")
    else:
        cols[3].metric("Date Range", "–")
