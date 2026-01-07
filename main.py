import streamlit as st
import pandas as pd
import yfinance as yf

# 設定網頁標題與排版
st.set_page_config(page_title="智能投資決策戰情室", layout="wide")

# 1. 解決更新慢：使用 Streamlit 緩存，設定 2 分鐘過期一次
@st.cache_data(ttl=120)
def load_data(url):
    df = pd.read_csv(url)
    df['ID'] = df['ID'].astype(str).str.strip()
    return df

# 2. 側邊欄：獨立診斷區 (輸入股票號碼看建議)
st.sidebar.markdown("## 🔍 智能選股診斷")
search_id = st.sidebar.text_input("請輸入股票代碼 (例: 2330.TW)", "0056.TW")

if search_id:
    try:
        s_stock = yf.Ticker(search_id)
        s_info = s_stock.info
        s_name = s_info.get('longName', '找不到名稱')
        s_price = s_stock.history(period="1d")['Close'].iloc[-1]
        
        st.sidebar.markdown(f"### 📋 {s_name}")
        st.sidebar.metric("目前價格", f"{s_price:.2f}")

        # 長短期判斷邏輯
        pe = s_info.get('trailingPE', 0)
        hist = s_stock.history(period="20d")
        ma20 = hist['Close'].mean()

        st.sidebar.markdown("---")
        # 長期建議 (本益比法)
        if pe > 0:
            if pe < 15: st.sidebar.success("✅ **長期建議：** 價值低估，適合存股佈局。")
            elif pe < 25: st.sidebar.info("🟡 **長期建議：** 股價合理。")
            else: st.sidebar.warning("⚠️ **長期建議：** 目前太貴，不宜長抱。")
        
        # 短期建議 (動能法)
        if s_price > ma20:
            st.sidebar.success("🚀 **短期建議：** 強勢上漲中。")
        else:
            st.sidebar.warning("📉 **短期建議：** 走勢偏弱。")
            
    except:
        st.sidebar.error("請確認代碼是否正確 (需含 .TW)")

# 3. 主畫面：投資對帳單
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📈 我的投資實時戰情室</h1>", unsafe_allow_html=True)

# 你的 Google Sheet CSV 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    data = load_data(SHEET_URL)
    
    total_cost = 0
    total_value = 0
    details = []

    for _, row in data.iterrows():
        tk = yf.Ticker(row['ID'])
        curr_p = tk.history(period="1d")['Close'].iloc[-1]
        name = tk.info.get('longName', row['ID'])
        
        # 成本滾算公式：(買入單價 * 股數) + 手續費
        # 注意：你的 Google Sheets 需增加一欄名為 Fee
        fee = row.get('Fee', 0)
        cost_sum = (row['Price'] * row['Qty']) + fee
        market_val = curr_p * row['Qty']
        profit = market_val - cost_sum
        roi = (profit / cost_sum) * 100 if cost_sum > 0 else 0
        
        total_cost += cost_sum
        total_value += market_val
        
        details.append({
            "名稱": name,
            "代碼": row['ID'],
            "手續費": fee,
            "總成本": f"{cost_sum:,.0f}",
            "損益": f"{profit:,.0f}",
            "報酬率": f"{roi:.2f}%"
        })

    # 看板顯示
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_value:,.0f}")
    c2.metric("總淨損益 (含手續費)", f"${(total_value - total_cost):,.0f}")
    c3.metric("總投入金額", f"${total_cost:,.0f}")

    st.write("### 🗂️ 持股詳細明細")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.info("請確認 Google Sheet 已填寫資料並發布 CSV。")
