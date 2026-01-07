import streamlit as st

import pandas as pd

import yfinance as yf



# 設定網頁標題與排版

st.set_page_config(page_title="智能投資戰情室", layout="wide")



# --- 1. 解決更新慢問題：設定緩存僅 2 分鐘 (120秒) ---

@st.cache_data(ttl=120)

def load_data(url):

    df = pd.read_csv(url)

    df['ID'] = df['ID'].astype(str).str.strip()

    return df



# --- 2. 側邊欄：智能診斷區 ---

st.sidebar.markdown("## 🔍 股票快速診斷")

search_id = st.sidebar.text_input("輸入代碼看建議 (例: 2330.TW)", "2330.TW")



if search_id:

    try:

        s_stock = yf.Ticker(search_id)

        s_info = s_stock.info

        # 抓取中文名稱 (yf 有時只有英文，會儘量抓取)

        s_name = s_info.get('longName') or s_info.get('shortName') or search_id

        # 取得最新股價

        s_hist = s_stock.history(period="1d")

        if not s_hist.empty:

            s_price = s_hist['Close'].iloc[-1]

            st.sidebar.markdown(f"### 📋 {s_name}")

            st.sidebar.metric("目前價格", f"{s_price:.2f}")



            # 診斷邏輯

            pe = s_info.get('trailingPE', 0)

            ma20 = s_stock.history(period="20d")['Close'].mean()



            st.sidebar.markdown("---")

            # 長期判斷

            if pe > 0:

                if pe < 15: st.sidebar.success("✅ 長期：估值低，適合存股。")

                elif pe < 25: st.sidebar.info("🟡 長期：價格合理。")

                else: st.sidebar.warning("⚠️ 長期：目前偏貴。")

            

            # 短期判斷

            if s_price > ma20:

                st.sidebar.success("🚀 短期：強勢上漲中。")

            else:

                st.sidebar.warning("📉 短期：走勢偏弱。")

    except:

        st.sidebar.error("代碼錯誤，請確認包含 .TW")



# --- 3. 主畫面：自動對帳單 ---

st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 我的投資實時戰情室</h1>", unsafe_allow_html=True)



# 貼入你的 Google Sheets CSV 連結

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"



try:

    df = load_data(SHEET_URL)

    

    total_cost = 0

    total_value = 0

    details = []



    with st.spinner('同步最新數據中...'):

        for _, row in df.iterrows():

            tk = yf.Ticker(row['ID'])

            curr_p = tk.history(period="1d")['Close'].iloc[-1]

            info = tk.info

            name = info.get('longName') or info.get('shortName') or row['ID']

            

            # 成本滾算：(單價 * 股數) + 手續費

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

                "手續費": f"{fee:,.0f}",

                "總成本": f"{cost_sum:,.0f}",

                "目前市值": f"{market_val:,.0f}",

                "損益": f"{profit:,.0f}",

                "報酬率": f"{roi:.2f}%"

            })



    # 看板顯示

    c1, c2, c3 = st.columns(3)

    c1.metric("當前總市值", f"${total_value:,.0f}")

    c2.metric("總損益 (含手續費)", f"${(total_value - total_cost):,.0f}", f"{((total_value-total_cost)/total_cost*100):.2f}%")

    c3.metric("總投入成本", f"${total_cost:,.0f}")



    st.write("### 🗂️ 詳細持股清單")

    st.table(pd.DataFrame(details))



except Exception as e:

    st.info("正在連線 Google Sheet... 請確認 CSV 網址是否正確。")
