import streamlit as st
import pandas as pd
import yfinance as yf

# 基本配置
st.set_page_config(page_title="智能投資戰情室", layout="wide")

# --- 1. 緩存機制 (設定 10 分鐘，避免頻繁請求被鎖) ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- 2. 側邊欄：智能選股診斷 ---
st.sidebar.markdown("## 🔍 智能選股診斷")
search_id = st.sidebar.text_input("輸入代碼 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        s_stock = yf.Ticker(search_id)
        s_info = s_stock.info
        # 優先抓取中文或簡稱
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

# --- 3. 主畫面 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 投資實時戰情室</h1>", unsafe_allow_html=True)

# 你的 Google Sheets CSV 網址 (已根據你提供的網址填入)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=0&single=true&output=csv"

try:
    df = load_data(SHEET_URL)
    details = []

    with st.spinner('數據同步中，請稍候...'):
        id_list = [str(i).strip() for i in df['ID'].unique()]
        # 批次抓取價格，大幅降低被封鎖機率
        all_data = yf.download(id_list, period="1d", group_by='ticker', progress=False)

        for _, row in df.iterrows():
            sid = str(row['ID']).strip()
            # 取得現價
            curr_p = all_data[sid]['Close'].iloc[-1] if len(id_list) > 1 else all_data['Close'].iloc[-1]
            
            # 獲取名稱
            tk = yf.Ticker(sid)
            stock_name = tk.info.get('shortName') or tk.info.get('longName') or sid
            
            fee = row.get('Fee', 0)
            cost_sum = (row['Price'] * row['Qty']) + fee
            market_val = curr_p * row['Qty']
            profit = market_val - cost_sum
            roi = (profit / cost_sum) * 100 if cost_sum > 0 else 0
            
            details.append({
                "代碼": sid,
                "名稱": stock_name,
                "手續費": fee,
                "總成本": cost_sum,
                "目前市值": market_val,
                "損益": profit,
                "報酬率(%)": roi
            })

    final_df = pd.DataFrame(details)

    # 上方指標看板
    total_v = final_df['目前市值'].sum()
    total_c = final_df['總成本'].sum()
    total_p = total_v - total_c
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前總市值", f"${total_v:,.0f}")
    col2.metric("總淨損益", f"${total_p:,.0f}", f"{(total_p/total_c*100):.2f}%")
    col3.metric("總投入成本", f"${total_c:,.0f}")

    st.write("### 🗂️ 詳細持股明細")

    # --- 建立總計列 ---
    summary = pd.DataFrame([{
        "代碼": "✨ 總計",
        "名稱": "-",
        "手續費": final_df['手續費'].sum(),
        "總成本": final_df['總成本'].sum(),
        "目前市值": final_df['目前市值'].sum(),
        "損益": final_df['損益'].sum(),
        "報酬率(%)": (final_df['損益'].sum() / final_df['總成本'].sum() * 100)
    }])

    # 合併清單與總計列
    display_df = pd.concat([final_df, summary], ignore_index=True)

    # 顯示表格並設定千分位格式
    st.table(display_df.style.format({
        "手續費": "{:,.0f}",
        "總成本": "{:,.0f}",
        "目前市值": "{:,.0f}",
        "損益": "{:,.0f}",
        "報酬率(%)": "{:.2f}%"
    }))

except Exception as e:
    st.error(f"連線暫時受阻：{e}")
    st.info("Yahoo 伺服器冷卻中，請等待 15 分鐘後重新整理網頁。")
