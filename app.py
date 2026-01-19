import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
import io
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) PAGE CONFIG & 고유 디자인 (기존 CSS 스타일 계승)
# =========================================================
st.set_page_config(page_title="Executive Card Audit Portal", layout="wide")

st.markdown("""
<style>
    :root {
        --bg: #0B0D10;
        --panel: #12151B;
        --gold: #D6B25E;
        --text: #EDEFF4;
    }
    .stApp { background: radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%), var(--bg); color: var(--text); }
    .hero { background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%); border: 1px solid #232836; border-radius: 18px; padding: 20px; margin-bottom: 20px; }
    .panel { background: #12151B; border: 1px solid #232836; border-radius: 16px; padding: 20px; margin-bottom: 15px; }
    h1, h2, h3 { color: var(--gold) !important; font-weight: 900 !important; }
    [data-testid="stMetric"] { background: #1A1E26; border: 1px solid #2D3446; border-radius: 12px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 고도화된 분석 엔진 (직책자/공용카드 특화)
# =========================================================
class ExecutiveAuditEngine:
    # 자동 컬럼 매핑 로직
    COLUMN_MAP = {
        "사용자": ["사용자", "성명", "이용자", "User", "성함"],
        "가맹점": ["가맹점명", "상호", "Merchant", "가맹점"],
        "금액": ["이용금액", "금액", "Amount", "결제금액", "승인금액"],
        "일시": ["승인일시", "결제일시", "일시", "Date", "거래일시"]
    }

    @staticmethod
    def get_mapping(df):
        mapping = {}
        for key, aliases in ExecutiveAuditEngine.COLUMN_MAP.items():
            for col in df.columns:
                if any(alias in str(col) for alias in aliases):
                    mapping[key] = col
                    break
        return mapping

    @staticmethod
    def run_audit(df, mapping, restricted_kws):
        df = df.copy()
        u_col = mapping.get("사용자", "미지정")
        m_col = mapping["가맹점"]
        a_col = mapping["금액"]
        t_col = mapping["일시"]

        # 데이터 전처리
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        df['P_DATE'] = df['P_DT'].dt.date

        # 위반 필터 1: 심야 사용 (23시-06시)
        df['V_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # 위반 필터 2: 휴일 사용 (주말)
        df['V_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 위반 필터 3: 제한업종 (키워드 매칭)
        pattern = "|".join([re.escape(k.strip()) for k in restricted_kws if k.strip()])
        df['V_RESTRICT'] = df[m_col].astype(str).str.contains(pattern, case=False, na=False)
        
        # 위반 필터 4: 분할 결제 탐지 (30분 이내 동일가맹점 재결제)
        df = df.sort_values(by=[u_col, m_col, 'P_DT'])
        df['time_diff'] = df.groupby([u_col, m_col])['P_DT'].diff().dt.total_seconds() / 60
        df['V_SPLIT'] = (df['time_diff'] > 0) & (df['time_diff'] <= 30)

        # 종합 판정
        df['IS_VIOLATION'] = df[['V_NIGHT', 'V_WEEKEND', 'V_RESTRICT', 'V_SPLIT']].any(axis=1)
        
        def build_reason(row):
            reasons = []
            if row['V_NIGHT']: reasons.append("🌙심야")
            if row['V_WEEKEND']: reasons.append("📅휴일")
            if row['V_RESTRICT']: reasons.append("🚫제한업종")
            if row['V_SPLIT']: reasons.append("✂️분할의심")
            return " / ".join(reasons)
            
        df['위반사유'] = df.apply(build_reason, axis=1)
        return df

# =========================================================
# 3) UI 구성 (메인 화면 및 사이드바)
# =========================================================
st.markdown("""
<div class="hero">
    <h1 style='margin:0;'>🛡️ Executive Compliance Audit</h1>
    <p style='color:#B9C2D6; margin-top:5px;'>임원·직책자·공용카드 전용 고도화 모니터링 시스템 v4.5</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=80)
    st.title("Admin Setting")
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    
    st.divider()
    st.markdown("### 🚫 제한 키워드 설정")
    kw_input = st.text_area("쉼표(,)로 구분", "노래방, 주점, 유흥, 마사지, 골프장, 사우나, 백화점, 면세점", height=150)
    keywords = kw_input.split(',')
    
    st.divider()
    st.caption("© 2026 Audit AI Solution. All rights reserved.")

# 비밀번호 보안 (임시 설정: ktmos0402!)
if admin_pw != "ktmos0402!":
    st.warning("🔒 관리자 인증이 필요합니다.")
    st.stop()

# 파일 업로드 섹션
st.markdown('<div class="panel">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("법인카드 사용이력 RAW 데이터를 업로드하세요 (Excel/CSV)", type=['xlsx', 'csv'])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    # 데이터 로드
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        
        engine = ExecutiveAuditEngine()
        mapping = engine.get_mapping(df_raw)
        
        # 필수 컬럼 체크
        if not all(k in mapping for k in ["가맹점", "금액", "일시"]):
            st.error("❌ 데이터 형식이 맞지 않습니다. 가맹점, 금액, 일시 컬럼이 포함되어야 합니다.")
            st.stop()

        # 분석 실행
        df_final = engine.run_audit(df_raw, mapping, keywords)
        
        # --- 4) 상단 요약 지표 (Metrics) ---
        viol_df = df_final[df_final['IS_VIOLATION']]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 검토 건수", f"{len(df_final):,}건")
        c2.metric("🚨 위반 의심 건수", f"{len(viol_df):,}건")
        c3.metric("✂️ 분할결제 탐지", f"{df_final['V_SPLIT'].sum():,}건")
        c4.metric("💰 위반 의심 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

        st.markdown("---")

        # --- 5) 고도화 대시보드 (Tabs) ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 위반 현황판", "✂️ 분할결제 집중관리", "👤 직책자별 통계", "⬇️ 데이터 내보내기"])

        with tab1:
            st.subheader("🚩 위반 의심 상세 내역")
            st.dataframe(viol_df, use_container_width=True)

        with tab2:
            st.subheader("✂️ 분할 결제(쪼개기) 의심 사례")
            st.info("동일 가맹점에서 30분 이내에 연속 결제된 내역입니다. 인당 한도 회피 여부를 확인하십시오.")
            split_df = df_final[df_final['V_SPLIT'] == True]
            st.dataframe(split_df, use_container_width=True)

        with tab3:
            st.subheader("👤 직책자/공용카드 사용자별 위반 분포")
            u_col = mapping.get("사용자", "사용자")
            user_stats = viol_df.groupby(u_col).size().reset_index(name='건수').sort_values('건수', ascending=False)
            
            # 

[Image of X]
 차트 시각화
            fig = px.bar(user_stats.head(15), x=u_col, y='건수', color='건수', 
                         title="상위 15인 위반 빈도 분석", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("📥 분석 결과 다운로드")
            col_d1, col_d2 = st.columns(2)
            
            # CSV 다운로드
            csv_data = df_final.to_csv(index=False).encode('utf-8-sig')
            col_d1.download_button("CSV로 저장", csv_data, "audit_result.csv", "text/csv", use_container_width=True)
            
            # Excel 다운로드 (openpyxl 필요)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Audit_Result')
            col_d2.download_button("Excel로 저장", output.getvalue(), "audit_result.xlsx", use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ 분석 중 오류가 발생했습니다: {e}")
else:
    st.info("💡 분석을 시작하려면 법인카드 RAW 데이터를 업로드해 주세요.")
