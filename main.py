import streamlit as st
import pandas as pd
import yfinance as yf

# 基本配置
st.set_page_config(page_title="智能投資戰情室", layout="wide")

# --- 1. 緩存機制 (10分鐘更新一次) ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    # 強制清理標題空白，避免 400 錯誤
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- 2. 側邊欄：智能診斷區 (目前已運作正常) ---
st.sidebar.markdown("## 🔍 智能選股診斷")
search_id = st.sidebar.text_input("輸入代碼 (例: 2330.TW)", "2330.TW")

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
        st.sidebar.error("請確認代碼含 .TW")

# --- 3. 主畫面：投資對帳單 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 投資實時戰情室</h1>", unsafe_allow_html=True)

# 貼入剛才在步驟 1 取得的 CSV 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    df = load_data(SHEET_URL)
    total_cost, total_value, details = 0, 0, []

    with st.spinner('同步最新股市數據中...'):
        # 批次取得股價，減少請求次數避免被封鎖
        id_list = [str(i).strip() for i in df['ID'].unique()]
        price_data = yf.download(id_list, period="1d", group_by='ticker', progress=False)

        for _, row in df.iterrows():
            sid = str(row['ID']).strip()
            # 取得現價
            if len(id_list) > 1:
                curr_p = price_data[sid]['Close'].iloc[-1]
            else:
                curr_p = price_data['Close'].iloc[-1]
            
            # 計算成本與手續費
            fee = row.get('Fee', 0)
            cost_sum = (row['Price'] * row['Qty']) + fee
            market_val = curr_p * row['Qty']
            profit = market_val - cost_sum
            roi = (profit / cost_sum) * 100 if cost_sum > 0 else 0
            
            total_cost += cost_sum
            total_value += market_val
            
            details.append({
                "代碼": sid, "手續費": f"{fee:,.0f}",
                "總成本": f"{cost_sum:,.0f}", "目前市值": f"{market_val:,.0f}",
                "損益": f"{profit:,.0f}", "報酬率": f"{roi:.2f}%"
            })

    # 數據指標卡
    c1, c2, c3 = st.columns(3)
    c1.metric("當前總市值", f"${total_value:,.0f}")
    if total_cost > 0:
        c2.metric("總損益 (含手續費)", f"${(total_value - total_cost):,.0f}", f"{((total_value-total_cost)/total_cost*100):.2f}%")
    c3.metric("總投入成本", f"${total_cost:,.0f}")

    st.write("### 🗂️ 詳細持股明細")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.error(f"連線更新中：{e}")
    st.info("建議動作：1. 清除網頁快取 (Clear Cache) 2. 檢查 Google Sheets 標題是否為 ID, Price, Qty, Fee。")
