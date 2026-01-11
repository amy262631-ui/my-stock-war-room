import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基礎配置
st.set_page_config(page_title="個人資產決策管理系統", layout="wide")

# --- 2. 數據處理與緩存 (強化過濾機制) ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    # 【核心修復】自動清洗 ID：轉大寫、修剪空白、只保留正確含 ".TW" 或 ".TWO" 的代碼
    df['ID'] = df['ID'].astype(str).str.strip().str.upper()
    df = df[df['ID'].str.contains(r'\.TW', na=False)]
    return df

# --- 3. 側邊欄：目標設定與智能診斷 ---
st.sidebar.header("🎯 投資目標設定")
annual_target = st.sidebar.number_input("年領股息目標 (TWD)", value=500000, step=10000)

st.sidebar.markdown("---")
st.sidebar.header("🔍 智能選股診斷")
search_id = st.sidebar.text_input("輸入代碼看診斷 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        tk_diag = yf.Ticker(search_id)
        info_diag = tk_diag.info
        hist_diag = tk_diag.history(period="60d")
        cp_diag = hist_diag['Close'].iloc[-1]
        
        # 多維度評分因子
        pe_diag = info_diag.get('trailingPE', 0)
        ma20_diag = hist_diag['Close'].tail(20).mean()
        dy_diag = (info_diag.get('dividendRate', 0) / cp_diag * 100) if cp_diag > 0 else 0
        
        st.sidebar.subheader(info_diag.get('shortName', search_id))
        st.sidebar.metric("目前價格", f"{cp_diag:.2f}")
        
        score = 0
        tips = []
        if 0 < pe_diag < 18: score += 25; tips.append("💰 價值：估值合理")
        if cp_diag > ma20_diag: score += 25; tips.append("🚀 動能：股價強勢")
        if dy_diag > 5: score += 25; tips.append("🧧 股息：高回報率")
        if info_diag.get('debtToEquity', 100) < 80: score += 25; tips.append("🛡️ 財務：體質穩健")
        
        st.sidebar.write(f"**綜合評分：{score} / 100**")
        for t in tips: st.sidebar.write(t)
    except:
        st.sidebar.error("診斷資料載入中或代碼錯誤")

# --- 4. 主畫面邏輯 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ 個人資產決策管理系統</h1>", unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=2040510123&single=true&output=csv"

try:
    raw_df = load_data(SHEET_URL)
    
    # 【功能 1：合併重複持股】
    raw_df['Cost_Total'] = raw_df['Price'] * raw_df['Qty']
    grouped = raw_df.groupby('ID').agg({'Qty': 'sum', 'Cost_Total': 'sum', 'Fee': 'sum'}).reset_index()
    grouped['Final_Cost'] = grouped['Cost_Total'] + grouped['Fee']
    
    details = []
    with st.spinner('同步最新股市數據與股利估算...'):
        id_list = grouped['ID'].tolist()
        # 批次下載價格避免 HTTP 400 錯誤
        all_prices = yf.download(id_list, period="5d", group_by='ticker', progress=False)

        for _, row in grouped.iterrows():
            sid = row['ID']
            tk = yf.Ticker(sid)
            # 取得現價
            curr_p = all_prices[sid]['Close'].iloc[-1] if len(id_list) > 1 else all_prices['Close'].iloc[-1]
            
            # 【功能 2：自動中文名稱】
            name = tk.info.get('shortName') or tk.info.get('longName') or sid
            
            # 【功能 3：自動推算股利】
            div_rate = tk.info.get('dividendRate', 0)
            if not div_rate:
                div_rate = curr_p * tk.info.get('dividendYield', 0)
            
            mv = curr_p * row['Qty']
            profit = mv - row['Final_Cost']
            ann_div = div_rate * row['Qty']
            
            # 管理行動建議
            signal = "🟢 持有"
            if profit < -row['Final_Cost'] * 0.1: signal = "🔵 價值加碼"
            elif profit > row['Final_Cost'] * 0.2: signal = "🔥 獲利減碼"

            details.append({
                "名稱": name, "代碼": sid, "持股數": row['Qty'], "總成本": row['Final_Cost'],
                "市值": mv, "損益": profit, "報酬率%": (profit/row['Final_Cost']*100),
                "年領股息": ann_div, "殖利率%": (div_rate/curr_p*100) if curr_p > 0 else 0,
                "管理信號": signal
            })

    final_df = pd.DataFrame(details)
    total_mv = final_df['市值'].sum()
    total_div = final_df['年領股息'].sum()
    total_cost = final_df['總成本'].sum()

    # --- 數據看板 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("當前總資產", f"${total_mv:,.0f}")
    c2.metric("預估年領股息", f"${total_div:,.0f}")
    c3.metric("目標達成率", f"{(total_div/annual_target*100):.1f}%")
    st.progress(min(total_div / annual_target, 1.0))

    # --- 視覺化分析 ---
    col_chart, col_risk = st.columns([1, 1.5])
    with col_chart:
        st.write("### 🍰 資產配置佔比")
        fig = px.pie(final_df, values='市值', names='名稱', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

    with col_risk:
        st.write("### 📢 風險控管指南")
        max_stock = final_df.loc[final_df['市值'].idxmax()]
        if (max_stock['市值'] / total_mv) > 0.35:
            st.error(f"⚠️ 警報：**{max_stock['名稱']}** 佔比達 {max_stock['市值']/total_mv*100:.1f}%，建議分散佈局。")
        else:
            st.success("✅ 持股分配均衡，風險管控良好。")
            
        for _, r in final_df.iterrows():
            if "🔥" in r['管理信號']:
                st.warning(f"🔔 {r['名稱']}：目前報酬率極佳 ({r['報酬率%']:.1f}%)，可考慮部分減碼。")

    # --- 總表顯示 ---
    st.write("### 🗂️ 已合併持股詳細清單")
    summary = pd.DataFrame([{
        "名稱": "✨ 總計", "代碼": "-", "持股數": "-", "總成本": total_cost,
        "市值": total_mv, "損益": total_mv - total_cost, 
        "報酬率%": (total_mv - total_cost)/total_cost*100 if total_cost > 0 else 0,
        "年領股息": total_div, "殖利率%": total_div/total_mv*100 if total_mv > 0 else 0, "管理信號": "-"
    }])
    st.table(pd.concat([final_df, summary], ignore_index=True).style.format({
        "持股數": "{:,.0f}", "總成本": "{:,.0f}", "市值": "{:,.0f}",
        "損益": "{:,.0f}", "報酬率%": "{:.2f}%", "年領股息": "{:,.0f}", "殖利率%": "{:.2f}%"
    }))

except Exception as e:
    st.error(f"連線異常：{e}")
    st.info("💡 解決方案：請檢查 Google Sheets 'ID' 欄位是否包含非股票代碼的字元。")
