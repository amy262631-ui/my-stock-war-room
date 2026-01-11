import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基礎配置
st.set_page_config(page_title="個人資產決策管理系統", layout="wide")

# --- 2. 數據處理與緩存 ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    # 強制清洗代碼，確保沒有空白或非法字元
    df['ID'] = df['ID'].astype(str).str.strip().str.upper()
    return df

# --- 3. 側邊欄：目標管理 ---
st.sidebar.header("🎯 投資目標設定")
annual_target = st.sidebar.number_input("年領股息目標 (TWD)", value=500000, step=10000)

# --- 4. 主畫面邏輯 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ 個人資產決策管理系統</h1>", unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=2040510123&single=true&output=csv"

try:
    raw_df = load_data(SHEET_URL)
    
    # 【合併持股邏輯】
    raw_df['Cost_Part'] = raw_df['Price'] * raw_df['Qty']
    grouped = raw_df.groupby('ID').agg({'Qty': 'sum', 'Cost_Part': 'sum', 'Fee': 'sum'}).reset_index()
    grouped['TotalCost'] = grouped['Cost_Part'] + grouped['Fee']
    
    details = []
    with st.spinner('同步最新行情與計算年化股息...'):
        # 取得不重複代碼清單並過濾掉空值
        id_list = [i for i in grouped['ID'].tolist() if i and i != 'NAN']
        
        # 批次下載價格 (修正 400 錯誤的核心：使用更穩定的下載方式)
        prices_df = yf.download(id_list, period="5d", group_by='ticker', progress=False, threads=True)

        for _, row in grouped.iterrows():
            sid = row['ID']
            if sid not in prices_df.columns and len(id_list) > 1: continue
            
            tk = yf.Ticker(sid)
            # 取得最新收盤價
            if len(id_list) > 1:
                curr_p = prices_df[sid]['Close'].iloc[-1]
            else:
                curr_p = prices_df['Close'].iloc[-1]
            
            # 自動抓取中文/簡稱
            name = tk.info.get('shortName') or tk.info.get('longName') or sid
            
            # 股息推算
            div_rate = tk.info.get('dividendRate', 0)
            if not div_rate:
                div_rate = curr_p * tk.info.get('dividendYield', 0)
            
            mv = curr_p * row['Qty']
            profit = mv - row['TotalCost']
            ann_div = div_rate * row['Qty']
            
            # 行動指南
            signal = "🟢 持有"
            if profit < -row['TotalCost'] * 0.1: signal = "🔵 價值加碼"
            elif profit > row['TotalCost'] * 0.2: signal = "🔥 獲利減碼"

            details.append({
                "名稱": name, "代碼": sid, "持股數": row['Qty'], "總成本": row['TotalCost'],
                "市值": mv, "損益": profit, "報酬%": (profit/row['TotalCost']*100),
                "年領股息": ann_div, "殖利率%": (div_rate/curr_p*100) if curr_p > 0 else 0,
                "行動指南": signal
            })

    final_df = pd.DataFrame(details)
    total_mv = final_df['市值'].sum()
    total_div = final_df['年領股息'].sum()
    total_c = final_df['總成本'].sum()

    # --- 看板與進度條 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("總資產市值", f"${total_mv:,.0f}")
    c2.metric("預估年領股息", f"${total_div:,.0f}")
    c3.metric("目標達成率", f"{(total_div/annual_target*100):.1f}%")
    st.progress(min(total_div / annual_target, 1.0))

    # --- 視覺化分析 ---
    col_chart, col_guide = st.columns([1, 1.2])
    with col_chart:
        st.write("### 🍰 資產配置佔比")
        fig = px.pie(final_df, values='市值', names='名稱', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

    with col_guide:
        st.write("### 📢 持股風險檢查")
        max_stock = final_df.loc[final_df['市值'].idxmax()]
        if (max_stock['市值'] / total_mv) > 0.3:
            st.error(f"⚠️ 警報：**{max_stock['名稱']}** 佔比過高，風險太集中！")
        else:
            st.success("✅ 持股分配均衡，請繼續保持。")
        
        # 顯示獲利/虧損提醒
        for _, r in final_df.iterrows():
            if "🔥" in r['行動指南']:
                st.warning(f"🔔 {r['名稱']}：目前獲利豐厚，可考慮部分入袋。")

    # --- 詳細表格與總計 ---
    st.write("### 🗂️ 已合併持股明細")
    summary = pd.DataFrame([{
        "名稱": "✨ 總計", "代碼": "-", "持股數": "-", "總成本": total_c,
        "市值": total_mv, "損益": total_mv - total_c, "報酬%": (total_mv - total_c)/total_c*100,
        "年領股息": total_div, "殖利率%": total_div/total_mv*100, "行動指南": "-"
    }])
    st.table(pd.concat([final_df, summary], ignore_index=True).style.format({
        "持股數": "{:,.0f}", "總成本": "{:,.0f}", "市值": "{:,.0f}",
        "損益": "{:,.0f}", "報酬%": "{:.2f}%", "年領股息": "{:,.0f}", "殖利率%": "{:.2f}%"
    }))

except Exception as e:
    st.error(f"連線中斷或數據異常: {e}")
    st.info("💡 提示：若持續 400 錯誤，請檢查 Google Sheets ID 欄位是否有非股票代碼的文字。")
