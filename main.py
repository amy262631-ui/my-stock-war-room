import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="智能投資決策戰情室", layout="wide")

# --- 1. 緩存設定 (2分鐘更新一次) ---
@st.cache_data(ttl=120)
def load_data(url):
    # 這裡強制讀取最新資料，避免被舊連結卡住
    return pd.read_csv(url)

# --- 2. 側邊欄診斷區 ---
st.sidebar.markdown("## 🔍 智能選股診斷")
search_id = st.sidebar.text_input("輸入代碼看建議 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        s_stock = yf.Ticker(search_id)
        s_info = s_stock.info
        s_name = s_info.get('longName') or s_info.get('shortName') or search_id
        s_price = s_stock.history(period="1d")['Close'].iloc[-1]
        
        st.sidebar.markdown(f"### 📋 {s_name}\n**現價：{s_price:.2f}**")
        
        pe = s_info.get('trailingPE', 0)
        ma20 = s_stock.history(period="20d")['Close'].mean()
        
        st.sidebar.markdown("---")
        if pe > 0:
            if pe < 15: st.sidebar.success("✅ 長期：價值低估。")
            elif pe < 25: st.sidebar.info("🟡 長期：股價合理。")
            else: st.sidebar.warning("⚠️ 長期：目前偏貴。")
        
        if s_price > ma20: st.sidebar.success("🚀 短期：強勢上漲中。")
        else: st.sidebar.warning("📉 短期：走勢偏弱。")
    except:
        st.sidebar.error("請輸入完整代碼 (需含 .TW)")

# --- 3. 主畫面設定 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 投資實時戰情室</h1>", unsafe_allow_html=True)

# 請更換為你在第一步獲得的「StockData 分頁」CSV 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    df = load_data(SHEET_URL)
    df.columns = df.columns.str.strip() # 去除標題可能有的空白
    
    total_cost, total_value, details = 0, 0, []

    with st.spinner('同步最新股市行情中...'):
        for _, row in df.iterrows():
            stock_id = str(row['ID']).strip()
            tk = yf.Ticker(stock_id)
            hist = tk.history(period="1d")
            
            if not hist.empty:
                cur_p = hist['Close'].iloc[-1]
                name = tk.info.get('longName') or tk.info.get('shortName') or stock_id
                
                fee = row.get('Fee', 0)
                cost_sum = (row['Price'] * row['Qty']) + fee
                market_val = cur_p * row['Qty']
                profit = market_val - cost_sum
                roi = (profit / cost_sum) * 100 if cost_sum > 0 else 0
                
                total_cost += cost_sum
                total_value += market_val
                
                details.append({
                    "名稱": name, "代碼": stock_id, "手續費": f"{fee:,.0f}",
                    "總成本": f"{cost_sum:,.0f}", "目前市值": f"{market_val:,.0f}",
                    "損益": f"{profit:,.0f}", "報酬率": f"{roi:.2f}%"
                })

    # 看板展示
    c1, c2, c3 = st.columns(3)
    c1.metric("當前總市值", f"${total_value:,.0f}")
    if total_cost > 0:
        c2.metric("總損益 (含手續費)", f"${(total_value - total_cost):,.0f}", f"{((total_value-total_cost)/total_cost*100):.2f}%")
    c3.metric("總投入成本", f"${total_cost:,.0f}")

    st.write("### 🗂️ 詳細持股明細")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.error(f"連線失敗：{e}")
    st.info("請確認：1. Google Sheets 已發佈為 CSV。2. 標題列為 ID, Price, Qty, Fee。")
