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
    df['ID'] = df['ID'].astype(str).str.strip()
    return df

# --- 3. 側邊欄：目標管理與多維診斷 ---
st.sidebar.header("🎯 投資目標設定")
annual_target = st.sidebar.number_input("年領股息目標 (TWD)", value=500000, step=10000)

st.sidebar.markdown("---")
st.sidebar.header("🔍 多維度智能診斷")
search_id = st.sidebar.text_input("輸入代碼 (例: 2330.TW)", "2330.TW")

if search_id:
    try:
        tk_diag = yf.Ticker(search_id)
        info_diag = tk_diag.info
        hist_diag = tk_diag.history(period="60d")
        cp_diag = hist_diag['Close'].iloc[-1]
        
        # 綜合診斷因子
        pe_diag = info_diag.get('trailingPE', 0)
        ma20_diag = hist_diag['Close'].tail(20).mean()
        dy_diag = (info_diag.get('dividendRate', 0) / cp_diag * 100) if cp_diag > 0 else 0
        
        st.sidebar.subheader(info_diag.get('shortName', search_id))
        st.sidebar.metric("目前價格", f"{cp_diag:.2f}")
        
        score = 0
        tips = []
        if 0 < pe_diag < 18: score += 25; tips.append("💰 價值：估值合理/偏低")
        if cp_diag > ma20_diag: score += 25; tips.append("🚀 動能：股價短期強勢")
        if dy_diag > 5: score += 25; tips.append("🧧 股息：具備高回報優勢")
        if info_diag.get('debtToEquity', 100) < 80: score += 25; tips.append("🛡️ 財務：債務比例低，體質穩")
        
        st.sidebar.write(f"**綜合投資評分：{score} / 100**")
        for t in tips: st.sidebar.write(t)
    except:
        st.sidebar.error("診斷暫時不可用")

# --- 4. 主畫面邏輯 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ 個人資產決策管理系統</h1>", unsafe_allow_html=True)

# 您的 Google Sheets CSV 連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmeA8nukY_OkQ-2cIVHG5Hzu7ZNyYWgiXRn9JILLe-EX0y7SpA5U2Yt94NT8x4xJRksitesk1ninV4/pub?gid=2040510123&single=true&output=csv"

try:
    raw_df = load_data(SHEET_URL)
    
    # 合併持股邏輯：將重複 ID 的股票加總，計算加權成本
    raw_df['Cost_Part'] = raw_df['Price'] * raw_df['Qty']
    grouped = raw_df.groupby('ID').agg({'Qty': 'sum', 'Cost_Part': 'sum', 'Fee': 'sum'}).reset_index()
    grouped['TotalCost'] = grouped['Cost_Part'] + grouped['Fee']
    
    details = []
    with st.spinner('同步最新股市行情與計算年化股息...'):
        id_list = grouped['ID'].tolist()
        # 批次下載價格避免頻繁請求
        prices = yf.download(id_list, period="5d", group_by='ticker', progress=False)

        for _, row in grouped.iterrows():
            sid = row['ID']
            tk = yf.Ticker(sid)
            # 取得現價
            curr_p = prices[sid]['Close'].iloc[-1] if len(id_list) > 1 else prices['Close'].iloc[-1]
            
            # 自動抓取中文/簡稱 (解決英文名稱亂的問題)
            name = tk.info.get('shortName') or tk.info.get('longName') or sid
            
            # 年度股息推算
            div_rate = tk.info.get('dividendRate', 0)
            if not div_rate:
                div_rate = curr_p * tk.info.get('dividendYield', 0)
            
            mv = curr_p * row['Qty']
            profit = mv - row['TotalCost']
            ann_div = div_rate * row['Qty']
            
            # 管理行動指南信號
            signal = "🟢 持有觀察"
            if profit < -row['TotalCost'] * 0.1: signal = "🔵 價值加碼"
            elif profit > row['TotalCost'] * 0.2: signal = "🔥 獲利減碼"

            details.append({
                "名稱": name, "代碼": sid, "持股數": row['Qty'], "總成本": row['TotalCost'],
                "市值": mv, "損益": profit, "報酬%": (profit/row['TotalCost']*100),
                "年領股息": ann_div, "殖利率%": (div_rate/curr_p*100) if curr_p > 0 else 0,
                "管理信號": signal
            })

    final_df = pd.DataFrame(details)
    total_mv = final_df['市值'].sum()
    total_div = final_df['年領股息'].sum()
    total_c = final_df['總成本'].sum()

    # --- 數據看板與進度條 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("當前總資產 (市值)", f"${total_mv:,.0f}")
    c2.metric("預估年領被動收入", f"${total_div:,.0f}")
    c3.metric("年度目標達成率", f"{(total_div/annual_target*100):.1f}%")
    
    st.write(f"**距離年領 {annual_target:,.0f} 股息目標進度：**")
    st.progress(min(total_div / annual_target, 1.0))

    # --- 視覺化分析與風險警示 ---
    col_chart, col_guide = st.columns([1, 1.2])
    
    with col_chart:
        st.write("### 🍰 資產配置權重")
        fig = px.pie(final_df, values='市值', names='名稱', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

    with col_guide:
        st.write("### 📢 風險控管行動指南")
        # 檢查是否有單一持股佔比過高
        max_stock = final_df.loc[final_df['市值'].idxmax()]
        if (max_stock['市值'] / total_mv) > 0.35:
            st.error(f"⚠️ 警報：**{max_stock['名稱']}** 佔比達 {max_stock['市值']/total_mv*100:.1f}%，風險過於集中。")
        else:
            st.success("✅ 持股分配均衡，風險管控良好。")
            
        # 列出盈虧異常的行動建議
        for _, r in final_df.iterrows():
            if "🔥" in r['管理信號']:
                st.warning(f"🔔 {r['名稱']}：報酬率已達 {r['報酬%']:.1f}%，可考慮部分減碼實現獲利。")
            elif "🔵" in r['管理信號']:
                st.info(f"💎 {r['名稱']}：目前貼息/虧損中，若基本面不變可考慮分批佈局。")

    # --- 底部明細表格與總計 ---
    st.write("### 🗂️ 已合併持股詳細清單")
    summary = pd.DataFrame([{
        "名稱": "✨ 總計", "代碼": "-", "持股數": "-", "總成本": total_c,
        "市值": total_mv, "損益": total_mv - total_c, "報酬%": (total_mv - total_c)/total_c*100,
        "年領股息": total_div, "殖利率%": total_div/total_mv*100, "管理信號": "-"
    }])
    st.table(pd.concat([final_df, summary], ignore_index=True).style.format({
        "持股數": "{:,.0f}", "總成本": "{:,.0f}", "市值": "{:,.0f}",
        "損益": "{:,.0f}", "報酬%": "{:.2f}%", "年領股息": "{:,.0f}", "殖利率%": "{:.2f}%"
    }))

except Exception as e:
    st.error(f"數據更新中，請稍候再刷新 (錯誤: {e})")
