import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from data_generator import generate_nilepay_data
from fraud_engine   import calculate_risk_scores

st.set_page_config(page_title="NilePay Fraud Detection",
                   page_icon="🔍", layout="wide")

st.markdown("""
<h1 style='text-align:center;color:#c0392b;'>🔍 NilePay</h1>
<p style='text-align:center;color:gray;'>
    Fraud Detection & Risk Monitoring System
</p><hr>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────
st.sidebar.header("⚙️ Settings")
n_tx       = st.sidebar.slider("Number of Transactions",
                                500, 5000, 1000, 500)
risk_filter = st.sidebar.multiselect(
    "Filter by Risk Level",
    ["🔴 High Risk", "🟡 Medium Risk", "🟢 Low Risk"],
    default=["🔴 High Risk", "🟡 Medium Risk"]
)
upload = st.sidebar.file_uploader(
    "Or upload your own CSV", type=["csv"])

# ── Load Data ────────────────────────────────────────────
@st.cache_data
def load_data(n, file=None):
    if file:
        df = pd.read_csv(file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df = generate_nilepay_data(n)
    return df

with st.spinner("Analyzing transactions..."):
    raw_df = load_data(n_tx, upload)
    df, vendor_stats = calculate_risk_scores(raw_df)

# ── Executive Summary ────────────────────────────────────
st.subheader("🎯 Executive Risk Summary")
total     = len(df)
high_risk = len(df[df['risk_level'] == "🔴 High Risk"])
med_risk  = len(df[df['risk_level'] == "🟡 Medium Risk"])
low_risk  = len(df[df['risk_level'] == "🟢 Low Risk"])
fraud_amt = df[df['risk_level'] == "🔴 High Risk"]['amount'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions", f"{total:,}")
col2.metric("🔴 High Risk",       f"{high_risk:,}",
            f"{high_risk/total*100:.1f}%")
col3.metric("🟡 Medium Risk",     f"{med_risk:,}",
            f"{med_risk/total*100:.1f}%")
col4.metric("💰 At-Risk Amount",  f"EGP {fraud_amt:,.0f}")

st.markdown("---")

# ── Risk Distribution Chart ──────────────────────────────
st.subheader("📊 Risk Distribution")
col1, col2 = st.columns(2)
with col1:
    risk_counts = df['risk_level'].value_counts().reset_index()
    risk_counts.columns = ['Risk Level', 'Count']
    fig = px.pie(risk_counts, values='Count', names='Risk Level',
                 color='Risk Level',
                 color_discrete_map={
                     "🔴 High Risk":   "#e74c3c",
                     "🟡 Medium Risk": "#f39c12",
                     "🟢 Low Risk":    "#2ecc71"},
                 title="Transaction Risk Distribution")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    flag_counts = {}
    for flags in df['flags']:
        for f in flags.split(", "):
            if f != "Clean":
                flag_counts[f] = flag_counts.get(f, 0) + 1
    if flag_counts:
        fig2 = px.bar(
            x=list(flag_counts.keys()),
            y=list(flag_counts.values()),
            color=list(flag_counts.keys()),
            title="Fraud Flags Breakdown",
            labels={'x': 'Flag Type', 'y': 'Count'}
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Time-based Analysis ──────────────────────────────────
st.subheader("⏰ Transaction Timing Analysis")
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
hourly = df.groupby(['hour', 'risk_level']).size().reset_index(name='count')
fig3 = px.bar(hourly, x='hour', y='count', color='risk_level',
              color_discrete_map={
                  "🔴 High Risk":   "#e74c3c",
                  "🟡 Medium Risk": "#f39c12",
                  "🟢 Low Risk":    "#2ecc71"},
              title="Transactions by Hour and Risk Level",
              labels={'hour': 'Hour of Day', 'count': 'Transactions'})
fig3.add_vrect(x0=23, x1=24, fillcolor="red", opacity=0.1,
               annotation_text="High Risk Hours")
fig3.add_vrect(x0=0,  x1=6,  fillcolor="red", opacity=0.1)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ── Vendor Risk Analysis ─────────────────────────────────
st.subheader("🏪 Vendor Risk Analysis")
vendor_stats['risk'] = vendor_stats['chargeback_rate'].apply(
    lambda x: "🔴 High Risk"   if x > 0.30
         else "🟡 Medium Risk" if x > 0.15
         else "🟢 Low Risk"
)
fig4 = px.scatter(
    vendor_stats, x='total', y='chargeback_rate',
    size='chargebacks', color='risk',
    color_discrete_map={
        "🔴 High Risk":   "#e74c3c",
        "🟡 Medium Risk": "#f39c12",
        "🟢 Low Risk":    "#2ecc71"},
    hover_name='vendor_id',
    title="Vendor Risk Map — Chargeback Rate vs Volume",
    labels={'total': 'Total Transactions',
            'chargeback_rate': 'Chargeback Rate'}
)
fig4.add_hline(y=0.30, line_dash="dash",
               line_color="red",
               annotation_text="High Risk Threshold")
st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ── Flagged Transactions ─────────────────────────────────
st.subheader("🚨 Flagged Transactions")
filtered = df[df['risk_level'].isin(risk_filter)] \
    if risk_filter else df

cols_show = ['transaction_id', 'customer_id', 'vendor_id',
             'amount', 'payment_method', 'timestamp',
             'city', 'transaction_status', 'risk_level', 'flags']
st.dataframe(filtered[cols_show].head(200),
             use_container_width=True)

# ── Amount Distribution ──────────────────────────────────
st.markdown("---")
st.subheader("💰 Amount Distribution by Risk")
fig5 = px.box(df, x='risk_level', y='amount', color='risk_level',
              color_discrete_map={
                  "🔴 High Risk":   "#e74c3c",
                  "🟡 Medium Risk": "#f39c12",
                  "🟢 Low Risk":    "#2ecc71"},
              title="Transaction Amount Distribution by Risk Level")
st.plotly_chart(fig5, use_container_width=True)

st.markdown("---")

# ── AI Fraud Analysis ────────────────────────────────────
st.subheader("🤖 AI Fraud Analysis Report")
if st.button("Generate AI Fraud Report"):
    with st.spinner("Analyzing fraud patterns..."):
        summary = {
            "total_transactions": total,
            "high_risk":          high_risk,
            "high_risk_pct":      round(high_risk/total*100, 1),
            "at_risk_amount":     round(fraud_amt, 0),
            "top_flags":          list(flag_counts.keys())[:3]
                                  if flag_counts else [],
            "risky_vendors":      vendor_stats[
                vendor_stats['chargeback_rate'] > 0.30
            ]['vendor_id'].tolist()
        }
        prompt = f"""
You are a Senior Fraud Risk Analyst at NilePay, an Egyptian digital payments company.

Fraud Detection Summary:
- Total Transactions Analyzed: {summary['total_transactions']:,}
- High Risk Transactions: {summary['high_risk']:,} ({summary['high_risk_pct']}%)
- At-Risk Amount: EGP {summary['at_risk_amount']:,.0f}
- Top Fraud Flags: {', '.join(summary['top_flags'])}
- High Risk Vendors: {', '.join(summary['risky_vendors'][:3]) if summary['risky_vendors'] else 'None identified'}

Write a professional Fraud Risk Report with:
1. Executive Summary
2. Key Risk Findings
3. Vendor Risk Assessment
4. Recommended Actions (5 specific steps)
5. Monitoring Priorities

Use professional risk management language.
"""
        try:
            groq_key = st.secrets.get("GROQ_API_KEY", "")
            if groq_key:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type":  "application/json",
                        "Authorization": f"Bearer {groq_key}"
                    },
                    json={
                        "model":      "llama-3.3-70b-versatile",
                        "messages":   [{"role": "user",
                                        "content": prompt}],
                        "max_tokens": 1000
                    },
                    timeout=30
                )
                result = resp.json()
                if "choices" in result:
                    st.markdown(result["choices"][0]["message"]["content"])
                else:
                    st.error("API Error — check your Groq key")
            else:
                st.warning("No API key found in secrets.toml")
        except Exception as e:
            st.error(f"Error: {e}")