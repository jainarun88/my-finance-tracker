import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Ultimate Finance Pro", page_icon="💎", layout="wide")
FILE_NAME = "finance_data.json"

# --- CONSTANTS ---
CATEGORY_MAPPING = {
    # Needs
    "Rent": "Needs", "Groceries": "Needs", "Utilities": "Needs",
    "Medicine": "Needs", "Fuel": "Needs", "EMI": "Needs",
    "Education": "Needs", "Mobile/Internet": "Needs", "House Help": "Needs",
    # Wants
    "Dining Out": "Wants", "Shopping": "Wants", "Entertainment": "Wants", 
    "Travel": "Wants", "Subscriptions": "Wants", "Gifts": "Wants",
    "Personal Care": "Wants",
    # Savings
    "Mutual Funds": "Savings", "Stocks": "Savings", "Emergency Fund": "Savings",
    "Insurance": "Savings", "Gold": "Savings", "PPF/EPF": "Savings"
}

INCOME_CATEGORIES = ["Salary", "Freelance", "Investments", "Rental", "Refunds", "Gifts", "Other"]
BROKERS = ["Zerodha", "Groww", "Paytm Money", "Upstox", "Angel One", "Coin", "Bank Direct"]

# --- DATA LOADING ---
def load_data():
    default = {
        "transactions": [],
        "accounts": ["HDFC", "SBI", "Credit Card", "Cash"],
        "initial_balances": {}, 
        "sips": [],
        "trading_pnl": [] 
    }
    
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, 'r') as f:
                loaded = json.load(f)
            for key, val in default.items():
                if key not in loaded:
                    loaded[key] = val
            return loaded
        except:
            return default
    return default

def save_data(data):
    with open(FILE_NAME, 'w') as f:
        json.dump(data, f, indent=4)

# Load Data
data = load_data()

# --- HELPER: CALCULATE BALANCES ---
def get_current_balances():
    balances = data.get("initial_balances", {}).copy()
    for acc in data['accounts']:
        if acc not in balances: balances[acc] = 0.0
            
    for t in data['transactions']:
        amt = float(t['amount'])
        if t['type'] == 'Income':
            if t['to_account'] in balances: balances[t['to_account']] += amt
        elif t['type'] == 'Expense':
            if t['from_account'] in balances: balances[t['from_account']] -= amt
        elif t['type'] == 'Transfer':
            if t['from_account'] in balances: balances[t['from_account']] -= amt
            if t['to_account'] in balances: balances[t['to_account']] += amt
        elif t['type'] == 'Investment':
            if t['from_account'] in balances: balances[t['from_account']] -= amt
            
    return balances

# --- PDF GENERATOR ---
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

# --- SIDEBAR MENU ---
with st.sidebar:
    st.title("💎 Ultimate Pro")
    try:
        from streamlit_option_menu import option_menu
        menu = option_menu(
            menu_title=None,
            options=["Dashboard", "Commodity Trading", "Investments (SIP)", "Add Transaction", "Manage Accounts", "Settings"],
            icons=["graph-up-arrow", "bar-chart-line", "briefcase", "wallet2", "bank", "gear"],
            default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#ff4b4b"}}
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
    k1.metric("💰 Net Worth", f"₹{net_worth:,.0f}", delta="Total")
    k2.metric("Liquid Cash", f"₹{liquid_cash:,.0f}", delta="Bank")
    k3.metric("Invested", f"₹{total_inv:,.0f}", delta="SIPs")
    k4.metric("Expenses", f"₹{total_exp:,.0f}", delta_color="inverse")
    
    st.divider()
    
    # --- ROW 1: ACCOUNT & BUDGET ---
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("🏦 Account Status")
        if balances:
            bal_df = pd.DataFrame(list(balances.items()), columns=["Account", "Balance"]).sort_values("Balance", ascending=False)
            st.dataframe(bal_df, use_container_width=True, hide_index=True, column_config={"Balance": st.column_config.NumberColumn(format="₹%d")})
        else: st.info("No accounts.")

    with c2:
        st.subheader("🎯 50-30-20 Budget")
        if total_inc > 0:
            exp_df = df[df['type'] == 'Expense']
            spent_map = exp_df.groupby("bucket")["amount"].sum() if not exp_df.empty else {}
            rules = {"Needs": 0.50, "Wants": 0.30, "Savings": 0.20}
            for cat, pct in rules.items():
                budget = total_inc * pct
                spent = spent_map.get(cat, 0.0)
                left = budget - spent
                st.write(f"**{cat}** (Budget: ₹{budget:,.0f})")
                if left < 0:
                    st.progress(1.0)
                    st.caption(f"⚠️ Over by ₹{abs(left):,.0f}")
                else:
                    st.progress(min(spent/budget, 1.0))
                    st.caption(f"✅ Left: ₹{left:,.0f}")
        else: st.warning("Add Income to see budget.")

    st.divider()
    
    # --- ROW 2: GRAPHS ---
    g1, g2, g3 = st.columns(3)
    
    with g1:
        st.subheader("Spending Analysis")
        if total_exp > 0:
            exp_df = df[df['type'] == 'Expense']
            fig = px.bar(exp_df.groupby("category")["amount"].sum().reset_index().sort_values("amount"), x="amount", y="category", orientation='h', text_auto='.2s')
            st.plotly_chart(fig, use_container_width=True)
            
    with g2:
        st.subheader("Wealth Split")
        if net_worth > 0:
            fig = px.pie(pd.DataFrame({"Asset": ["Cash", "Investments"], "Amount": [liquid_cash, total_inv]}), values="Amount", names="Asset", hole=0.5, color_discrete_sequence=["#00CC96", "#636EFA"])
            st.plotly_chart(fig, use_container_width=True)

    with g3:
        st.subheader("Income Sources")
        if total_inc > 0:
            inc_df = df[df['type'] == 'Income']
            fig = px.pie(inc_df, values="amount", names="category", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 2. COMMODITY TRADING
# ==========================================
elif menu == "Commodity Trading":
    st.title("📈 Commodity Tracker (Zerodha)")
    t1, t2 = st.tabs(["📝 Daily Log", "📊 Performance"])
    
    with t1:
        with st.form("trade_log"):
            c1, c2, c3 = st.columns(3)
            date_log = c1.date_input("Date", datetime.now())
            pnl_type = c2.selectbox("Result", ["Profit 🟢", "Loss 🔴"])
            amount = c3.number_input("Amount (₹)", min_value=0.0)
            notes = st.text_input("Notes")
            
            if st.form_submit_button("Save P&L"):
                final_amt = amount if pnl_type == "Profit 🟢" else -amount
                data['trading_pnl'].append({"date": str(date_log), "amount": final_amt, "notes": notes, "broker": "Zerodha"})
                save_data(data)
                st.success("Saved!")
                st.rerun()

        st.subheader("Log History")
        if data['trading_pnl']:
            trade_df = pd.DataFrame(data['trading_pnl'])
            trade_df['date'] = pd.to_datetime(trade_df['date'])
            trade_df = trade_df.sort_values(by='date', ascending=False)
            st.dataframe(trade_df, use_container_width=True, column_config={"amount": st.column_config.NumberColumn("Net P&L", format="₹%d")})

    with t2:
        if data['trading_pnl']:
            df_trade = pd.DataFrame(data['trading_pnl'])
            df_trade['date'] = pd.to_datetime(df_trade['date'])
            df_trade = df_trade.sort_values(by='date')
            df_trade['Cumulative P&L'] = df_trade['amount'].cumsum()
            
            # Line Chart
            st.subheader("Growth Curve")
            fig = px.line(df_trade, x='date', y='Cumulative P&L', markers=True)
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
            
            # Bar Chart (Volatility) - ADDED BACK
            st.subheader("Daily Volatility")
            fig2 = px.bar(df_trade, x='date', y='amount', color='amount', color_continuous_scale=['red', 'green'])
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Add logs to see graphs.")

# ==========================================
# 3. INVESTMENTS (SIP)
# ==========================================
elif menu == "Investments (SIP)":
    st.title("🚀 SIP Manager")
    t1, t2, t3 = st.tabs(["⚡ Due SIPs", "⚙️ Setup", "📜 History"])
    
    with t1:
        st.subheader("Monthly Status")
        if not data['sips']:
            st.warning("No SIPs set up.")
        else:
            current_month = datetime.now().strftime("%Y-%m")
            for i, sip in enumerate(data['sips']):
                last_paid = sip.get("last_paid", "")
                is_paid = last_paid.startswith(current_month)
                with st.container():
                    c1, c2, c3, c4 = st.columns([2,1,1,1])
                    c1.markdown(f"**{sip['fund_name']}** ({sip['broker']})")
                    c2.write(f"₹{sip['amount']:,}")
                    c3.write(f"Day: {sip['day']}")
                    if is_paid: c4.success("✅ Paid")
                    else:
                        if c4.button("Pay Now", key=f"pay_{i}"):
                            t = {"date": str(datetime.now().date()), "type": "Investment",
                                 "category": "Mutual Fund", "bucket": "Savings",
                                 "broker": sip['broker'], "desc": f"SIP: {sip['fund_name']}",
                                 "amount": float(sip['amount']), "from_account": sip['account']}
                            data['transactions'].append(t)
                            data['sips'][i]['last_paid'] = str(datetime.now().date())
                            save_data(data)
                            st.rerun()
                    st.divider()

    with t2:
        with st.form("sip_add"):
            c1, c2 = st.columns(2)
            brk = c1.selectbox("Broker", BROKERS)
            fund = c2.text_input("Fund Name")
            c3, c4 = st.columns(2)
            amt = c3.number_input("Amount", min_value=500.0)
            day = c4.slider("Date", 1, 31, 5)
            acc = st.selectbox("Deduct From", data['accounts'])
            if st.form_submit_button("Save SIP"):
                data['sips'].append({"broker": brk, "fund_name": fund, "amount": amt, "day": day, "account": acc, "last_paid": ""})
                save_data(data)
                st.success("Saved!")
                st.rerun()
        if data['sips']:
            opts = [f"{s['fund_name']} - {s['amount']}" for s in data['sips']]
            d = st.selectbox("Delete SIP", opts)
            if st.button("Delete Selected"):
                idx = opts.index(d)
                data['sips'].pop(idx)
                save_data(data)
                st.rerun()

    with t3:
        inv_df = pd.DataFrame(data['transactions'])
        if not inv_df.empty:
            inv_df = inv_df[inv_df['type'] == 'Investment']
            if not inv_df.empty: st.dataframe(inv_df[['date', 'broker', 'desc', 'amount']], use_container_width=True)

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
            amt = st.number_input("Amount", min_value=1.0)
            desc = st.text_input("Desc")
            if st.form_submit_button("Save"):
                t = {"date": str(datetime.now().date()), "type": "Expense", 
                     "category": cat, "bucket": CATEGORY_MAPPING[cat], "amount": amt, 
                     "from_account": acc, "desc": desc if desc else cat}
                data['transactions'].append(t)
                save_data(data)
                st.success("Saved!")
    with t2:
        with st.form("inc"):
            src = st.selectbox("Source", INCOME_CATEGORIES)
            acc = st.selectbox("To", data['accounts'])
            amt = st.number_input("Amount", min_value=1.0)
            if st.form_submit_button("Save"):
                t = {"date": str(datetime.now().date()), "type": "Income", 
                     "category": src, "amount": amt, "to_account": acc, "desc": src}
                data['transactions'].append(t)
                save_data(data)
                st.success("Saved!")
    with t3:
        with st.form("trf"):
            c1, c2 = st.columns(2)
            f = c1.selectbox("From", data['accounts'], key="f")
            t = c2.selectbox("To", data['accounts'], key="t")
            amt = st.number_input("Amount", min_value=1.0)
            if st.form_submit_button("Transfer"):
                tr = {"date": str(datetime.now().date()), "type": "Transfer", 
                     "amount": amt, "from_account": f, "to_account": t, "desc": "Transfer"}
                data['transactions'].append(tr)
                save_data(data)
                st.success("Done!")

# ==========================================
# 5. MANAGE ACCOUNTS
# ==========================================
elif menu == "Manage Accounts":
    st.title("🏦 Account Settings")
    t1, t2 = st.tabs(["Add/Remove", "Opening Balances"])
    with t1:
        st.write("Current:", ", ".join(data['accounts']))
        new = st.text_input("New Account")
        if st.button("Add"):
            if new and new not in data['accounts']:
                data['accounts'].append(new)
                save_data(data)
                st.rerun()
    with t2:
        st.info("Set the money you already have in these accounts.")
        with st.form("bal"):
            updates = {}
            for acc in data['accounts']:
                curr = data.get("initial_balances", {}).get(acc, 0.0)
                updates[acc] = st.number_input(f"{acc}", value=float(curr))
            if st.form_submit_button("Update Balances"):
                data["initial_balances"] = updates
                save_data(data)
                st.success("Updated!")

# ==========================================
# 6. SETTINGS
# ==========================================
elif menu == "Settings":
    st.title("⚙️ Data & Export")
    if data['transactions']:
        df = pd.DataFrame(data['transactions'])
        c1, c2, c3 = st.columns(3)
        with c1:
            try:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Excel", buffer.getvalue(), "data.xlsx")
            except: st.error("Pip install openpyxl")
        with c2:
            st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8'), "data.csv")
        with c3:
            pdf = create_pdf(df)
            if pdf: st.download_button("📥 PDF", pdf, "report.pdf")
            else: st.error("Pip install fpdf")
