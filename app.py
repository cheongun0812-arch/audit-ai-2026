import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io

# --- 1. 페이지 설정 및 UI 테마 (시인성 극대화) ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# CSS를 통한 시인성 개선: 배경은 Black, 텍스트는 Off-White, 강조는 Gold/Red
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; margin-bottom: 5px; }
    .header-box { background-color: #161618; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 25px; }
    
    /* 메트릭 및 테이블 시인성 */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800 !important; }
    .stDataFrame { border: 1px solid #444 !important; }
    
    /* 리스크 컬러 코딩 */
    .high-risk { color: #FF4B4B !important; font-weight: bold; }
    .mid-risk { color: #FFA500 !important; font-weight: bold; }
    
    /* 버튼 스타일 */
    .stButton>button { background-color: #FFD700 !important; color: #000 !important; font-weight: bold !important; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 로직 엔진 (Logic Layer) ---
class AuditSystem:
    @staticmethod
    def get_standard_mapping(df):
        """가공된 표준 데이터를 우선적으로 매핑"""
        mapping = {}
        standard_cols = {
            '사용자': ['사용자', '성명', '이용자'],
            '가맹점': ['가맹점명', '거래처', '상호'],
            '금액': ['이용금액', '금액', '결제금액'],
            '일시': ['승인일시', '결제일시', '일시'],
            '업종': ['업종', '분류']
        }
        for key, aliases in standard_cols.items():
            for col in df.columns:
                if str(col).strip() in aliases:
                    mapping[key] = col
                    break
        return mapping

    @staticmethod
    def analyze_risk(df, m, n_start, n_end, h_limit):
        """AI 기반 리스크 스코어링 및 탐지"""
        # 데이터 클렌징
        df['P_AMT'] = pd.to_numeric(df[m['금액']].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[m['일시']], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        def calc(row):
            score = 0
            reasons = []
            # 1. 심야 시간
            is_night = (row['P_HOUR'] >= n_start) or (row['P_HOUR'] <= n_end)
            if is_night:
                score += 40
                reasons.append("🌙심야")
            # 2. 고액 결제
            if row['P_AMT'] >= h_limit:
                score += 30
                reasons.append("💰고액")
            # 3. 위장 가맹점 의심 (AI 패턴)
            fake_keywords = ['유통', '기획', '네트웍스', '컨설팅']
            if any(k in str(row[m['가맹점']]) for k in fake_keywords) and is_night:
                score += 30
                reasons.append("🔍위장의심")
            
            return pd.Series([score, ", ".join(reasons)])

        df[['risk_score', 'violation']] = df.apply(calc, axis=1)
        return df

    @staticmethod
    def detect_split(df, m, window=5):
        """분할 결제(쪼개기) 탐지"""
        df = df.sort_values(by=[m['사용자'], 'P_DT'])
        df['prev_dt'] = df.groupby([m['사용자'], m['가맹점']])['P_DT'].shift(1)
        df['diff_min'] = (df['P_DT'] - df['prev_dt']).dt.total_seconds() / 60
        return df[df['diff_min'] <= window]

# --- 3. UI 메인 루프 ---
st.markdown('<div class="header-box"><p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p><p style="color:#FFD700; font-weight:bold;">Pre-Audit Intelligence System v1.1</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 감사 기준 설정")
    night_range = st.slider("심야 시간 설정", 0, 23, (23, 6))
    h_limit = st.number_input("고액 기준(원)", value=500000, step=50000)
    split_min = st.number_input("분할결제 의심(분)", value=5)
    st.divider()
    st.write("표준 데이터 규격: [사용자, 가맹점명, 이용금액, 승인일시]")

uploaded_file = st.file_uploader("가공된 표준 데이터(CSV/XLSX)를 업로드하세요.", type=['csv', 'xlsx'])

if uploaded_file:
    # 데이터 로드
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 분석 엔진 실행
    audit = AuditSystem()
    mapping = audit.get_standard_mapping(df_raw)
    
    if len(mapping) < 3:
        st.error("❗ 필수 컬럼을 찾을 수 없습니다. [사용자, 가맹점명, 이용금액, 승인일시] 규격을 확인해주세요.")
    else:
        # 분석 프로세스
        df_analyzed = audit.analyze_risk(df_raw, mapping, night_range[0], night_range[1], h_limit)
        split_df = audit.detect_split(df_analyzed, mapping, split_min)
        
        # --- 결과 출력 ---
        st.subheader("📊 감사 분석 요약")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 분석 건수", f"{len(df_analyzed):,}건")
        c2.metric("고위험군(70↑)", f"{len(df_analyzed[df_analyzed['risk_score']>=70])}건")
        c3.metric("주의군(40↑)", f"{len(df_analyzed[(df_analyzed['risk_score']>=40) & (df_analyzed['risk_score']<70)])}건")
        c4.metric("분할결제 의심", f"{len(split_df)}건")

        st.divider()
        
        # 메인 리포트 테이블
        st.subheader("📋 정밀 검토 대상 리스트 (High/Mid Risk)")
        report_df = df_analyzed[df_analyzed['risk_score'] >= 40].sort_values(by='risk_score', ascending=False)
        
        # 시인성 높은 데이터 에디터
        st.data_editor(
            report_df[[mapping['사용자'], mapping['가맹점'], 'P_AMT', mapping['일시'], 'risk_score', 'violation']],
            column_config={
                "risk_score": st.column_config.ProgressColumn("위험도", min_value=0, max_value=100, format="%d점"),
                "P_AMT": st.column_config.NumberColumn("결제금액", format="%d원"),
                "violation": "위반 사유"
            },
            use_container_width=True,
            hide_index=True
        )

        # 분할결제 상세
        if not split_df.empty:
            with st.expander("🔗 분할결제(쪼개기) 의심 세부 내역"):
                st.table(split_df[[mapping['사용자'], mapping['가맹점'], 'P_AMT', mapping['일시'], 'diff_min']])

        # 통합 다운로드 기능
        st.divider()
        csv = report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 최종 감사 보고서 다운로드 (소명 요청용)",
            data=csv,
            file_name=f"Audit_Final_Report_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime='text/csv'
        )
else:
    st.info("💡 가공된 RAW 데이터를 업로드하면 AI 분석 대시보드가 활성화됩니다.")
