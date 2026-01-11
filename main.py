import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基礎配置
st.set_page_config(page_title="個人投資管理戰情系統", layout="wide")

# --- 2. 數據處理與緩存 ---
@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    df['ID'] = df['ID'].astype(str).str.strip()
    return df

# --- 3. 側邊欄：目標管理與診斷 ---
st.sidebar.header("🎯 投資目標設定")
annual_target = st.sidebar.number_input("年領股息目標 (TWD)", value=500000, step=10000)

st.sidebar.markdown("---")
st.sidebar.header("🔍 多維度個股診斷")
search_id = st.sidebar.text_input("輸入代碼看建議 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        tk = yf.Ticker(search_id)
        info = tk.info
        hist = tk.history(period="60d")
        cp = hist['Close'].iloc[-1]
        
        # 診斷因子
        pe = info.get('trailingPE', 0)
        ma20 = hist['Close'].tail(20).mean()
        dy = (info.get('dividendRate', 0) / cp * 100) if cp > 0 else 0
        
        st.sidebar.subheader(info.get('shortName', search_id))
        st.sidebar.metric("目前股價", f"{cp:.2f}")
        
        score = 0
        tips = []
        if 0 < pe < 18: score += 25; tips.append("💰 價值：估值合理")
        if cp > ma20: score += 25; tips.append("🚀 動能：股價強勢")
        if dy > 5: score += 25; tips.append("🧧 股息：高回報率")
        if info.get('debtToEquity', 100) < 80: score += 25; tips.append("🛡️ 財務：體質穩健")
        
        st.sidebar.write(f"**綜合評分：{score} / 100**")
        for t in tips: st.sidebar.write(t)
    except:
        st.sidebar.error("診斷暫時不可用")

# --- 4. 主畫面邏輯 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ 個人資產決策管理系統</h1>", unsafe_allow_html=True)

# 你的 Google Sheets CSV 連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=2040510123&single=true&output=csv"

try:
    raw_df = load_data(SHEET_URL)
    
    # 合併持股邏輯
    raw_df['Cost_Part'] = raw_df['Price'] * raw_df['Qty']
    grouped = raw_df.groupby('ID').agg({'Qty': 'sum', 'Cost_Part': 'sum', 'Fee': 'sum'}).reset_index()
    grouped['TotalCost'] = grouped['Cost_Part'] + grouped['Fee']
    
    details = []
    with st.spinner('正在分析資產權重與最新行情...'):
        id_list = grouped['ID'].tolist()
        prices = yf.download(id_list, period="5d", group_by='ticker', progress=False)

        for _, row in grouped.iterrows():
            sid = row['ID']
            tk = yf.Ticker(sid)
            curr_p = prices[sid]['Close'].iloc[-1] if len(id_list) > 1 else prices['Close'].iloc[-1]
            
            # 自動中文名
            name = tk.info.get('shortName') or tk.info.get('longName') or sid
            
            # 股息估算
            div_rate = tk.info.get('dividendRate', 0)
            if not div_rate:
                div_rate = curr_p * tk.info.get('dividendYield', 0)
            
            mv = curr_p * row['Qty']
            profit = mv - row['TotalCost']
            ann_div = div_rate * row['Qty']
            
            # 行動信號
            signal = "🟢 持有觀察"
            if profit < -row['TotalCost'] * 0.1: signal = "🔵 分批攤平"
            elif profit > row['TotalCost'] * 0.2: signal = "🔥 獲利了結"

            details.append({
                "名稱": name, "代碼": sid, "持股數": row['Qty'], "總成本": row['TotalCost'],
                "市值": mv, "損益": profit, "報酬%": (profit/row['TotalCost']*100),
                "年領股息": ann_div, "殖利率%": (div_rate/curr_p*100) if curr_p > 0 else 0,
                "行動信號": signal
            })

    final_df = pd.DataFrame(details)
    total_mv = final_df['市值'].sum()
    total_div = final_df['年領股息'].sum()
    total_c = final_df['總成本'].sum()

    # --- 數據看板 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_mv:,.0f}")
    c2.metric("預估年領股息", f"${total_div:,.0f}")
    c3.metric("目標達成率", f"{(total_div/annual_target*100):.1f}%")
    
    st.write(f"**距離年領 {annual_target:,.0f} 股息目標：**")
    st.progress(min(total_div / annual_target, 1.0))

    # --- 視覺化分析 ---
    col_left, col_right = st.columns([1, 1.5])
    
    with col_left:
        st.write("### 🍰 資產配置比例")
        fig = px.pie(final_df, values='市值', names='名稱', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.write("### 📢 持股管理行動指南")
        for _, r in final_df.iterrows():
            if "🔥" in r['行動信號']:
                st.warning(f"🔔 {r['名稱']}：漲幅已高，可考慮落袋為安。")
            elif "🔵" in r['行動信號']:
                st.info(f"💎 {r['名稱']}：目前處於虧損，若基本面無虞可考慮分批佈局。")
        
        # 風險檢查
        max_stock = final_df.loc[final_df['市值'].idxmax()]
        if (max_stock['市值'] / total_mv) > 0.35:
            st.error(f"⚠️ 警報：{max_stock['名稱']} 佔比過高 ({max_stock['市值']/total_mv*100:.1f}%)，建議分散投資。")

    # --- 最終明細表格 ---
    st.write("### 🗂️ 已合併持股詳細清單")
    summary = pd.DataFrame([{
        "名稱": "✨ 總計", "代碼": "-", "持股數": "-", "總成本": total_c,
        "市值": total_mv, "損益": total_mv - total_c, "報酬%": (total_mv - total_c)/total_c*100,
        "年領股息": total_div, "殖利率%": total_div/total_mv*100, "行動信號": "-"
    }])
    st.table(pd.concat([final_df, summary], ignore_index=True).style.format({
        "持股數": "{:,.0f}", "總成本": "{:,.0f}", "市值": "{:,.0f}",
        "損益": "{:,.0f}", "報酬%": "{:.2f}%", "年領股息": "{:,.0f}", "殖利率%": "{:.2f}%"
    }))

except Exception as e:
    st.error(f"連線中，請稍候：{e}")
