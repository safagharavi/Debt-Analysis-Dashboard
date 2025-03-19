import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import os
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="Company Funding Dashboard",
    page_icon="💰",
    layout="wide"
)

# Define function to categorize funding types
def categorize_funding(funding_type, equity_only):
    if funding_type == "Grant":
        return "Grant"
    elif funding_type == "Debt Financing" or "Debt" in funding_type:
        return "Debt"
    elif equity_only == "Yes" or "Series" in funding_type or "Venture" in funding_type or "Equity" in funding_type:
        return "Equity"
    else:
        return "Other"

# Load and process the data
@st.cache_data
def load_data():
    df = pd.read_csv('funding-rounds-17-03-2025.csv')
    
    # Convert date to datetime format
    df['Announced Date'] = pd.to_datetime(df['Announced Date'])
    
    # Sort by date
    df = df.sort_values('Announced Date')
    
    # Categorize funding types into Equity, Debt, and Grant
    df['Funding Category'] = df.apply(
        lambda row: categorize_funding(row['Funding Type'], row['Equity Only Funding']), 
        axis=1
    )
    
    return df

# Function to load company logo
def load_company_logo(company_name):
    # Create a standardized filename (lowercase, replace spaces with underscores)
    filename = company_name.lower().replace(' ', '_').replace(',', '').replace('.', '') + '.png'
    logo_path = os.path.join('logos', filename)
    
    # Check if logo file exists
    if os.path.exists(logo_path):
        return Image.open(logo_path)
    else:
        return None

# Load the data
df = load_data()

# Dashboard title
st.title("Company Funding Dashboard")
st.markdown("Visualize funding rounds by company, showing Equity, Debt, and Grant funding types.")

# Sidebar with filters
st.sidebar.header("Filters")

# Get all unique companies
companies = sorted(df['Organization Name'].unique())

# Company selection
selected_company = st.sidebar.selectbox(
    "Select a Company", 
    options=companies,
    index=0
)

# Load and display company logo in sidebar
logo = load_company_logo(selected_company)
if logo:
    # Add some space before the logo
    st.sidebar.markdown("---")
    st.sidebar.subheader("Company Logo")
    # Display logo in the sidebar with appropriate width
    st.sidebar.image(logo, width=200)
else:
    # If no logo is found, display a message (can be commented out in production)
    st.sidebar.markdown("---")
    st.sidebar.info(f"No logo found for {selected_company}")

# Filter data for selected company
company_data = df[df['Organization Name'] == selected_company]

# Display company information in main area
st.header(f"Funding Information for {selected_company}")

# Show summary statistics
total_raised = company_data['Money Raised (in USD)'].sum()
num_rounds = len(company_data)
latest_round = company_data.iloc[-1]['Funding Type'] if not company_data.empty else "N/A"
latest_date = company_data.iloc[-1]['Announced Date'].strftime("%B %d, %Y") if not company_data.empty else "N/A"

# Calculate funding by category totals
funding_by_category = company_data.groupby('Funding Category')['Money Raised (in USD)'].sum()

# Default values in case some categories don't exist
equity_funding = funding_by_category.get('Equity', 0)
debt_funding = funding_by_category.get('Debt', 0)
grant_funding = funding_by_category.get('Grant', 0)

# Calculate debt-to-equity ratio
debt_to_equity = "N/A"
if equity_funding > 0:
    debt_to_equity = f"{debt_funding / equity_funding:.2f}"

# Calculate debt-to-total funding ratio
debt_to_total = 0
if total_raised > 0:
    debt_to_total = f"{(debt_funding / total_raised) * 100:.1f}%"

col1, col2 = st.columns(2)

# Apply smaller font size to metrics using markdown with HTML
col1.markdown("<div style='font-size: 20px;'><b>Total Funding</b><br/>{}</div>".format(f"${total_raised:,.0f}"), unsafe_allow_html=True)
col1.markdown("<div style='font-size: 20px;'><b>Number of Rounds</b><br/>{}</div>".format(num_rounds), unsafe_allow_html=True)
col2.markdown("<div style='font-size: 20px;'><b>Latest Round</b><br/>{}</div>".format(f"{latest_round} ({latest_date})"), unsafe_allow_html=True)

# Create a new row for financial ratios
st.subheader("Financial Ratios")
ratio_col1, ratio_col2, ratio_col3 = st.columns(3)
ratio_col1.metric("Debt-to-Equity Ratio", debt_to_equity)
ratio_col2.metric("Debt-to-Total Funding", debt_to_total)
ratio_col3.metric("Equity Percentage", f"{(equity_funding / total_raised) * 100:.1f}%" if total_raised > 0 else "0%")

# Rest of the code remains the same...
# Show funding breakdown by type
st.subheader("Funding Breakdown")
funding_types = company_data.groupby('Funding Category')['Money Raised (in USD)'].sum().reset_index()

if not funding_types.empty:
    # Use the same consistent colors as defined for the bar chart
    category_colors = {
        'Equity': '#1f77b4',  # Blue
        'Debt': '#ff7f0e',    # Orange
        'Grant': '#2ca02c'    # Green
    }
    
    # Map colors to categories in the data
    colors = [category_colors.get(category, '#d62728') for category in funding_types['Funding Category']]
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=funding_types['Funding Category'],
        values=funding_types['Money Raised (in USD)'],
        hole=.4,
        marker_colors=colors,
        hovertemplate='%{label}: $%{value:,.0f} (%{percent})'
    )])
    
    fig_pie.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=30, b=0),
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("No funding data available for the selected company.")

# Show stacked bar chart of funding rounds
st.subheader("Funding Rounds Over Time")

# Group data by date and funding category
funding_by_category = pd.pivot_table(
    company_data, 
    values='Money Raised (in USD)', 
    index=['Announced Date'],
    columns=['Funding Category'], 
    aggfunc=np.sum,
    fill_value=0
)

# Create Plotly figure
fig = go.Figure()

# Define consistent colors for each funding category
category_colors = {
    'Equity': '#1f77b4',  # Blue
    'Debt': '#ff7f0e',    # Orange
    'Grant': '#2ca02c'    # Green
}

# Add traces for each funding category that exists in the data
for category in ['Equity', 'Debt', 'Grant']:
    if category in funding_by_category.columns:
        fig.add_trace(
            go.Bar(
                x=funding_by_category.index,
                y=funding_by_category[category],
                name=category,
                marker_color=category_colors[category],
                hovertemplate='%{y:$,.0f}'
            )
        )

# Update layout
fig.update_layout(
    barmode='stack',
    xaxis_title="Announced Date",
    yaxis_title="Money Raised (USD)",
    hovermode="x unified",
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Format y-axis as currency
fig.update_yaxes(tickprefix="$", tickformat=",")

# Show the chart
st.plotly_chart(fig, use_container_width=True)

# Display detailed funding rounds
st.subheader("Funding Rounds Details")
details_df = company_data[['Announced Date', 'Funding Type', 'Money Raised (in USD)', 'Lead Investors']]
details_df = details_df.rename(columns={
    'Money Raised (in USD)': 'Amount (USD)'
})
details_df['Announced Date'] = details_df['Announced Date'].dt.strftime('%Y-%m-%d')
details_df['Amount (USD)'] = details_df['Amount (USD)'].apply(lambda x: f"${x:,.0f}")
# Display dataframe without the index column
st.dataframe(details_df, use_container_width=True, hide_index=True)
