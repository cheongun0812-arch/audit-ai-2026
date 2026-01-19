import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

# 1. [디자인 복구] v5.9의 고대비 다크 모드 CSS 그대로 적용
st.set_page_config(page_title="2026 Audit System", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; } /* 메인 배경 */
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; } /* 사이드바 밝게 */
    [data-testid="stSidebar"] * { color: #111111 !important; font-weight: 800 !important; }
    h1, h2, h3, p, label, .stMarkdown { color: #FFFFFF !important; }
    
    .hero { background: #1A1E26; border-left: 5px solid #FFD700; padding: 20px; margin-bottom: 25px; }
    
    /* 지표(Metric) 박스 v5.9 스타일 복구 */
    [data-testid="stMetric"] { background: #FFFFFF; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; font-weight: 900 !important; }
    
    /* 통합 지표 카드 v5.8 스타일 복구 */
    .integrated-card { background: #FFFFFF; border-radius: 12px; padding: 20px; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .sub-item { text-align: center; padding: 0 20px; border-left: 1px solid #EEE; }
    .sub-label { color: #666; font-size: 0.8rem; font-weight: 700; }
    .sub-value { color: #111; font-weight: 800; font-size: 1.2rem; }
    
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], div[data-testid="stFileUploader"] small { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# 2. 분석 엔진 (로직 완전 분리)
class AuditEngineV6:
    @staticmethod
    def card_audit(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        def check_rest(row):
            u, m = str(row[u_col]), str(row[m_col])
            if "차량운전비" in u or "카카오" in m: return False
            for kw in keywords:
                if kw in m:
                    if kw == "주점" and re.search(r"[가-힣]주점$", m): continue
                    return True
            return False
        df['F_RESTRICT'] = df.apply(check_rest, axis=1)
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        df['검토사유'] = df.apply(lambda r: " / ".join([s for c, s in zip(['F_NIGHT','F_WEEKEND','F_RESTRICT'], ["🌙심야","📅휴일","🚫업종"]) if r[c]]), axis=1)
        return df

    @staticmethod
    def fuel_audit(df, price):
        u_col, a_col, t_col = "사용자", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['EST_LITER'] = df['P_AMT'] / price
        df['F_OVER'] = df['EST_LITER'] > 75 # 임시 기준
        df['F_WEEK'] = df['P_DT'].dt.weekday >= 5
        df['IS_VIOLATION'] = df[['F_OVER', 'F_WEEK']].any(axis=1)
        df['검토사유'] = df.apply(lambda r: " / ".join([s for c, s in zip(['F_OVER','F_WEEK'], ["⛽용량의심","📅휴일주유"]) if r[c]]), axis=1)
        return df

# 3. 사이드바 메뉴 (UI 선택)
with st.sidebar:
    st.markdown("## ⚙️ Audit Menu")
    menu = st.radio("분석 대상을 선택하세요", ["💳 일반 법인카드", "⛽ 차량주유카드"])
    st.divider()
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    if menu == "💳 일반 법인카드":
        kw_input = st.text_area("🚫 금지 키워드", "주점,노래방,유흥,마사지,골프장,사우나,귀금속,백화점,면세점", height=150)
        keywords = [k.strip() for k in kw_input.split(",")]
    else:
        fuel_price = st.number_input("⛽ 리터당 평균 유가", value=1650)

# 4. 메인 화면 구성
if admin_pw == "ktmos0402!":
    if menu == "💳 일반 법인카드":
        st.markdown('<div class="hero"><h1>🛡️ Card Audit AI</h1><p style="color:#FFD700;">SIMPLE IS BEST : 법인카드 검증 모드</p></div>', unsafe_allow_html=True)
        if (file := st.file_uploader("법인카드 내역 업로드", type=['xlsx', 'csv'])):
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df_res = AuditEngineV6.card_audit(df, keywords)
            viol = df_res[df_res['IS_VIOLATION']]
            
            # v5.8 통합 지표 레이아웃 완벽 복구
            c1, c2, c3 = st.columns([1, 3, 1.5])
            c1.metric("🔍 전체", f"{len(df_res):,}건")
            with c2:
                st.markdown(f"""<div class="integrated-card">
                    <div style="padding-right:30px; border-right:2px solid #EEE;">
                        <div class="metric-label">🚨 검토 필요</div>
                        <div style="color:#D62728; font-size:2.2rem; font-weight:900;">{len(viol):,}건</div>
                    </div>
                    <div class="metric-sub-container" style="display:flex; flex-grow:1; justify-content:space-around;">
                        <div class="sub-item"><div class="sub-label">🌙 심야</div><div class="sub-value">{df_res['F_NIGHT'].sum()}건</div></div>
                        <div class="sub-item"><div class="sub-label">📅 휴일</div><div class="sub-value">{df_res['F_WEEKEND'].sum()}건</div></div>
                        <div class="sub-item"><div class="sub-label">🚫 업종</div><div class="sub-value">{df_res['F_RESTRICT'].sum()}건</div></div>
                    </div>
                </div>""", unsafe_allow_html=True)
            c3.metric("💰 의심 금액", f"{viol['P_AMT'].sum():,.0f}원")
            
            st.divider()
            t1, t2 = st.tabs(["📋 위반 리스트", "📊 사용자 분석"])
            with t1: st.dataframe(viol[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)
            with t2:
                stats = viol.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
                fig = px.bar(stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
                if (sel := st.plotly_chart(fig, use_container_width=True, on_select="rerun")) and sel.get("selection") and sel["selection"]["points"]:
                    u = sel["selection"]["points"][0]["x"]
                    st.markdown(f"<h3 style='color:#FFD700;'>📄 {u} 님의 상세 내역</h3>", unsafe_allow_html=True)
                    st.dataframe(viol[viol['사용자'] == u], use_container_width=True)

    elif menu == "⛽ 차량주유카드":
        st.markdown('<div class="hero"><h1>⛽ Fuel Audit AI</h1><p style="color:#FFD700;">차량 주유비 전용 검증 모드</p></div>', unsafe_allow_html=True)
        if (file := st.file_uploader("주유카드 내역 업로드", type=['xlsx', 'csv'])):
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df_res = AuditEngineV6.fuel_audit(df, fuel_price)
            viol = df_res[df_res['IS_VIOLATION']]
            
            c1, c2, c3 = st.columns([1, 2, 1])
            c1.metric("🔍 총 주유", f"{len(df_res):,}건")
            c2.metric("🚨 의심 건수", f"{len(viol):,}건")
            c3.metric("💰 주유 금액", f"{viol['P_AMT'].sum():,.0f}원")
            st.divider()
            st.dataframe(viol[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True)

else:
    st.info("💡 사이드바에서 메뉴를 선택하고 비밀번호를 입력해 주세요.")
