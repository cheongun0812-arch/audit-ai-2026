import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 페이지 설정 및 디자인 (텍스트 색상 화이트 업데이트)
# =========================================================
st.set_page_config(page_title="Executive & Shared Card Audit", layout="wide")

st.markdown("""
<style>
    :root {
        --bg: #0B0D10;
        --panel: #12151B;
        --gold: #D6B25E;
        --text: #EDEFF4;
        --border: #232836;
    }
    .stApp { 
        background: radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%), var(--bg); 
    }
    .hero { 
        background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%); 
        border: 1px solid var(--border); 
        border-radius: 18px; padding: 25px; margin-bottom: 25px; 
    }
    /* ✅ 제목(Gold) 유지, 나머지 텍스트는 화이트로 설정 */
    .hero p, .panel h4, .stMarkdown p, .stTabs [data-baseweb="tab"] {
        color: #FFFFFF !important;
    }
    
    .panel { 
        background: var(--panel); border: 1px solid var(--border); 
        border-radius: 16px; padding: 20px; margin-bottom: 20px; 
    }
    h1, h2, h3 { color: var(--gold) !important; font-weight: 900 !important; }

    /* ✅ Metric(지표) 라벨 및 값 색상 화이트로 변경 */
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-weight: 900 !important;
    }
    [data-testid="stMetric"] { 
        background: #1A1E26; border: 1px solid #2D3446; 
        border-radius: 12px; padding: 15px; 
    }

    /* 탭 스타일 조정 */
    .stTabs [aria-selected="true"] { background-color: var(--gold) !important; color: #000 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 임원·직책자·공용카드 특화 분석 엔진
# =========================================================
class ComplianceEngine:
    MAP_RULES = {
        "사용자": ["사용자", "성명", "이용자", "User", "성함"],
        "가맹점": ["가맹점명", "상호", "Merchant", "가맹점", "지점"],
        "금액": ["이용금액", "금액", "Amount", "결제금액", "승인금액"],
        "일시": ["승인일시", "결제일시", "일시", "Date", "거래일시"]
    }

    @staticmethod
    def auto_mapping(df):
        mapping = {}
        for key, aliases in ComplianceEngine.MAP_RULES.items():
            for c in df.columns:
                if any(alias in str(c) for alias in aliases):
                    mapping[key] = c
                    break
        return mapping

    @staticmethod
    def run_analysis(df, mapping, keywords):
        df = df.copy()
        u_col, m_col, a_col, t_col = mapping["사용자"], mapping["가맹점"], mapping["금액"], mapping["일시"]

        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 위반 필터
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        pattern = "|".join([re.escape(k.strip()) for k in keywords if k.strip()])
        df['F_RESTRICT'] = df[m_col].astype(str).str.contains(pattern, case=False, na=False)
        
        # 분할 결제 탐지
        df = df.sort_values(by=[u_col, m_col, 'P_DT'])
        df['time_diff'] = df.groupby([u_col, m_col])['P_DT'].diff().dt.total_seconds() / 60
        df['F_SPLIT'] = (df['time_diff'] > 0) & (df['time_diff'] <= 30)

        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT', 'F_SPLIT']].any(axis=1)
        
        def get_reason(row):
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫제한업종")
            if row['F_SPLIT']: r.append("✂️분할의심")
            return " / ".join(r)
        df['비고(위반사유)'] = df.apply(get_reason, axis=1)
        return df

# =========================================================
# 3) 메인 레이아웃 및 분석 실행
# =========================================================
st.markdown("""
<div class="hero">
    <div style="display:flex; align-items:center; gap:15px;">
        <span style="font-size:40px;">🛡️</span>
        <div>
            <h1 style="margin:0; font-size:28px;">Executive & Shared Card Audit Portal</h1>
            <p style="margin:5px 0 0 0;">임원·직책자·공용카드 준법 감시 고도화 시스템 v4.7</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔐 Admin Control")
    admin_pw = st.text_input("관리자 인증", type="password", value="ktmos0402!")
    st.divider()
    kw_text = st.text_area("🚫 제한업종 키워드", "노래방, 주점, 유흥, 마사지, 골프장, 사우나, 면세점", height=120)
    keywords = [k.strip() for k in kw_text.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("🔒 관리자 인증이 필요합니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 RAW 데이터 업로드", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    engine = ComplianceEngine()
    mapping = engine.auto_mapping(df_raw)
    df_final = engine.run_analysis(df_raw, mapping, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # --- Metrics (모두 흰색 텍스트 적용됨) ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔍 검토 내역", f"{len(df_final):,}건")
    c2.metric("🚨 위반 의심 총계", f"{len(viol_df):,}건")
    c3.metric("✂️ 분할결제 의심", f"{df_final['F_SPLIT'].sum():,}건")
    c4.metric("💰 위반 의심 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 위반 리스트", "📊 사용자별 분석", "📥 다운로드"])

    with tab1:
        st.dataframe(viol_df, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### 📊 사용자별 위반 통계 (막대 클릭 시 상세 내역 표시)")
        u_col = mapping["사용자"]
        user_stats = viol_df.groupby(u_col).size().reset_index(name='위반건수').sort_values('위반건수', ascending=False)
        
        # ✅ Plotly 차트 생성 및 선택 이벤트 활성화
        fig = px.bar(user_stats.head(20), x=u_col, y='위반건수', color='위반건수', 
                     color_continuous_scale="OrRd", template="plotly_dark")
        
        # Streamlit 1.35+ 신기능: on_select="rerun"을 통해 클릭 감지
        selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        # ✅ 클릭 시 상세 내역 노출 로직
        if selected_points and selected_points.get("selection") and selected_points["selection"]["points"]:
            # 클릭한 바의 사용자 이름 추출
            selected_user = selected_points["selection"]["points"][0]["x"]
            st.markdown(f"#### 🔍 '{selected_user}'님의 상세 위반 내역 ({user_stats[user_stats[u_col]==selected_user]['위반건수'].values[0]}건)")
            user_detail = viol_df[viol_df[u_col] == selected_user]
            st.dataframe(user_detail, use_container_width=True, hide_index=True)
        else:
            st.info("💡 위 그래프의 막대를 클릭하면 해당 사용자의 상세 위반 내역을 바로 확인할 수 있습니다.")

    with tab3:
        csv_bytes = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 전체 결과 다운로드 (CSV)", csv_bytes, "audit_result.csv", "text/csv", use_container_width=True)
