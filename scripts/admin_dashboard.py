"""
Admin dashboard for the RAG application.
Provides administrative controls, RAG configuration, and usage statistics.
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

# Import our modules
from src.rag import LocalRAG
from src.embeddings import EmbeddingsGenerator
from src.llm_factory import create_llm
from src.usage_integration import (
    initialize_usage_limiter,
    get_client_ip,
    save_admin_ip
)
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME, LLM_PROVIDER

def mask_ip(ip):
    """
    Mask an IP address for display while preserving some identifying information.
    
    Args:
        ip: The IP address to mask
        
    Returns:
        str: The masked IP address
    """
    if not ip:
        return ""
        
    # Function to mask a segment of an IP address
    def mask_segment(segment):
        if len(segment) <= 2:
            return segment  # Keep very short segments as is
        elif len(segment) <= 4:
            return segment[0] + '*' * (len(segment) - 1)
        else:
            return segment[0:2] + '*' * (len(segment) - 2)
    
    # Handle IPv4 addresses (like 192.168.1.1)
    if '.' in ip:
        parts = ip.split('.')
        # Show first part, mask the rest (except last digit of last part)
        if len(parts) >= 4:
            return f"{parts[0]}.{parts[1][0]}*.*.{parts[3][-1]}"
        else:
            return '.'.join([mask_segment(part) for part in parts])
            
    # Handle IPv6 addresses
    elif ':' in ip:
        parts = ip.split(':')
        # Only show first and last part partially
        if len(parts) > 2:
            masked_parts = [mask_segment(parts[0])]
            masked_parts.extend(['****' for _ in range(len(parts)-2)])
            masked_parts.append(mask_segment(parts[-1]))
            return ':'.join(masked_parts)
        else:
            return ':'.join([mask_segment(part) for part in parts])
            
    # Handle other formats (unlikely)
    else:
        if len(ip) <= 4:
            return ip[0] + '*' * (len(ip) - 1)
        else:
            return ip[0:2] + '*' * (len(ip) - 4) + ip[-2:]
        
# Set page configuration
st.set_page_config(
    page_title="Admin Dashboard - Executive Orders RAG",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🔒 Admin Dashboard")
st.markdown("Administrative controls, configuration, and usage statistics for the Executive Orders RAG system.")

# Get the limiter instance
limiter = initialize_usage_limiter()

# Get client IP
client_ip = get_client_ip()

# Check admin access
if not limiter.is_admin_ip(client_ip):
    st.error("Access Denied: Administrator access required.")
    
    # IP Management Section for non-admins
    st.markdown("## IP Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Option to add current IP as admin
        if st.button(f"Add Current IP to Admin List"):
            # Add the current IP to admin IPs
            limiter.add_admin_ip(client_ip)
            limiter.add_unlimited_ip(client_ip)
            
            # Attempt to save the IP
            if save_admin_ip(client_ip):
                st.success(f"Added your IP to admin list. Refresh to access admin dashboard.")
            else:
                st.error("Failed to save admin IP.")
    
    with col2:
        # Manual IP entry option
        manual_ip = st.text_input("Enter IP to add to admin list")
        if st.button("Add Manual IP"):
            if manual_ip:
                limiter.add_admin_ip(manual_ip)
                limiter.add_unlimited_ip(manual_ip)
                
                # Save to persistent storage
                if save_admin_ip(manual_ip):
                    st.success(f"Added {manual_ip} to admin list. Refresh to access admin dashboard.")
                else:
                    st.error("Failed to save admin IP.")
    
    st.markdown("### Return to Application")
    if st.button("Back to Main App"):
        st.switch_page("app.py")
        
    st.stop()  # Stop execution for non-admin users

# Create tabs for different admin sections
config_tab, usage_tab, llm_tab, rag_tab = st.tabs([
    "💡 Usage Configuration", 
    "📊 Usage Statistics", 
    "🤖 LLM Settings",
    "🔍 RAG Settings"
])

# TAB 1: USAGE CONFIGURATION
with config_tab:
    st.header("Usage Limiting Configuration")
    
    # System Status
    st.subheader("System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Limiting Status", 
            "Enabled" if limiter.enabled else "Disabled"
        )
        
        if st.button("Toggle Limiting Status"):
            new_state = limiter.toggle_enabled()
            st.success(f"Usage limiting {'enabled' if new_state else 'disabled'}")
            st.experimental_rerun()
    
    with col2:
        st.metric(
            "Prompt Limit", 
            str(limiter.prompt_limit or "No Limit")
        )
    
    with col3:
        st.metric(
            "Reset Period", 
            f"{limiter.reset_period.total_seconds() / 3600:.1f} hours"
        )
    
    # Limit settings
    st.subheader("Limit Settings")
    
    limit_col1, limit_col2, limit_col3 = st.columns(3)
    
    with limit_col1:
        prompt_limit = st.number_input(
            "Prompt Limit", 
            min_value=0,
            max_value=1000,
            value=limiter.prompt_limit or 20,
            help="Max prompts per user per day (0 = no limit)"
        )
    
    with limit_col2:
        token_limit = st.number_input(
            "Token Limit", 
            min_value=0,
            max_value=1000000,
            value=limiter.token_limit or 0,
            help="Max tokens per user per day (0 = no limit)"
        )
    
    with limit_col3:
        reset_hours = st.slider(
            "Reset Period (hours)",
            min_value=1,
            max_value=168,
            value=int(limiter.reset_period.total_seconds() / 3600),
            help="Hours before usage counters reset"
        )
    
    if st.button("Update Limits"):
        # Convert 0 to None for no limit
        prompt_limit_val = None if prompt_limit == 0 else prompt_limit
        token_limit_val = None if token_limit == 0 else token_limit
        
        new_limits = limiter.update_limits(
            prompt_limit=prompt_limit_val,
            token_limit=token_limit_val,
            reset_period_hours=reset_hours
        )
        st.success(f"Limits updated: {json.dumps(new_limits)}")
    
    # IP Management
    st.subheader("IP Management")
    
    ip_col1, ip_col2 = st.columns(2)
    
    with ip_col1:
        st.markdown("#### Add New Admin IP")
        new_admin_ip = st.text_input("IP Address")
        if st.button("Add Admin IP") and new_admin_ip:
            limiter.add_admin_ip(new_admin_ip)
            limiter.add_unlimited_ip(new_admin_ip)
            
            # Save to persistent storage
            if save_admin_ip(new_admin_ip):
                st.success(f"Added {new_admin_ip} to admin list")
            else:
                st.error("Failed to save admin IP.")
        
        # Add the remove current IP button
        st.markdown("#### Remove Current IP from Admin")
        current_ip = get_client_ip()
        if st.button("Remove My IP from Admin List"):
            # Check if this IP is an admin
            if limiter.is_admin_ip(current_ip):
                # Remove from unlimited IPs if it exists
                if current_ip in limiter.unlimited_ips:
                    limiter.unlimited_ips.remove(current_ip)
                    
                # Remove from admin IPs if it exists  
                if current_ip in limiter.admin_ips:
                    limiter.admin_ips.remove(current_ip)
                    
                # Update the admin_ips.txt file
                try:
                    config_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'admin_ips.txt')
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            existing_ips = [line.strip() for line in f.readlines() 
                                           if line.strip() and line.strip() != current_ip]
                        
                        # Write back to file without the current IP
                        with open(config_path, 'w') as f:
                            for ip in existing_ips:
                                f.write(f"{ip}\n")
                        
                        st.success(f"Successfully removed {current_ip} from admin IPs")
                        st.warning("You will lose admin access after the next refresh!")
                    else:
                        st.error("admin_ips.txt file not found")
                except Exception as e:
                    st.error(f"Error updating admin_ips.txt: {e}")
            else:
                st.info(f"IP {current_ip} is not currently an admin")
    
    with ip_col2:
        st.markdown("#### Current Admin IPs")
        admin_ips_display = "\n".join(limiter.admin_ips)
        st.code(admin_ips_display)
        
        # Show the current IP
        st.markdown("#### Your Current IP")
        st.code(current_ip)
        st.info("If your IP appears in the admin list above, you have unlimited access and won't be subject to usage limits.")

# TAB 2: USAGE STATISTICS
with usage_tab:
    st.header("Usage Statistics")
    
    try:
        # Get client IP
        client_ip = get_client_ip()
        
        # Make sure we're passing the admin IP to get_usage_stats
        if not limiter.is_admin_ip(client_ip):
            st.error("Unauthorized access to usage statistics")
        else:
            # Get usage data with explicit admin IP
            stats = limiter.get_usage_stats(admin_ip=client_ip)  # Pass admin IP explicitly
            
            if isinstance(stats, dict) and "error" in stats:
                st.error(stats["error"])
            else:
                # Summary metrics
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                
                with metric_col1:
                    st.metric("Total Users", stats.get("total_ips", 0))
                
                with metric_col2:
                    st.metric("Total Prompts", stats.get("total_prompts", 0))
                
                with metric_col3:
                    st.metric("Total Tokens", f"{stats.get('total_tokens', 0):,}")
                
                # User table
                st.subheader("User Activity")
                
                if "ips" in stats and stats["ips"]:
                    # Create a list to hold user data
                    user_data = []
                    
                    for ip in stats["ips"]:
                        # Use admin_ip parameter here too
                        ip_stats = limiter.get_usage_stats(ip=ip, admin_ip=client_ip)
                        if "error" not in ip_stats and "usage" in ip_stats:
                            usage = ip_stats["usage"]
                            
                            # Mask the IP for display
                            masked_ip = mask_ip(ip)
                            
                            user_data.append({
                                "Original IP": ip,  # Keep the original IP for internal use
                                "IP": masked_ip,    # Display the masked IP
                                "Prompts": usage.get("prompt_count", 0),
                                "Tokens": usage.get("token_count", 0),
                                "Last Activity": usage.get("last_request", "Never"),
                                "Status": "Admin" if limiter.is_admin_ip(ip) else "Unlimited" if limiter.is_unlimited_ip(ip) else "Normal"
                            })
                    
                    if user_data:
                        # Convert to DataFrame, but exclude the original IP from display
                        display_df = pd.DataFrame(user_data)
                        display_df = display_df.drop(columns=["Original IP"])  # Remove the original IP
                        st.dataframe(display_df, use_container_width=True)
                        
                        # Reset user option - use the original IP for the reset operation
                        reset_col1, reset_col2 = st.columns([3, 1])
                        
                        with reset_col1:
                            # Show masked IPs in the dropdown but keep mapping to original IPs
                            ip_options = [(row["IP"], row["Original IP"]) for row in user_data]
                            masked_ip_to_reset = st.selectbox(
                                "Select IP to reset",
                                options=[option[0] for option in ip_options]
                            )
                            
                            # Find the corresponding original IP
                            ip_to_reset = None
                            for masked, original in ip_options:
                                if masked == masked_ip_to_reset:
                                    ip_to_reset = original
                                    break
                        
                        with reset_col2:
                            if st.button("Reset Selected IP"):
                                if ip_to_reset and limiter.reset_ip_usage(ip_to_reset):
                                    st.success(f"Reset usage for {masked_ip_to_reset}")
                                    st.experimental_rerun()
                                else:
                                    st.error(f"Failed to reset usage for {masked_ip_to_reset}")
                    else:
                        st.info("No user activity data available.")
                else:
                    st.info("No users have used the system yet.")
                
                # Try to visualize usage
                try:
                    # Get all usage data
                    usage_data = limiter._load_usage_data()
                    
                    if usage_data and "usage" in usage_data and usage_data["usage"]:
                        # Create tab for visualizations
                        st.subheader("Usage Visualization")
                        
                        # Prepare data for visualization
                        all_data = []
                        
                        for ip in usage_data["usage"]:
                            data = usage_data["usage"][ip]
                            if "request_history" in data:
                                for entry in data["request_history"]:
                                    if "timestamp" in entry:
                                        try:
                                            timestamp = datetime.fromisoformat(entry["timestamp"])
                                            tokens = entry.get("tokens", 0)
                                            
                                            all_data.append({
                                                "IP": mask_ip(ip),  # Use masked IP for display
                                                "Timestamp": timestamp,
                                                "Tokens": tokens,
                                                "Date": timestamp.date(),
                                                "Hour": timestamp.hour
                                            })
                                        except (ValueError, TypeError):
                                            pass
                        
                        if all_data:
                            history_df = pd.DataFrame(all_data)
                            
                            # Create tabs for different views
                            viz_tab1, viz_tab2, viz_tab3 = st.tabs(["Daily Usage", "Hourly Distribution", "User Comparison"])
                            
                            with viz_tab1:
                                # Daily usage
                                daily_usage = history_df.groupby(history_df["Timestamp"].dt.date)["Tokens"].sum().reset_index()
                                daily_usage.columns = ["Date", "Tokens"]
                                
                                fig, ax = plt.subplots(figsize=(10, 4))
                                sns.barplot(x="Date", y="Tokens", data=daily_usage, ax=ax)
                                plt.xticks(rotation=45)
                                plt.tight_layout()
                                st.pyplot(fig)
                            
                            with viz_tab2:
                                # Hourly distribution
                                hourly_usage = history_df.groupby("Hour")["Tokens"].sum().reset_index()
                                
                                fig, ax = plt.subplots(figsize=(10, 4))
                                sns.barplot(x="Hour", y="Tokens", data=hourly_usage, ax=ax)
                                plt.xlabel("Hour of Day")
                                plt.ylabel("Total Tokens")
                                plt.tight_layout()
                                st.pyplot(fig)
                            
                            with viz_tab3:
                                # User comparison
                                user_usage = history_df.groupby("IP")["Tokens"].sum().reset_index()
                                user_usage = user_usage.sort_values("Tokens", ascending=False)
                                
                                fig, ax = plt.subplots(figsize=(10, 4))
                                sns.barplot(x="IP", y="Tokens", data=user_usage, ax=ax)
                                plt.xticks(rotation=45)
                                plt.tight_layout()
                                st.pyplot(fig)
                        else:
                            st.info("No detailed usage history available for visualization.")
                    else:
                        st.info("No usage data available for visualization.")
                except Exception as e:
                    st.error(f"Error generating visualization: {e}")
    except Exception as e:
        st.error(f"Error retrieving usage statistics: {e}")

# TAB 3: LLM SETTINGS
with llm_tab:
    st.header("LLM Configuration")
    
    # Initialize session state for LLM settings if not exists
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = LLM_PROVIDER
    if 'temperature' not in st.session_state:
        st.session_state.temperature = 0.7
    if 'use_llm' not in st.session_state:
        st.session_state.use_llm = True
    if 'llm_instance' not in st.session_state:
        st.session_state.llm_instance = None
    
    # LLM settings
    st.subheader("Model Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        use_llm = st.checkbox(
            "Use LLM for Response Generation", 
            value=st.session_state.use_llm,
            help="Enable to generate responses using LLM. Disable for search-only mode."
        )
    
    with col2:
        llm_provider = st.selectbox(
            "LLM Provider",
            options=["azure_ai_foundry", "azure_openai"],
            index=0 if st.session_state.llm_provider == "azure_ai_foundry" else 1,
            help="Select which LLM provider to use"
        )
    
    with col3:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="Controls randomness in LLM responses. Lower is more deterministic."
        )
    
    # Initialize or update LLM
    if st.button("Initialize LLM"):
        try:
            with st.spinner("Initializing LLM..."):
                llm_instance = create_llm(provider=llm_provider, temperature=temperature)
                st.session_state.llm_instance = llm_instance
                st.session_state.llm_provider = llm_provider
                st.session_state.temperature = temperature
                st.session_state.use_llm = use_llm
                st.success(f"✅ LLM initialized using {llm_provider}")
        except Exception as e:
            st.error(f"❌ Error initializing LLM: {str(e)}")
            st.session_state.llm_instance = None
    
    # Advanced LLM settings
    st.subheader("Advanced Settings")
    st.markdown("""
    These settings require restarting the application to take effect.
    They can be configured in your environment or config.py file.
    """)
    
    # Display current settings
    with st.expander("Current LLM Configuration"):
        # Format settings
        settings = {
            "Provider": LLM_PROVIDER,
            "Azure Search Endpoint": AZURE_SEARCH_ENDPOINT[:30] + "..." if AZURE_SEARCH_ENDPOINT and len(AZURE_SEARCH_ENDPOINT) > 30 else AZURE_SEARCH_ENDPOINT,
            "Azure Search Index": AZURE_SEARCH_INDEX_NAME
        }
        
        # Display as a table
        settings_df = pd.DataFrame(list(settings.items()), columns=["Setting", "Value"])
        st.table(settings_df)

# TAB 4: RAG SETTINGS
with rag_tab:
    st.header("RAG Configuration")
    
    # Initialize session state for RAG settings if not exists
    if 'index_file' not in st.session_state:
        st.session_state.index_file = "data/vector_store.json"
    if 'top_k' not in st.session_state:
        st.session_state.top_k = 3
    if 'similarity_threshold' not in st.session_state:
        st.session_state.similarity_threshold = 0.4
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = None
    
    # Vector store selection
    st.subheader("Vector Store")
    
    index_file = st.text_input(
        "Vector Store Index Path",
        value=st.session_state.index_file,
        help="Path to the vector store index file"
    )
    
    # RAG parameters
    st.subheader("Retrieval Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        top_k = st.slider(
            "Number of Results",
            min_value=1,
            max_value=10,
            value=st.session_state.top_k,
            help="Number of documents to retrieve"
        )
    
    with col2:
        similarity_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.similarity_threshold,
            step=0.05,
            help="Minimum similarity score for retrieved documents"
        )
    
    # Load vector store button
    if st.button("Load Vector Store"):
        try:
            if os.path.exists(index_file):
                with st.spinner("Loading vector store..."):
                    # Initialize RAG system
                    rag_system = LocalRAG(
                        vector_store_path=index_file,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                        llm=st.session_state.llm_instance if st.session_state.use_llm else None
                    )
                    
                    # Save to session state
                    st.session_state.rag_system = rag_system
                    st.session_state.index_file = index_file
                    st.session_state.top_k = top_k
                    st.session_state.similarity_threshold = similarity_threshold
                    
                    st.success(f"✅ Loaded vector store with {len(rag_system.vector_store.documents)} documents")
            else:
                st.error(f"❌ Vector store file not found: {index_file}")
                st.session_state.rag_system = None
        except Exception as e:
            st.error(f"❌ Error loading vector store: {str(e)}")
            st.session_state.rag_system = None
    
    # Vector store info
    if 'rag_system' in st.session_state and st.session_state.rag_system:
        st.subheader("Current Vector Store Status")
        
        # Display vector store information
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Documents", len(st.session_state.rag_system.vector_store.documents))
        
        with col2:
            st.metric("Top K", st.session_state.top_k)
        
        with col3:
            st.metric("Sim. Threshold", st.session_state.similarity_threshold)
    else:
        st.warning("RAG system is not initialized or vector store is not loaded.")
        
        # Check if the default file exists
        if os.path.exists(index_file):
            st.info(f"Vector store file exists at {index_file}. Click 'Load Vector Store' to initialize the RAG system.")
        else:
            st.error(f"Vector store file not found at {index_file}. Please specify a valid path to a vector store file.")

# Return to main app button
st.markdown("---")
st.markdown("### Return to Application")
if st.button("Back to Main App"):
    st.switch_page("app.py")