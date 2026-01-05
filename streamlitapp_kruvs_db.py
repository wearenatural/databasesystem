import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Aethera Naturals Manager", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Google Sheets Connection ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gsheet_connection():
    """Establishes connection to Google Sheets using Streamlit Secrets."""
    try:
        # Load credentials from Streamlit secrets (Only for API access, not app users)
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet_url = st.secrets["sheets"]["spreadsheet_url"]
        spreadsheet = client.open_by_url(sheet_url)
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.stop()

def get_or_create_worksheet(spreadsheet, title, headers):
    """Gets a worksheet or creates it if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet(title)
        return ws
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=20)
        ws.append_row(headers)
        return ws

# --- User Authentication (From Sheet) ---
def fetch_users_from_sheet():
    """Fetches valid users and passwords from the 'Users' tab in Google Sheets."""
    sh = get_gsheet_connection()
    
    # Check for Users sheet
    try:
        ws = sh.worksheet("Users")
    except gspread.WorksheetNotFound:
        # Create if missing and add default admin
        ws = sh.add_worksheet(title="Users", rows=100, cols=5)
        ws.append_row(["Username", "Password"])
        # ws.append_row(["admin", "admin123"]) # Default fallback
    
    records = ws.get_all_records()
    
    # Convert to dictionary {username: password}
    user_db = {}
    for row in records:
        if row.get("Username") and row.get("Password"):
            # Store usernames in lowercase for case-insensitive login
            user_db[str(row["Username"]).strip().lower()] = str(row["Password"]).strip()
            
    if not user_db:
        # Fallback if list is empty but sheet exists
        return {"admin": "admin123"}
        
    return user_db

# --- Data Loading (From Sheets) ---
def load_data():
    sh = get_gsheet_connection()
    
    # 1. Inventory
    inv_headers = ["Variant", "Size", "Stock", "Default_Price", "Last_Updated"]
    ws_inv = get_or_create_worksheet(sh, "Inventory", inv_headers)
    inv_data = ws_inv.get_all_records()
    inventory_df = pd.DataFrame(inv_data)
    if inventory_df.empty:
        inventory_df = pd.DataFrame(columns=inv_headers)

    # 2. Sales
    sales_headers = [
        "Date_of_Sale", "Seller_Name", "Sales_Channel", "Customer_Name", 
        "Contact_Number", "City_Location", "Customer_Type", "Shampoo_Variant", 
        "Bottle_Size", "Quantity_Sold", "Unit_Selling_Price", "Total_Sale_Amount", 
        "Payment_Method", "Payment_Status", "Delivery_Mode", "Shipping_Cost"
    ]
    ws_sales = get_or_create_worksheet(sh, "Sales", sales_headers)
    sales_data = ws_sales.get_all_records()
    sales_df = pd.DataFrame(sales_data)
    if sales_df.empty:
        sales_df = pd.DataFrame(columns=sales_headers)

    # 3. History
    hist_headers = ["Timestamp", "Date", "User", "Variant", "Size", "Action", "Qty_Change", "Stock_Before", "Stock_After", "Notes"]
    ws_hist = get_or_create_worksheet(sh, "History", hist_headers)
    hist_data = ws_hist.get_all_records()
    history_df = pd.DataFrame(hist_data)
    if history_df.empty:
        history_df = pd.DataFrame(columns=hist_headers)
        
    return sales_df, inventory_df, history_df

# --- Data Saving (To Sheets) ---
def update_inventory_sheet(df):
    """Rewrites the inventory sheet."""
    sh = get_gsheet_connection()
    ws = sh.worksheet("Inventory")
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

def append_sale_sheet(row_dict):
    """Appends a single row to Sales sheet."""
    sh = get_gsheet_connection()
    ws = sh.worksheet("Sales")
    ws.append_row(list(row_dict.values()))

def append_history_sheet(row_dict):
    """Appends a single row to History sheet."""
    sh = get_gsheet_connection()
    ws = sh.worksheet("History")
    ws.append_row(list(row_dict.values()))


# --- PREMIUM STYLING (CSS) ---
st.markdown("""
    <style>
    /* 1. MAIN BACKGROUND & SCROLLBAR */
    .stApp {
        background: linear-gradient(to bottom right, #0a0c10, #161b22);
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0d1117; 
    }
    ::-webkit-scrollbar-thumb {
        background: #30363d; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #58a6ff; 
    }

    /* 2. SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] h1 {
        background: linear-gradient(90deg, #2dd4bf, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        margin-bottom: 0;
    }
    
    /* 3. CARD CONTAINERS (Glassmorphism) */
    .stContainer, div[data-testid="stExpander"] {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(48, 54, 61, 0.6);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.5rem;
    }
    
    /* 4. METRIC CARDS (Hover Effects) */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(33, 38, 45, 0.8), rgba(22, 27, 34, 0.9));
        border: 1px solid rgba(56, 139, 253, 0.15);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        border-color: #3b82f6; /* Blue Glow */
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* 5. INPUT FIELDS & DROPDOWNS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #0d1117;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 6px;
        height: 45px;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 1px #3b82f6;
    }
    
    /* 6. BUTTONS */
    div.stButton > button {
        background: linear-gradient(90deg, #238636, #2ea043);
        color: white;
        border: 1px solid rgba(240, 246, 252, 0.1);
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #2ea043, #3fb950);
        box-shadow: 0 0 12px rgba(46, 160, 67, 0.4);
        transform: scale(1.02);
    }
    
    /* 7. LOGIN SPECIFIC */
    .login-box {
        background: rgba(13, 17, 23, 0.95);
        border: 1px solid #30363d;
        border-top: 4px solid #3b82f6;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }
    
    /* 8. HEADERS */
    h2, h3 {
        color: #e6edf3 !important;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    hr {
        border-color: #30363d;
    }
    </style>
""", unsafe_allow_html=True)

# --- Initialization ---
if 'sales_data' not in st.session_state:
    with st.spinner("Connecting to Secure Cloud Database..."):
        try:
            st.session_state.sales_data, st.session_state.inventory, st.session_state.history = load_data()
        except Exception as e:
            st.error("⚠️ Failed to load data. Please check your internet or API Quota.")
            st.stop()

if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- Logic Functions ---
def log_stock_movement(variant, size, action, qty_change, stock_before, stock_after, user, notes=""):
    new_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "User": str(user),
        "Variant": str(variant),
        "Size": str(size),
        "Action": str(action),
        "Qty_Change": int(qty_change),
        "Stock_Before": int(stock_before),
        "Stock_After": int(stock_after),
        "Notes": str(notes)
    }
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_entry])], ignore_index=True)
    append_history_sheet(new_entry)

def add_stock(variant, size, qty, price, user):
    df = st.session_state.inventory
    match = df[(df['Variant'] == variant) & (df['Size'] == size)]
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if not match.empty:
        idx = match.index[0]
        prev_stock = int(st.session_state.inventory.at[idx, 'Stock'])
        
        st.session_state.inventory.at[idx, 'Stock'] = prev_stock + qty
        st.session_state.inventory.at[idx, 'Default_Price'] = price
        st.session_state.inventory.at[idx, 'Last_Updated'] = current_date
        
        new_stock = int(st.session_state.inventory.at[idx, 'Stock'])
        log_stock_movement(variant, size, "Restock", qty, prev_stock, new_stock, user, f"Price: {price}")
        msg = f"Restocked {variant}: {prev_stock} ➝ {new_stock} units."
    else:
        new_row = {
            "Variant": variant, "Size": size, "Stock": qty, 
            "Default_Price": price, "Last_Updated": current_date
        }
        st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_row])], ignore_index=True)
        log_stock_movement(variant, size, "New Product", qty, 0, qty, user, f"Init Price: {price}")
        msg = f"Created {variant} ({size}) with {qty} units."
    
    update_inventory_sheet(st.session_state.inventory)
    return msg

def deduct_stock(variant, size, qty, customer="Unknown", user="Sales_Terminal"):
    df = st.session_state.inventory
    match = df[(df['Variant'] == variant) & (df['Size'] == size)]
    
    if not match.empty:
        idx = match.index[0]
        current_stock = int(st.session_state.inventory.at[idx, 'Stock'])
        
        if current_stock >= qty:
            st.session_state.inventory.at[idx, 'Stock'] = current_stock - qty
            new_stock = int(st.session_state.inventory.at[idx, 'Stock'])
            
            log_stock_movement(variant, size, "Sale", -qty, current_stock, new_stock, user, f"Cust: {customer}")
            update_inventory_sheet(st.session_state.inventory)
            return True
    return False

# ==========================================
# AUTHENTICATION GATEWAY
# ==========================================
if st.session_state.logged_in_user is None:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Login Box with New Styling
        st.markdown("""
        <div class="login-box">
            <h1 style="font-size: 2.5rem; margin-bottom: 5px;">🌿 Aethera Naturals</h1>
            <p style="color: #8b949e; margin-top: 0;">Authorized Access Only</p>
            <hr style="opacity: 0.2; margin: 25px 0;">
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your ID").lower().strip()
            password = st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Launch Portal", type="primary", use_container_width=True):
                # Dynamically fetch users from Google Sheets
                valid_users = fetch_users_from_sheet()
                
                if username in valid_users and valid_users[username] == password:
                    st.session_state.logged_in_user = username
                    st.success("Access Granted.")
                    st.rerun()
                else:
                    st.error("Access Denied.")

else:
    # ==========================================
    # MAIN APP
    # ==========================================
    with st.sidebar:
        st.title("🌿 Aethera")
        st.caption("Cloud Command Center")
        st.divider()
        menu = st.radio("System Navigation", ["Dashboard", "New Sale", "Smart Inventory", "Sales History"])
        st.divider()
        st.success(f"🟢 {st.session_state.logged_in_user.title()}")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in_user = None
            st.rerun()

    # --- PAGE 1: DASHBOARD ---
    if menu == "Dashboard":
        st.markdown("## 🚀 Business Intelligence")
        st.markdown("Real-time overview of your operations.")
        st.markdown("<br>", unsafe_allow_html=True)

        df = st.session_state.sales_data
        inv = st.session_state.inventory
        
        # 1. KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        total_rev = pd.to_numeric(df['Total_Sale_Amount'], errors='coerce').sum() if not df.empty else 0
        ah_stock = 0
        total_val = 0
        if not inv.empty:
            inv['Stock'] = pd.to_numeric(inv['Stock'], errors='coerce').fillna(0)
            inv['Default_Price'] = pd.to_numeric(inv['Default_Price'], errors='coerce').fillna(0)
            ah_stock = inv[inv['Variant'].str.contains("Anti-Hairfall", case=False, na=False)]['Stock'].sum()
            total_val = (inv['Stock'] * inv['Default_Price']).sum()
        
        avg_ah_price = 0
        if not df.empty:
            df['Unit_Selling_Price'] = pd.to_numeric(df['Unit_Selling_Price'], errors='coerce').fillna(0)
            ah_sales = df[df['Shampoo_Variant'].str.contains("Anti-Hairfall", case=False, na=False)]
            if not ah_sales.empty:
                avg_ah_price = ah_sales['Unit_Selling_Price'].mean()
        
        kpi1.metric("Total Revenue", f"₹{total_rev:,.0f}", delta="Lifetime")
        kpi2.metric("Anti-Hairfall Stock", f"{ah_stock} Units")
        kpi3.metric("Avg Price (AH)", f"₹{avg_ah_price:,.2f}")
        kpi4.metric("Inventory Value", f"₹{total_val:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not df.empty:
            # 2. Charts (2x2 Grid)
            r1c1, r1c2 = st.columns(2)
            
            with r1c1:
                with st.container():
                    st.markdown("### 📈 Revenue by Status")
                    chart = alt.Chart(df).mark_bar(cornerRadius=6).encode(
                        x=alt.X('Payment_Status', title='Status', axis=alt.Axis(labelColor='#8b949e', titleColor='#8b949e')),
                        y=alt.Y('sum(Total_Sale_Amount)', title='Revenue', axis=alt.Axis(labelColor='#8b949e', titleColor='#8b949e')),
                        color=alt.Color('Payment_Status', scale=alt.Scale(scheme='tealblues'), legend=None),
                        tooltip=['Payment_Status', 'sum(Total_Sale_Amount)']
                    ).properties(height=280).configure_view(strokeWidth=0).configure_axis(gridColor='#30363d')
                    st.altair_chart(chart, use_container_width=True)
            
            with r1c2:
                with st.container():
                    st.markdown("### 📱 Sales Channels")
                    channel_chart = alt.Chart(df).mark_bar(cornerRadius=6).encode(
                        x=alt.X('Sales_Channel', title='Channel', axis=alt.Axis(labelColor='#8b949e', titleColor='#8b949e')),
                        y=alt.Y('count()', title='Orders', axis=alt.Axis(labelColor='#8b949e', titleColor='#8b949e')),
                        color=alt.Color('Sales_Channel', scale=alt.Scale(scheme='category20b'), legend=None),
                        tooltip=['Sales_Channel', 'count()', 'sum(Total_Sale_Amount)']
                    ).properties(height=280).configure_view(strokeWidth=0).configure_axis(gridColor='#30363d')
                    st.altair_chart(channel_chart, use_container_width=True)

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                with st.container():
                    st.markdown("### 👥 New vs Recurring")
                    pie = alt.Chart(df).mark_arc(innerRadius=60, stroke="#161b22").encode(
                        theta=alt.Theta("count()", stack=True),
                        color=alt.Color("Customer_Type", scale=alt.Scale(scheme='viridis')),
                        tooltip=["Customer_Type", "count()"]
                    ).properties(height=280).configure_view(strokeWidth=0)
                    st.altair_chart(pie, use_container_width=True)
            
            with r2c2:
                with st.container():
                    st.markdown("### 💳 Payment Methods")
                    pm_chart = alt.Chart(df).mark_arc(innerRadius=60, stroke="#161b22").encode(
                        theta=alt.Theta("count()", stack=True),
                        color=alt.Color("Payment_Method", scale=alt.Scale(scheme='magma')),
                        tooltip=["Payment_Method", "count()", "sum(Total_Sale_Amount)"]
                    ).properties(height=280).configure_view(strokeWidth=0)
                    st.altair_chart(pm_chart, use_container_width=True)
        else:
            st.info("Start recording sales to visualize data.")

    # --- PAGE 2: NEW SALE ---
    elif menu == "New Sale":
        st.markdown("## ✨ New Transaction")
        st.markdown("Log a new sale into the system.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.inventory.empty:
            st.warning("Inventory is empty.")
            st.stop()

        with st.container():
            st.subheader("👤 Customer Details")
            c1, c2, c3 = st.columns(3)
            date_of_sale = c1.date_input("Date", datetime.now())
            
            current_user = st.session_state.logged_in_user
            # Fetch actual users from sheet for dropdown
            users_dict = fetch_users_from_sheet()
            user_list = list(users_dict.keys())
            if current_user in user_list:
                user_list.remove(current_user)
                user_list.insert(0, current_user)
            
            seller_name = c2.selectbox("Seller", user_list)
            sales_channel = c3.selectbox("Channel", ["WhatsApp", "Instagram", "Personal","event/stall", "Reference","B2B"])
            
            c4, c5 = st.columns(2)
            cust_name = c4.text_input("Customer Name", placeholder="Enter full name")
            contact = c5.text_input("Contact", placeholder="Mobile number")
            c6, c7 = st.columns(2)
            city = c6.text_input("City", placeholder="Location")
            cust_type = c7.radio("Type", ["New", "Recurring"], horizontal=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container():
            st.subheader("🛒 Product Selection")
            inv_df = st.session_state.inventory
            inv_df['Display'] = inv_df['Variant'].astype(str) + " (" + inv_df['Size'].astype(str) + ")"
            
            pc1, pc2 = st.columns([2, 1])
            selected_display = pc1.selectbox("Choose Product", inv_df['Display'].unique())
            item = inv_df[inv_df['Display'] == selected_display].iloc[0]
            current_stock_val = int(item['Stock'])
            
            stock_color = "#ef4444" if current_stock_val < 10 else "#238636"
            pc2.markdown(f"""
                <div style="background: rgba(13,17,23,0.5); border:1px solid {stock_color}; padding:12px; border-radius:8px; text-align:center; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                    <small style="color:#8b949e; text-transform: uppercase;">Available Stock</small><br>
                    <strong style="color:{stock_color}; font-size:28px; font-family: monospace;">{current_stock_val}</strong>
                </div>
            """, unsafe_allow_html=True)

            if current_stock_val > 0:
                qc1, qc2, qc3 = st.columns(3)
                qty_sold = qc1.number_input("Quantity", min_value=1, max_value=current_stock_val, value=1)
                unit_price = qc2.number_input("Unit Price (₹)", value=float(item['Default_Price']))
                total_amt = qty_sold * unit_price
                qc3.metric("Total Amount", f"₹{total_amt:,.2f}")
            else:
                st.error("🚫 Out of Stock!")

        st.markdown("<br>", unsafe_allow_html=True)

        if current_stock_val > 0:
            with st.container():
                st.subheader("🚚 Payment & Delivery")
                lc1, lc2, lc3, lc4 = st.columns(4)
                pay_method = lc1.selectbox("Method", ["UPI", "Cash"])
                pay_status = lc2.selectbox("Status", ["Paid", "Pending", "Credit"])
                del_mode = lc3.selectbox("Delivery", ["Hand Delivery", "Courier"])
                ship_cost = lc4.number_input("Shipping Cost", value=0.0)

            if st.button("✅ Confirm Order & Sync", type="primary", use_container_width=True):
                if not cust_name:
                    st.error("Customer Name Required")
                else:
                    with st.spinner("Syncing to Cloud..."):
                        date_str = date_of_sale.strftime("%Y-%m-%d")
                        if deduct_stock(item['Variant'], item['Size'], qty_sold, cust_name, user=seller_name):
                            new_sale = {
                                "Date_of_Sale": date_str, "Seller_Name": seller_name, "Sales_Channel": sales_channel,
                                "Customer_Name": cust_name, "Contact_Number": contact, "City_Location": city,
                                "Customer_Type": cust_type, "Shampoo_Variant": item['Variant'], "Bottle_Size": item['Size'],
                                "Quantity_Sold": int(qty_sold),
                                "Unit_Selling_Price": float(unit_price),
                                "Total_Sale_Amount": float(total_amt),
                                "Payment_Method": pay_method, "Payment_Status": pay_status,
                                "Delivery_Mode": del_mode, "Shipping_Cost": float(ship_cost)
                            }
                            st.session_state.sales_data = pd.concat([st.session_state.sales_data, pd.DataFrame([new_sale])], ignore_index=True)
                            append_sale_sheet(new_sale)
                            st.balloons()
                            st.success("Sale Recorded & Synced Successfully!")
                        else:
                            st.error("Stock update failed.")

    # --- PAGE 3: SMART INVENTORY ---
    elif menu == "Smart Inventory":
        st.markdown("## 📦 Inventory Control")
        st.markdown("Manage stock levels and track changes.")
        
        tab1, tab2, tab3 = st.tabs(["📊 Live Stock", "➕ Restock / Edit", "📜 Audit Logs"])
        
        with tab1:
            if st.session_state.inventory.empty:
                st.info("Inventory Empty")
            else:
                def stock_style(val):
                    color = '#f85149' if val < 10 else '#3fb950'
                    return f'color: {color}; font-weight: bold;'
                
                df_view = st.session_state.inventory.copy()
                df_view['Stock'] = pd.to_numeric(df_view['Stock'], errors='coerce').fillna(0)
                
                st.dataframe(
                    df_view[['Variant', 'Size', 'Stock', 'Default_Price', 'Last_Updated']].style.map(stock_style, subset=['Stock']),
                    use_container_width=True,
                    height=500
                )

        with tab2:
            with st.container():
                st.info(f"You are modifying inventory as: **{st.session_state.logged_in_user}**")
                mode = st.radio("Operation Mode", ["Restock Existing Item", "Create New Product"], horizontal=True)
                st.markdown("<hr>", unsafe_allow_html=True)
                
                with st.form("inv_form", clear_on_submit=True):
                    if mode == "Restock Existing Item":
                        if st.session_state.inventory.empty:
                            st.warning("No items.")
                            st.stop()
                        inv = st.session_state.inventory
                        inv['Label'] = inv['Variant'].astype(str) + " (" + inv['Size'].astype(str) + ")"
                        sel = st.selectbox("Select Item", inv['Label'].unique())
                        curr = inv[inv['Label'] == sel].iloc[0]
                        c1, c2 = st.columns(2)
                        c1.metric("Current Stock", curr['Stock'])
                        c2.metric("Current Price", f"₹{curr['Default_Price']}")
                        variant = curr['Variant']
                        size = curr['Size']
                        qty = st.number_input("Add Quantity (Use negative to remove)", value=10)
                        price = st.number_input("Update Price", value=float(curr['Default_Price']))
                    else:
                        variant = st.text_input("Variant Name", placeholder="e.g. Aloe Vera Shampoo")
                        size = st.selectbox("Size", ["100ml", "200ml", "500ml", "1L"])
                        qty = st.number_input("Initial Stock", min_value=1, value=50)
                        price = st.number_input("Selling Price", value=300.0)

                    if st.form_submit_button("💾 Save Changes to Cloud"):
                        with st.spinner("Updating Cloud Database..."):
                            res = add_stock(variant, size, qty, price, user=st.session_state.logged_in_user)
                            st.success(res)
                            st.rerun()

        with tab3:
            hist = st.session_state.history
            if not hist.empty:
                st.dataframe(hist.sort_values(by="Timestamp", ascending=False), use_container_width=True, height=500)
            else:
                st.info("No history found.")

    # --- PAGE 4: HISTORY ---
    elif menu == "Sales History":
        st.markdown("## 📊 Transaction Archive")
        df = st.session_state.sales_data
        if not df.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                search = st.text_input("🔍 Search Transactions", placeholder="Type customer name, seller, or ID...")
            
            if search:
                mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                df = df[mask]
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("No sales data available.")

