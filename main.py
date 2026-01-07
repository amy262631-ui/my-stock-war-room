import streamlit as st

import pandas as pd

import yfinance as yf



# 基本設定

st.set_page_config(page_title="智能投資戰情室", layout="wide")



# --- 1. 解決更新慢：設定 2 分鐘緩存 ---

@st.cache_data(ttl=120)

def load_data(url):

    return pd.read_csv(url)



# --- 2. 側邊欄：智能診斷區 ---

st.sidebar.markdown("## 🔍 智能選股診斷")

search_id = st.sidebar.text_input("輸入代碼 (例: 2330.TW)", "2330.TW")



if search_id:

    try:

        s_stock = yf.Ticker(search_id)

        s_name = s_stock.info.get('longName', search_id)

        s_price = s_stock.history(period="1d")['Close'].iloc[-1]

        st.sidebar.markdown(f"### {s_name}\n**現價：{s_price:.2f}**")

        

        # 簡單判斷邏輯

        pe = s_stock.info.get('trailingPE', 0)

        ma20 = s_stock.history(period="20d")['Close'].mean()

        

        st.sidebar.write("---")

        if pe > 0:

            if pe < 15: st.sidebar.success("✅ 長期：價值低估，適合存股。")

            elif pe < 25: st.sidebar.info("🟡 長期：估值合理。")

            else: st.sidebar.warning("⚠️ 長期：目前偏貴。")

            

        if s_price > ma20: st.sidebar.success("🚀 短期：走勢強勁。")

        else: st.sidebar.warning("📉 短期：走勢偏弱。")

    except:

        st.sidebar.error("請輸入正確代碼 (需含 .TW)")



# --- 3. 主畫面：對帳單 ---

st.markdown("<h1 style='text-align: center;'>📊 投資實時戰情室</h1>", unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"



try:

    df = load_data(SHEET_URL)

    df['ID'] = df['ID'].astype(str).str.strip()

    

    total_cost, total_value, details = 0, 0, []



    for _, row in df.iterrows():

        tk = yf.Ticker(row['ID'])

        cur_p = tk.history(period="1d")['Close'].iloc[-1]

        # 自動抓取中文/英文名稱

        name = tk.info.get('longName', row['ID'])

        

        # 成本滾算：(單價 * 股數) + 手續費

        fee = row.get('Fee', 0)

        cost = (row['Price'] * row['Qty']) + fee

        mkt_val = cur_p * row['Qty']

        profit = mkt_val - cost

        

        total_cost += cost

        total_value += mkt_val

        details.append({"名稱": name, "代碼": row['ID'], "成本": f"{cost:,.0f}", "損益": f"{profit:,.0f}", "報酬率": f"{(profit/cost*100):.2f}%"})



    c1, c2, c3 = st.columns(3)

    c1.metric("總市值", f"${total_value:,.0f}")

    c2.metric("總損益(含費)", f"${(total_value - total_cost):,.0f}")

    c3.metric("總成本", f"${total_cost:,.0f}")

    st.table(pd.DataFrame(details))



except:

    st.info("連線中... 請確認 Google Sheets 已發布 CSV 並填入正確代碼 (如 0056.TW)。")
