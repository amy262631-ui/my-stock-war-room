import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="智能投資決策戰情室", layout="wide")

# --- 1. 緩存設定 (10分鐘更新一次，保護連線) ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

# --- 2. 側邊欄診斷區 ---
st.sidebar.markdown("## 🔍 智能選股診斷")
search_id = st.sidebar.text_input("輸入代碼看建議 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        s_stock = yf.Ticker(search_id)
        s_name = s_stock.info.get('longName') or s_stock.info.get('shortName') or search_id
        s_price = s_stock.history(period="1d")['Close'].iloc[-1]
        
        st.sidebar.markdown(f"### 📋 {s_name}\n**現價：{s_price:.2f}**")
        
        pe = s_stock.info.get('trailingPE', 0)
        ma20 = s_stock.history(period="20d")['Close'].mean()
        
        st.sidebar.markdown("---")
        if pe > 0:
            if pe < 15: st.sidebar.success("✅ 長期：價值低估，適合存股。")
            elif pe < 25: st.sidebar.info("🟡 長期：股價合理。")
            else: st.sidebar.warning("⚠️ 長期：目前偏貴。")
        
        if s_price > ma20: st.sidebar.success("🚀 短期：強勢上漲中。")
        else: st.sidebar.warning("📉 短期：走勢偏弱。")
    except:
        st.sidebar.error("請確認代碼含 .TW")

# --- 3. 主畫面 ---
st.markdown("<h1 style='text-align: center;'>📊 投資實時戰情室</h1>", unsafe_allow_html=True)

# 貼入你指定 StockData 分頁的 CSV 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    df = load_data(SHEET_URL)
    total_cost, total_value, details = 0, 0, []

    with st.spinner('同步最新行情中...'):
        # 批次取得股價
        stock_list = df['ID'].unique().tolist()
        # 修正批次抓取邏輯，確保即使只有一支股票也能運作
        price_df = yf.download(stock_list, period="1d")['Close']

        for _, row in df.iterrows():
            sid = str(row['ID']).strip()
            # 取得現價
            cur_p = price_df[sid].iloc[-1] if len(stock_list) > 1 else price_df.iloc[-1]
            
            # 名稱抓取
            tk = yf.Ticker(sid)
            name = tk.info.get('longName') or tk.info.get('shortName') or sid
            
            fee = row.get('Fee', 0)
            cost_sum = (row['Price'] * row['Qty']) + fee
            mkt_val = cur_p * row['Qty']
            profit = mkt_val - cost_sum
            roi = (profit / cost_sum) * 100 if cost_sum > 0 else 0
            
            total_cost += cost_sum
            total_value += mkt_val
            
            details.append({
                "名稱": name, "代碼": sid, "手續費": f"{fee:,.0f}",
                "總成本": f"{cost_sum:,.0f}", "目前市值": f"{market_val:,.0f}",
                "損益": f"{profit:,.0f}", "報酬率": f"{roi:.2f}%"
            })

    # 看板展示
    c1, c2, c3 = st.columns(3)
    c1.metric("當前總市值", f"${total_value:,.0f}")
    c2.metric("總損益 (含手續費)", f"${(total_value - total_cost):,.0f}", f"{((total_value-total_cost)/total_cost*100):.2f}%")
    c3.metric("總投入成本", f"${total_cost:,.0f}")

    st.write("### 🗂️ 詳細持股明細")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.error(f"連線暫時中斷：{e}")
    st.info("Yahoo 伺服器冷卻中，請 15 分鐘後再重新整理網頁。")

