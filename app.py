import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 가독성 극대화 디자인 (High Contrast Design)
# =========================================================
st.set_page_config(page_title="2026 Compliance Audit", layout="wide")

st.markdown("""
<style>
    :root {
        --bg: #0E1117;       /* 짙은 배경 */
        --panel: #1A1E26;    /* 패널 배경 */
        --gold: #FFD700;     /* 포인트 컬러 (금색) */
        --pure-white: #FFFFFF; /* 순백색 (텍스트) */
        --border: #30363D;
    }
    .stApp { background-color: var(--bg); }
    
    /* 텍스트 가독성: 어두운 배경에는 반드시 밝은 흰색 사용 */
    h1, h2, h3, .hero p, .stMarkdown, p, label { 
        color: var(--pure-white) !important; 
    }
    
    .hero { 
        background: linear-gradient(135deg, #1A1E26 0%, #2D3446 100%);
        border: 2px solid var(--gold);
        border-radius: 15px; padding: 30px; margin-bottom: 25px;
    }

    /* 지표(Metric) 박스 가독성 */
    [data-testid="stMetric"] {
        background: #252A34; border: 1px solid var(--border);
        border-radius: 12px; padding: 20px;
    }
    [data-testid="stMetricLabel"] { color: var(--pure-white) !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: var(--gold) !important; font-size: 2rem !important; }

    /* 데이터프레임 폰트 조절 */
    .stDataFrame { background: white; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 재원운영기준 기반 분석 로직
# =========================================================
class RealWorldAuditEngine:
    @staticmethod
    def run_analysis(df, keywords):
        # 필수 컬럼 매핑 (사용자 데이터 구조 반영)
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # --- [규정 준수 기준] ---
        # 1. 심야 사용: 23시 이후 ~ 익일 06시 이전 사용 건
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # 2. 휴일 사용: 토요일, 일요일 사용 건
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 3. 제한업종: PDF 지침에 명시된 불인정 업종 (유흥, 골프, 마사지 등)
        pattern = "|".join([re.escape(k.strip()) for k in keywords if k.strip()])
        df['F_RESTRICT'] = df[m_col].astype(str).str.contains(pattern, case=False, na=False)
        
        # 4. 분할 결제: 동일 가맹점, 동일 날짜 30분 이내 결제 (한도 회피 방지)
        df = df.sort_values(by=[u_col, m_col, 'P_DT'])
        df['time_diff'] = df.groupby([u_col, m_col])['P_DT'].diff().dt.total_seconds() / 60
        df['F_SPLIT'] = (df['time_diff'] > 0) & (df['time_diff'] <= 30)

        # 5. 종합 판정 (하나라도 해당되면 '검토 필요')
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT', 'F_SPLIT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫금지업종")
            if row['F_SPLIT']: r.append("✂️분할의심")
            reasons.append(" / ".join(r))
        df['위반사유'] = reasons
        return df

# =========================================================
# 3) UI 구성 및 실행
# =========================================================
st.markdown(f"""
<div class="hero">
    <h1 style="margin:0; font-size:32px; color:#FFD700 !important;">🛡️ Compliance Audit System</h1>
    <p style="margin-top:10px; font-size:16px;">재원운영기준(v2025.09) 기반 실무자 맞춤형 자동 검증 솔루션</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Password", type="password", value="ktmos0402!")
    st.divider()
    # PDF 지침 기반 기본 금지 키워드 설정
    default_kws = "노래방, 단란주점, 유흥, 마사지, 골프장, 사우나, 백화점, 면세점, 귀금속, 성인용품"
    kw_input = st.text_area("🚫 금지업종 키워드 (지침 반영)", default_kws, height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if pw != "ktmos0402!":
    st.warning("관리자 인증이 필요합니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 RAW 데이터 업로드 (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 분석 실행
    engine = RealWorldAuditEngine()
    df_final = engine.run_analysis(df_raw, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]

    # 상단 지표 (보색 대비 적용)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
    c2.metric("🚨 위반 의심 건", f"{len(viol_df):,}건")
    c3.metric("✂️ 분할결제 의심", f"{df_final['F_SPLIT'].sum():,}건")
    c4.metric("💰 의심 금액 합계", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 위반 의심 상세 리스트", "📊 직책자/공용별 분포"])

    with tab1:
        st.markdown("#### 🚩 실무 검토 대상 (기준 미준수 건)")
        st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '위반사유']], 
                     use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### 👤 사용자별 위반 건수 (클릭 시 상세 조회)")
        user_stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        
        fig = px.bar(user_stats.head(20), x='사용자', y='건수', color='건수',
                     color_continuous_scale="Reds", template="plotly_dark")
        selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        if selected_points and selected_points.get("selection") and selected_points["selection"]["points"]:
            sel_user = selected_points["selection"]["points"][0]["x"]
            st.markdown(f"#### 🔍 {sel_user} 님의 위반 의심 내역")
            st.dataframe(viol_df[viol_df['사용자'] == sel_user], use_container_width=True)

    # 내보내기
    st.markdown("---")
    csv = df_final.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 분석 결과 다운로드 (CSV)", csv, "Audit_Result.csv", use_container_width=True)
