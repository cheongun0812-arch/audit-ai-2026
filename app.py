import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

# 1. 시인성 극대화 디자인 (High-Contrast Dark Mode)
st.set_page_config(page_title="2026 Audit System", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; } /* 메인 배경 */
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; } /* 사이드바 배경 */
    [data-testid="stSidebar"] * { color: #111111 !important; font-weight: 800 !important; } /* 사이드바 글씨 */
    h1, h2, h3, p, label, .stMarkdown { color: #FFFFFF !important; } /* 메인 글씨 */
    .hero { background: #1A1E26; border-left: 5px solid #FFD700; padding: 20px; margin-bottom: 25px; }
    [data-testid="stMetric"] { background: #FFFFFF; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; font-weight: 900 !important; }
    .integrated-card { background: #FFFFFF; border-radius: 12px; padding: 20px; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .sub-item { text-align: center; padding: 0 20px; border-left: 1px solid #EEE; }
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], div[data-testid="stFileUploader"] small { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# 2. 실무 최적화 분석 엔진
class SimpleAuditEngine:
    @staticmethod
    def run(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 기본 필터: 심야(23-06), 휴일(토/일)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 금지업종 및 화이트리스트 (차량운전비, 카카오, 지점명 예외)
        def check(row):
            user, merchant = str(row[u_col]), str(row[m_col])
            if "차량운전비" in user: return False # 최우선 제외
            if "카카오" in merchant: return False # 업무용 서비스 제외
            for kw in keywords:
                if kw in merchant:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant): continue # 지점명 예외
                    return True
            return False
        
        df['F_RESTRICT'] = df.apply(check, axis=1)
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫업종")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

# 3. 화면 구성
st.markdown('<div class="hero"><h1>🛡️ Card Audit AI</h1><p style="color:#FFD700;">SIMPLE IS BEST : 실무자 맞춤형 검증 v5.9</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Setting")
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    kw_input = st.text_area("🚫 금지 키워드", "주점,노래방,유흥,마사지,골프장,사우나,귀금속,백화점,면세점", height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw == "ktmos0402!" and (uploaded_file := st.file_uploader("파일 업로드 (CSV/Excel)", type=['xlsx', 'csv'])):
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df_final = SimpleAuditEngine.run(df_raw, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # 통합 지표 카드
    c1, c2, c3 = st.columns([1, 3, 1.5])
    c1.metric("🔍 전체", f"{len(df_final):,}건")
    with c2:
        st.markdown(f"""<div class="integrated-card">
            <div style="padding-right:20px;">
                <div style="color:#333; font-weight:700;">🚨 검토 필요</div>
                <div style="color:#D62728; font-size:2rem; font-weight:900;">{len(viol_df):,}건</div>
            </div>
            <div class="sub-item"><div style="color:#666; font-size:0.8rem;">🌙 심야</div><div style="color:#111; font-weight:800;">{df_final['F_NIGHT'].sum()}건</div></div>
            <div class="sub-item"><div style="color:#666; font-size:0.8rem;">📅 휴일</div><div style="color:#111; font-weight:800;">{df_final['F_WEEKEND'].sum()}건</div></div>
            <div class="sub-item"><div style="color:#666; font-size:0.8rem;">🚫 업종</div><div style="color:#111; font-weight:800;">{df_final['F_RESTRICT'].sum()}건</div></div>
        </div>""", unsafe_allow_html=True)
    c3.metric("💰 의심 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.divider()
    tab1, tab2 = st.tabs(["📋 위반 리스트", "📊 사용자별 분석"])
    with tab1: st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)
    with tab2:
        st.markdown("#### 👤 사용자별 건수 (클릭 시 상세 조회)")
        stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        fig = px.bar(stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
        if (sel := st.plotly_chart(fig, use_container_width=True, on_select="rerun")) and sel.get("selection") and sel["selection"]["points"]:
            user = sel["selection"]["points"][0]["x"]
            st.markdown(f"<h3 style='color:#FFD700;'>📄 {user} 님의 상세 내역</h3>", unsafe_allow_html=True)
            st.dataframe(viol_df[viol_df['사용자'] == user], use_container_width=True)
    
    st.download_button("📥 결과 다운로드 (CSV)", df_final.to_csv(index=False).encode('utf-8-sig'), "Audit_Result.csv", use_container_width=True)
else:
    st.info("💡 파일을 업로드하면 분석이 시작됩니다.")
