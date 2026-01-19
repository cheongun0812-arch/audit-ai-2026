import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 보색 대비 및 시각적 레이아웃 디자인
# =========================================================
st.set_page_config(page_title="2026 Audit System", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: #111111 !important; font-weight: 800 !important;
    }
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"], label {
        color: #FFFFFF !important;
    }
    .main-white-text { color: #FFFFFF !important; font-weight: 700 !important; }
    
    /* 파일 업로드 텍스트 화이트닝 */
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], 
    [data-testid="stFileUploaderFileData"] > div, div[data-testid="stFileUploader"] small { 
        color: #FFFFFF !important; 
    }

    .hero {
        background: #1A1E26; border-left: 5px solid #FFD700;
        padding: 20px; margin-bottom: 25px;
    }
    
    /* ✅ 지표(Metric) 박스 디자인 개선 */
    [data-testid="stMetric"] {
        background: #FFFFFF; border-radius: 10px; padding: 15px;
    }
    [data-testid="stMetricLabel"] { color: #111111 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; font-weight: 900 !important; }
    
    /* 세부 건수 표시용 배지 스타일 */
    .sub-metric-box {
        background: #252A34; border: 1px solid #444; border-radius: 8px;
        padding: 10px; text-align: center; color: #FFFFFF;
    }
    .sub-metric-label { font-size: 0.8rem; color: #8791A6; margin-bottom: 2px; }
    .sub-metric-value { font-size: 1.1rem; font-weight: 800; color: #FFD700; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 분석 엔진 (차량운전비 완전 제외 및 세부 카운트)
# =========================================================
class AuditEngineV5_7:
    @staticmethod
    def run_analysis(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 1. 심야 (23-06시)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        # 2. 휴일 (토/일)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 3. 금지업종 및 화이트리스트 (차량운전비/카카오 제외)
        def check_compliance(row):
            user, merchant = str(row[u_col]), str(row[m_col])
            if "차량운전비" in user: return False
            if "카카오업무택시" in merchant or "카카오T비즈" in merchant: return False
            for kw in keywords:
                if kw in merchant:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant): continue
                    return True
            return False

        df['F_RESTRICT'] = df.apply(check_compliance, axis=1)
        
        # ✅ 차량운전비는 어떤 위반 조건에서도 무조건 제외 처리
        is_car_fee = df[u_col].astype(str).str.contains("차량운전비", na=False)
        df.loc[is_car_fee, ['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']] = False

        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫금지업종")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

# =========================================================
# 3) 메인 화면 구성
# =========================================================
st.markdown("""
<div class="hero">
    <h1 style="margin:0;">🛡️ Corporate Card Audit AI</h1>
    <p style="color:#FFD700; margin:5px 0 0 0;">실무 최적화 준법 감시 시스템 v5.7 (세부 지표 강화)</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ 검증 설정")
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    st.divider()
    st.markdown("## 🚫 집중 모니터링 업종")
    kw_input = st.text_area("쉼표 구분", "주점, 노래방, 유흥, 마사지, 골프장, 사우나, 귀금속, 백화점, 면세점", height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("인증이 필요합니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 내역 파일 업로드", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    engine = AuditEngineV5_7()
    df_final = engine.run_analysis(df_raw, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # --- ✅ 상단 세부 지표 레이아웃 개편 ---
    # 지표 행 구성: 총 검토(2) | 검토 필요(2) | 세부 내역(4) | 의심 금액(2)
    m1, m2, m3, m4, m5, m6 = st.columns([1.5, 1.5, 1, 1, 1, 2])
    
    m1.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
    m2.metric("🚨 검토 필요 건", f"{len(viol_df):,}건")
    
    # 검토 필요 건 우측 빈 공간에 세부 항목별 건수 배치
    with m3:
        st.markdown(f'<div class="sub-metric-box"><div class="sub-metric-label">🌙 심야</div><div class="sub-metric-value">{df_final["F_NIGHT"].sum()}건</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="sub-metric-box"><div class="sub-metric-label">📅 휴일</div><div class="sub-metric-value">{df_final["F_WEEKEND"].sum()}건</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="sub-metric-box"><div class="sub-metric-label">🚫 업종</div><div class="sub-metric-value">{df_final["F_RESTRICT"].sum()}건</div></div>', unsafe_allow_html=True)
    
    m6.metric("💰 검토 금액 합계", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.markdown("---")
    tab1, tab2 = st.tabs(["📋 검토 필요 내역", "📊 사용자별 분석"])
    
    with tab1:
        st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown('<p class="main-white-text">👤 사용자별 추출 건수 (그래프 클릭 시 하단 상세 표시)</p>', unsafe_allow_html=True)
        user_stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        fig = px.bar(user_stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
        sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        
        if sel and sel.get("selection") and sel["selection"]["points"]:
            user = sel["selection"]["points"][0]["x"]
            st.markdown(f'<h3 style="color:#FFD700 !important; margin-top:20px;">📄 {user} 님의 상세 내역</h3>', unsafe_allow_html=True)
            st.dataframe(viol_df[viol_df['사용자'] == user], use_container_width=True)

    csv_out = df_final.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 분석 결과 다운로드 (CSV)", csv_out, "Audit_Result_Final.csv", use_container_width=True)
