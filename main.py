import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基本設定 (前端 HTML 風格)
st.set_page_config(page_title="小白股票戰情室", layout="wide")

# 使用 HTML 語法做一個漂亮的標題列
st.markdown("""
    <div style="background-color:#003366; padding:20px; border-radius:15px; margin-bottom:25px">
        <h1 style="color:white; text-align:center; font-family:sans-serif;">📈 我的投資實時戰情室</h1>
        <p style="color:#D1D5DB; text-align:center;">數據自動同步自 Google Sheets</p>
    </div>
""", unsafe_allow_html=True)

# 2. 設定你的 Google Sheet CSV 連結 (請記得更換成你自己的網址)
# 步驟：Google Sheet -> 檔案 -> 共用 -> 發布到網路 -> 選擇 CSV -> 複製網址
SHEET_URL = "請在此處貼上你的CSV網址"

try:
    # 讀取資料
    df = pd.read_csv(SHEET_URL)
    
    # 強制將 ID 轉為字串並移除空白
    df['ID'] = df['ID'].astype(str).str.strip()
    
    # 3. 後端邏輯計算
    total_cost = 0
    total_value = 0
    details = []

    with st.spinner('正在從交易所抓取最新行情...'):
        for _, row in df.iterrows():
            stock = yf.Ticker(row['ID'])
            # 抓取最新收盤價
            price_data = stock.history(period="1d")
            if not price_data.empty:
                cur_price = price_data['Close'].iloc[-1]
                cost = row['Price'] * row['Qty']
                market_value = cur_price * row['Qty']
                profit = market_value - cost
                roi = (profit / cost) * 100 if cost > 0 else 0
                
                total_cost += cost
                total_value += market_value
                
                details.append({
                    "代碼": row['ID'],
                    "成本價": row['Price'],
                    "現價": round(cur_price, 2),
                    "股數": row['Qty'],
                    "損益": round(profit, 0),
                    "報酬率(%)": f"{roi:.2f}%"
                })

    # 4. 前端展示：大數字卡片
    total_profit = total_value - total_cost
    total_roi = (total_profit / total_cost) * 100 if total_cost > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前總市值", f"${total_value:,.0f}")
    col2.metric("總損益", f"${total_profit:,.0f}", f"{total_roi:.2f}%")
    col3.metric("投入本金", f"${total_cost:,.0f}")

    # 5. 展示明細清單
    st.subheader("🗂️ 持股明細")
    st.table(pd.DataFrame(details))

except Exception as e:
    st.error(f"目前讀取不到數據。請確認 Google Sheets 是否已發布為 CSV，並將網址填入程式碼中。")
    st.info("錯誤提示: " + str(e))