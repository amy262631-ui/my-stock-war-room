import streamlit as st
import pandas as pd
import yfinance as yf
import datetime

st.set_page_config(page_title="專業級股票戰情室", layout="wide")

# --- 1. 更新慢的解決方案：緩存設定 ---
# 透過 st.cache_data 讓網頁讀取更快，且設定每 5 分鐘強制更新一次
@st.cache_data(ttl=300) 
def get_stock_data(url):
    return pd.read_csv(url)

# --- 2. 前端美化 (HTML) ---
st.markdown("""
    <div style="background-color:#0f172a; padding:20px; border-radius:15px; margin-bottom:25px">
        <h1 style="color:white; text-align:center;">💎 智能投資決策戰情室</h1>
    </div>
""", unsafe_allow_html=True)

# --- 3. 診斷區 (互動功能) ---
st.sidebar.header("🔍 股票快速診斷")
search_id = st.sidebar.text_input("輸入代碼看建議 (例: 2330.TW)", "2330.TW")
if search_id:
    s_info = yf.Ticker(search_id)
    # 抓取中文名稱 (yf 有時只給英文，若無則顯示代碼)
    s_name = s_info.info.get('longName', search_id)
    s_price = s_info.history(period="1d")['Close'].iloc[-1]
    pe_ratio = s_info.info.get('trailingPE', 0)
    
    st.sidebar.write(f"**名稱：** {s_name}")
    st.sidebar.write(f"**現價：** {s_price:.2f}")
    
    # 判斷建議
    if pe_ratio > 0:
        if pe_ratio < 15:
            st.sidebar.success("✅ 長期建議：價值低估，適合長線佈局。")
        elif pe_ratio < 25:
            st.sidebar.info("🟡 長期建議：估值合理。")
        else:
            st.sidebar.warning("⚠️ 長期建議：目前偏貴，小心追高。")
    
    # 短期建議 (簡單均線判斷)
    hist = s_info.history(period="20d")
    ma20 = hist['Close'].mean()
    if s_price > ma20:
        st.sidebar.success("🚀 短期建議：強勢上漲中，具動能。")
    else:
        st.sidebar.warning("📉 短期建議：走勢偏弱，建議觀望。")

# --- 4. 對帳單核心邏輯 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    df = get_stock_data(SHEET_URL)
    df['ID'] = df['ID'].astype(str).str.strip()
    
    total_cost_with_fee = 0
    total_value = 0
    details = []

    for _, row in df.iterrows():
        tk = yf.Ticker(row['ID'])
        cur_price = tk.history(period="1d")['Close'].iloc[-1]
        name = tk.info.get('longName', row['ID'])
        
        # 成本計算：(單價 * 股數) + 手續費
        cost = (row['Price'] * row['Qty']) + row.get('Fee', 0)
        mkt_val = cur_price * row['Qty']
        profit = mkt_val - cost
        roi = (profit / cost) * 100 if cost > 0 else 0
        
        total_cost_with_fee += cost
        total_value += mkt_val
        
        details.append({
            "股票名稱": name,
            "代碼": row['ID'],
            "手續費": row.get('Fee', 0),
            "總成本": f"{cost:,.0f}",
            "現價": f"{cur_price:.2f}",
            "損益": f"{profit:,.0f}",
            "報酬率": f"{roi:.2f}%"
        })

    # 顯示總表
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_value:,.0f}")
    c2.metric("總損益(含手續費)", f"${(total_value - total_cost_with_fee):,.0f}")
    c3.metric("總投入成本", f"${total_cost_with_fee:,.0f}")

    st.write("### 🗂️ 詳細持股清單")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.info("正在等待 Google Sheets 資料... 請確保 CSV 網址已填入。")
