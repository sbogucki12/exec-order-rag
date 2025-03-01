"""
Admin dashboard for viewing usage statistics.
Run this script to view and manage usage limits and statistics.
"""
import os
import sys
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Add the parent directory to sys.path to enable imports from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.usage_limiter import UsageLimiter
from src.usage_config import get_usage_config

# Configure page
st.set_page_config(
    page_title="Usage Statistics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize usage limiter
config = get_usage_config()
usage_limiter = UsageLimiter(
    enabled=config["enabled"],
    usage_db_path=config["db_path"],
    prompt_limit=config["prompt_limit"],
    token_limit=config["token_limit"],
    reset_period_hours=config["reset_period_hours"],
    unlimited_ips=config["unlimited_ips"],
    admin_ips=config["admin_ips"]
)

# Header
st.title("📊 Usage Statistics Dashboard")
st.markdown("View and manage usage limits and statistics for the RAG application.")

# System Status
st.header("System Status")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Limiting Status", 
        "Enabled" if usage_limiter.enabled else "Disabled"
    )

with col2:
    st.metric(
        "Prompt Limit", 
        str(usage_limiter.prompt_limit or "No Limit")
    )

with col3:
    st.metric(
        "Reset Period", 
        f"{usage_limiter.reset_period.total_seconds() / 3600:.1f} hours"
    )

# Controls
st.header("Admin Controls")
controls_col1, controls_col2 = st.columns(2)

with controls_col1:
    toggle_limiting = st.button(
        "Toggle Usage Limiting",
        help="Enable or disable usage limiting"
    )
    
    if toggle_limiting:
        new_state = usage_limiter.toggle_enabled()
        st.success(f"Usage limiting {'enabled' if new_state else 'disabled'}")

with controls_col2:
    prompt_limit = st.number_input(
        "Prompt Limit",
        min_value=0,
        max_value=1000,
        value=usage_limiter.prompt_limit or 0,
        help="Maximum prompts per reset period (0 = no limit)"
    )
    
    token_limit = st.number_input(
        "Token Limit",
        min_value=0,
        max_value=1000000,
        value=usage_limiter.token_limit or 0,
        help="Maximum tokens per reset period (0 = no limit)"
    )
    
    reset_hours = st.slider(
        "Reset Period (hours)",
        min_value=1,
        max_value=168,
        value=int(usage_limiter.reset_period.total_seconds() / 3600),
        help="Hours before usage counters reset"
    )
    
    if st.button("Update Limits"):
        new_limits = usage_limiter.update_limits(
            prompt_limit=prompt_limit if prompt_limit > 0 else None,
            token_limit=token_limit if token_limit > 0 else None,
            reset_period_hours=reset_hours
        )
        st.success(f"Limits updated: {json.dumps(new_limits)}")

# Get usage data
usage_data = usage_limiter._load_usage_data()

# Check if we have usage data
if not usage_data.get("usage"):
    st.info("No usage data available yet.")
    st.stop()

# User Statistics Table
st.header("User Statistics")

# Prepare data for table
table_data = []
for ip, data in usage_data["usage"].items():
    row = {
        "IP Address": ip,
        "Prompts": data.get("prompt_count", 0),
        "Tokens": data.get("token_count", 0),
        "Last Request": datetime.fromisoformat(data.get("last_request", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
        "Last Reset": datetime.fromisoformat(data.get("last_reset", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
        "Status": "Unlimited" if usage_limiter.is_unlimited_ip(ip) else "Admin" if usage_limiter.is_admin_ip(ip) else "Normal"
    }
    table_data.append(row)

# Convert to DataFrame
df = pd.DataFrame(table_data)

# Add a button to reset user usage
reset_col1, reset_col2 = st.columns([2, 1])
with reset_col1:
    ip_to_reset = st.selectbox(
        "Select IP to reset",
        options=[row["IP Address"] for row in table_data]
    )

with reset_col2:
    if st.button("Reset Selected IP"):
        if usage_limiter.reset_ip_usage(ip_to_reset):
            st.success(f"Reset usage for {ip_to_reset}")
            st.experimental_rerun()
        else:
            st.error(f"Failed to reset usage for {ip_to_reset}")

# Display the table
st.dataframe(df, use_container_width=True)

# Usage Visualization
st.header("Usage Visualization")

# Prepare data for visualization
try:
    # Extract all timestamps and prompt counts
    all_data = []
    
    for ip, data in usage_data["usage"].items():
        if "request_history" in data:
            for entry in data["request_history"]:
                if "timestamp" in entry:
                    try:
                        timestamp = datetime.fromisoformat(entry["timestamp"])
                        tokens = entry.get("tokens", 0)
                        request_type = entry.get("type", "unknown")
                        
                        all_data.append({
                            "IP": ip,
                            "Timestamp": timestamp,
                            "Tokens": tokens,
                            "Type": request_type,
                            "Hour": timestamp.hour,
                            "Date": timestamp.date()
                        })
                    except (ValueError, TypeError):
                        pass
    
    if all_data:
        history_df = pd.DataFrame(all_data)
        
        # Daily usage chart
        st.subheader("Daily Token Usage")
        
        daily_usage = history_df.groupby(history_df["Timestamp"].dt.date)["Tokens"].sum().reset_index()
        daily_usage.columns = ["Date", "Tokens"]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x="Date", y="Tokens", data=daily_usage, ax=ax)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # Hourly distribution
        st.subheader("Usage by Hour of Day")
        
        hourly_usage = history_df.groupby("Hour")["Tokens"].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x="Hour", y="Tokens", data=hourly_usage, ax=ax)
        plt.xlabel("Hour of Day")
        plt.ylabel("Total Tokens")
        plt.tight_layout()
        st.pyplot(fig)
        
        # User comparison
        st.subheader("Usage by IP Address")
        
        user_usage = history_df.groupby("IP")["Tokens"].sum().reset_index()
        user_usage = user_usage.sort_values("Tokens", ascending=False)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x="IP", y="Tokens", data=user_usage, ax=ax)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
    else:
        st.info("No usage history data available for visualization.")
        
except Exception as e:
    st.error(f"Error generating visualization: {str(e)}")

# Raw Data Access
st.header("Raw Data Access")
if st.checkbox("Show raw usage data"):
    st.json(usage_data)