import streamlit as st
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
from github import Github
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Cloud Finance (Gist)", page_icon="☁️", layout="wide")

# --- SECRETS SETUP ---
try:
    # Must add these to Streamlit Secrets!
    GH_TOKEN = st.secrets["GH_TOKEN"]
    GIST_ID = st.secrets["GIST_ID"]
except:
    st.error("⚠️ Secrets Missing! Add GH_TOKEN and GIST_ID to Streamlit Cloud Secrets.")
    st.stop()

# --- CONSTANTS ---
CATEGORY_MAPPING = {
    "Rent": "Needs", "Groceries": "Needs", "Utilities": "Needs",
    "Medicine": "Needs", "Fuel": "Needs", "EMI": "Needs",
    "Education": "Needs", "Mobile/Internet": "Needs", "House Help": "Needs",
    "Dining Out": "Wants", "Shopping": "Wants", "Entertainment": "Wants", 
    "Travel": "Wants", "Subscriptions": "Wants", "Gifts": "Wants",
    "Personal Care": "Wants",
    "Mutual Funds": "Savings", "Stocks": "Savings", "Emergency Fund": "Savings",
    "Insurance": "Savings", "Gold": "Savings", "PPF/EPF": "Savings"
}
INCOME_CATEGORIES = ["Salary", "Freelance", "Investments", "Rental", "Refunds", "Gifts", "Other"]
BROKERS = ["Zerodha", "Groww", "Paytm Money", "Upstox", "Angel One", "Coin", "Bank Direct"]

# --- GITHUB GIST FUNCTIONS ---
def get_gist_content():
    """Reads the JSON file from GitHub Gist"""
    try:
        g = Github(GH_TOKEN)
        gist = g.get_gist(GIST_ID)
        content = gist.files['finance_data.json'].content
        return json.loads(content)
    except Exception as e:
        st.error(f"Error reading Gist: {e}")
        # Return default structure if fail
        return {"transactions": [], "accounts": ["Cash"], "initial_balances": {}, "sips": [], "trading_pnl": []}

def update_gist(data):
    """Writes the updated JSON back to Gist"""
    try:
        g = Github(GH_TOKEN)
        gist = g.get_gist(GIST_ID)
        gist.edit(
            description="Updated via Finance App",
            files={'finance_data.json': from_github.InputFileContent(json.dumps(data, indent=4))}
        )
    except:
        # Fallback if InputFileContent fails (common import issue in some envs)
        try:
            g = Github(GH_TOKEN)
            gist = g.get_gist(GIST_ID)
            # Standard edit
            from github import InputFileContent
            gist.edit(files={'finance_data.json': InputFileContent(json.dumps(data, indent=4))})
        except Exception as e:
            st.error(f"Save failed: {e}")

# Load Data Once per Session
if 'data' not in st.session_state:
    st.session_state['data'] = get_gist_content()
data = st.session_state['data']

# --- PDF GEN ---
def create_pdf(df):
    try:
        from fpdf import FPDF
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 15)
                self.cell(0, 10, 'Finance Report', 0, 1, 'C')
                self.ln(10)
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        cols = ["Date", "Type", "Category", "Amount"]
        for c in cols: pdf.cell(45, 10, c, 1)
        pdf.ln()
        for i, row in df.iterrows():
            pdf.cell(45, 10, str(row['date']), 1)
            pdf.cell(45, 10, str(row['type']), 1)
            pdf.cell(45, 10, str(row.get('category', row.get('desc')))[:20], 1)
            pdf.cell(45, 10, str(row['amount']), 1)
            pdf.ln()
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- HELPER: BALANCES ---
def get_current_balances():
    balances = data.get("initial_balances", {}).copy()
    for acc in data['accounts']:
        if acc not in balances: balances[acc] = 0.0
    for t in data['transactions']:
        amt = float(t['amount'])
        if t['type'] == 'Income':
            if t.get('to_account') in balances: balances[t['to_account']] += amt
        elif t['type'] == 'Expense':
            if t.get('from_account') in balances: balances[t['from_account']] -= amt
        elif t['type'] == 'Transfer':
            if t.get('from_account') in balances: balances[t['from_account']] -= amt
            if t.get('to_account') in balances: balances[t['to_account']] += amt
        elif t['type'] == 'Investment':
            if t.get('from_account') in balances: balances[t['from_account']] -= amt
    return balances

# --- SIDEBAR ---
with st.sidebar:
    st.title("☁️ Cloud Finance")
    try:
        from streamlit_option_menu import option_menu
        menu = option_menu(
            menu_title=None,
            options=["Dashboard", "Commodity Trading", "Investments (SIP)", "Add Transaction", "Manage Accounts", "Settings"],
            icons=["graph-up-arrow", "bar-chart-line", "briefcase", "wallet2", "bank", "gear"],
            default_index=0
        )
    except:
        menu = st.radio("Menu", ["Dashboard", "Commodity Trading", "Investments (SIP)", "Add Transaction", "Manage Accounts", "Settings"])

# ==========================================
# 1. DASHBOARD
# ==========================================
if menu == "Dashboard":
    st.title("📊 Financial Overview")
    df = pd.DataFrame(data['transactions'])
    balances = get_current_balances()
    liquid_cash = sum(balances.values())
    
    if not df.empty:
        total_inc = df[df['type'] == 'Income']['amount'].sum()
        total_exp = df[df['type'] == 'Expense']['amount'].sum()
        total_inv = df[df['type'] == 'Investment']['amount'].sum()
    else:
        total_inc = total_exp = total_inv = 0
    net_worth = liquid_cash + total_inv 

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Net Worth", f"₹{net_worth:,.0f}")
    k2.metric("Liquid Cash", f"₹{liquid_cash:,.0f}")
    k3.metric("Invested", f"₹{total_inv:,.0f}")
    k4.metric("Expenses", f"₹{total_exp:,.0f}", delta_color="inverse")
    
    st.divider()
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("🏦 Accounts")
        if balances:
            bal_df = pd.DataFrame(list(balances.items()), columns=["Account", "Balance"]).sort_values("Balance", ascending=False)
            st.dataframe(bal_df, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("🎯 Budget")
        if total_inc > 0:
            exp_df = df[df['type'] == 'Expense']
            spent_map = exp_df.groupby("bucket")["amount"].sum() if not exp_df.empty else {}
            rules = {"Needs": 0.50, "Wants": 0.30, "Savings": 0.20}
            for cat, pct in rules.items():
                budget = total_inc * pct
                spent = spent_map.get(cat, 0.0)
                st.write(f"**{cat}** (Budget: ₹{budget:,.0f})")
                st.progress(min(spent/budget, 1.0) if budget > 0 else 0)
        else: st.warning("Add Income.")
    
    st.divider()
    g1, g2, g3 = st.columns(3)
    with g1:
        st.subheader("Spending")
        if total_exp > 0:
            fig = px.bar(df[df['type']=='Expense'].groupby("category")["amount"].sum().reset_index().sort_values("amount"), x="amount", y="category", orientation='h')
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.subheader("Wealth")
        if net_worth > 0:
            st.plotly_chart(px.pie(names=["Cash", "Investments"], values=[liquid_cash, total_inv], hole=0.5), use_container_width=True)
    with g3:
        st.subheader("Income")
        if total_inc > 0:
            st.plotly_chart(px.pie(df[df['type']=='Income'], values="amount", names="category", hole=0.5), use_container_width=True)

# ==========================================
# 2. COMMODITY TRADING
# ==========================================
elif menu == "Commodity Trading":
    st.title("📈 Commodity Tracker")
    t1, t2 = st.tabs(["Daily Log", "Performance"])
    with t1:
        with st.form("trade_log"):
            c1, c2, c3 = st.columns(3)
            date_log = c1.date_input("Date", datetime.now())
            pnl_type = c2.selectbox("Result", ["Profit 🟢", "Loss 🔴"])
            amount = c3.number_input("Amount", 0.0)
            notes = st.text_input("Notes")
            if st.form_submit_button("Save"):
                final_amt = amount if pnl_type == "Profit 🟢" else -amount
                st.session_state['data']['trading_pnl'].append({"date": str(date_log), "amount": final_amt, "notes": notes, "broker": "Zerodha"})
                update_gist(st.session_state['data'])
                st.success("Saved!")
                st.rerun()
        if data['trading_pnl']:
            st.dataframe(pd.DataFrame(data['trading_pnl']).sort_values("date", ascending=False), use_container_width=True)
    with t2:
        if data['trading_pnl']:
            df_trade = pd.DataFrame(data['trading_pnl'])
            df_trade['date'] = pd.to_datetime(df_trade['date'])
            df_trade = df_trade.sort_values(by='date')
            df_trade['Cumulative P&L'] = df_trade['amount'].cumsum()
            st.plotly_chart(px.line(df_trade, x='date', y='Cumulative P&L', markers=True), use_container_width=True)
            st.plotly_chart(px.bar(df_trade, x='date', y='amount', color='amount', color_continuous_scale=['red', 'green']), use_container_width=True)

# ==========================================
# 3. SIPs
# ==========================================
elif menu == "Investments (SIP)":
    st.title("🚀 SIP Manager")
    t1, t2, t3 = st.tabs(["Due", "Setup", "History"])
    with t1:
        if not data['sips']: st.warning("No SIPs.")
        else:
            cur_ym = datetime.now().strftime("%Y-%m")
            for i, sip in enumerate(data['sips']):
                is_paid = str(sip.get("last_paid", "")).startswith(cur_ym)
                with st.container():
                    c1, c2, c3, c4 = st.columns([2,1,1,1])
                    c1.markdown(f"**{sip['fund_name']}**")
                    c2.write(f"₹{sip['amount']}")
                    if is_paid: c4.success("Paid")
                    else:
                        if c4.button("Pay", key=f"pay_{i}"):
                            t = {"date": str(datetime.now().date()), "type": "Investment", "category": "Mutual Fund", "bucket": "Savings", "broker": sip['broker'], "desc": f"SIP: {sip['fund_name']}", "amount": float(sip['amount']), "from_account": sip['account']}
                            st.session_state['data']['transactions'].append(t)
                            st.session_state['data']['sips'][i]['last_paid'] = str(datetime.now().date())
                            update_gist(st.session_state['data'])
                            st.success("Invested!")
                            st.rerun()
                    st.divider()
    with t2:
        with st.form("sip_add"):
            c1, c2 = st.columns(2)
            brk = c1.selectbox("Broker", BROKERS)
            fund = c2.text_input("Fund")
            c3, c4 = st.columns(2)
            amt = c3.number_input("Amount", 500.0)
            day = c4.slider("Day", 1, 31, 5)
            acc = st.selectbox("From", data['accounts'])
            if st.form_submit_button("Save"):
                st.session_state['data']['sips'].append({"broker": brk, "fund_name": fund, "amount": amt, "day": day, "account": acc, "last_paid": ""})
                update_gist(st.session_state['data'])
                st.rerun()
    with t3:
        df = pd.DataFrame(data['transactions'])
        if not df.empty: st.dataframe(df[df['type']=='Investment'], use_container_width=True)

# ==========================================
# 4. ADD TRANSACTION
# ==========================================
elif menu == "Add Transaction":
    st.title("💳 New Transaction")
    t1, t2, t3 = st.tabs(["Expense", "Income", "Transfer"])
    with t1:
        with st.form("exp"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Category", sorted(CATEGORY_MAPPING.keys()))
            acc = c2.selectbox("Account", data['accounts'])
            amt = st.number_input("Amount", 1.0)
            desc = st.text_input("Desc")
            if st.form_submit_button("Save"):
                t = {"date": str(datetime.now().date()), "type": "Expense", "category": cat, "bucket": CATEGORY_MAPPING[cat], "amount": amt, "from_account": acc, "desc": desc}
                st.session_state['data']['transactions'].append(t)
                update_gist(st.session_state['data'])
                st.success("Saved!")
    with t2:
        with st.form("inc"):
            src = st.selectbox("Source", INCOME_CATEGORIES)
            acc = st.selectbox("To", data['accounts'])
            amt = st.number_input("Amount", 1.0)
            if st.form_submit_button("Save"):
                t = {"date": str(datetime.now().date()), "type": "Income", "category": src, "amount": amt, "to_account": acc, "desc": src}
                st.session_state['data']['transactions'].append(t)
                update_gist(st.session_state['data'])
                st.success("Saved!")
    with t3:
        with st.form("trf"):
            c1, c2 = st.columns(2)
            f = c1.selectbox("From", data['accounts'], key="f")
            t_acc = c2.selectbox("To", data['accounts'], key="t")
            amt = st.number_input("Amount", 1.0)
            if st.form_submit_button("Transfer"):
                t = {"date": str(datetime.now().date()), "type": "Transfer", "amount": amt, "from_account": f, "to_account": t_acc, "desc": "Transfer"}
                st.session_state['data']['transactions'].append(t)
                update_gist(st.session_state['data'])
                st.success("Done!")

# ==========================================
# 5. MANAGE ACCOUNTS
# ==========================================
elif menu == "Manage Accounts":
    st.title("🏦 Accounts")
    t1, t2 = st.tabs(["Add", "Balances"])
    with t1:
        new = st.text_input("New Account")
        if st.button("Add"):
            if new not in data['accounts']:
                st.session_state['data']['accounts'].append(new)
                update_gist(st.session_state['data'])
                st.rerun()
    with t2:
        with st.form("bal"):
            updates = {}
            for acc in data['accounts']:
                curr = data.get("initial_balances", {}).get(acc, 0.0)
                updates[acc] = st.number_input(f"{acc}", value=float(curr))
            if st.form_submit_button("Update"):
                st.session_state['data']['initial_balances'] = updates
                update_gist(st.session_state['data'])
                st.success("Updated!")

# ==========================================
# 6. SETTINGS
# ==========================================
elif menu == "Settings":
    st.title("⚙️ Settings")
    if st.button("Reload from Cloud"):
        st.session_state['data'] = get_gist_content()
        st.success("Reloaded!")
    if data['transactions']:
        df = pd.DataFrame(data['transactions'])
        c1, c2 = st.columns(2)
        with c1: st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8'), "data.csv")
        with c2: 
            pdf = create_pdf(df)
            if pdf: st.download_button("📥 PDF", pdf, "report.pdf")
