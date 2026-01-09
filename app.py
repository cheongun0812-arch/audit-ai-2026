import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 페이지 설정 및 시각 요소 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; margin-bottom: 10px; }
    .sub-title { font-size: 18px; color: #AAAAAA; margin-bottom: 30px; }
    .status-card { 
        background: #161618; border-left: 5px solid #FF4B4B; padding: 20px; 
        border-radius: 10px; margin-bottom: 20px;
    }
    .audit-label { font-weight: bold; color: #FF4B4B; }
    .stDataFrame { border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 감사 엔진 클래스 (Logic Layer) ---
class AuditEngine:
    @staticmethod
    def infer_category_risk(row, night_start, night_end):
        """AI 업종 추론 로직: 가맹점명과 결제시간을 분석"""
        score = 0
        reasons = []
        
        # 1. 심야 시간대 위반 (기본 규칙)
        is_night = (row['hour'] >= night_start) or (row['hour'] <= night_end)
        if is_night:
            score += 40
            reasons.append("🌙 심야사용")

        # 2. 위장 가맹점 추론 (AI 패턴 매칭)
        hidden_keywords = ['유통', '기획', '네트웍스', '컨설팅', '종합']
        if any(k in row['가맹점명'] for k in hidden_keywords) and is_night:
            score += 30
            reasons.append("🔍 위장가맹점 의심(심야 결제)")
            
        # 3. 고액 결제
        if row['이용금액'] >= 500000:
            score += 30
            reasons.append("💰 고액결제")

        return pd.Series([score, ", ".join(reasons)])

    @staticmethod
    def detect_split_payments(df, window_min=5):
        """분할 결제 탐지 (동일인, 동일가맹점, n분 이내)"""
        df = df.sort_values(by=['사용자', '승인일시'])
        df['prev_time'] = df.groupby(['사용자', '가맹점명'])['승인일시'].shift(1)
        df['time_diff'] = (df['승인일시'] - df['prev_time']).dt.total_seconds() / 60
        return df[df['time_diff'] <= window_min]

# --- 3. 헤더 및 사이드바 제어 ---
st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">데이터 업로드 및 이상징후 탐지 단계 (Pre-Audit Analysis)</p>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.header("⚙️ 감사 기준 설정")
    night_start = st.slider("심야 시작(시)", 0, 23, 23)
    night_end = st.slider("심야 종료(시)", 0, 23, 6)
    high_limit = st.number_input("고액 결제 기준(원)", value=500000)
    split_min = st.number_input("분할결제 의심(분)", value=5)
    st.divider()
    st.info("설정한 기준에 따라 AI가 위험 점수를 자동으로 계산합니다.")

# --- 4. 데이터 로드 및 전처리 ---
uploaded_file = st.file_uploader("법인카드 사용내역(CSV/XLSX)을 업로드하세요", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # 데이터 읽기
        df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        # [데이터 정제] 컬럼 매핑 자동화 (예시 기반 최적화)
        # 실제 환경에선 사용자 파일의 컬럼명에 맞춰 수정 필요
        # 예시: '거래처명'->'가맹점명', '승인일자'->'날짜' 등
        df = df_raw.copy()
        # (편의상 시뮬레이션을 위해 컬럼명 표준화 로직 생략, 실제 업로드 데이터 컬럼 기준)
        
        # 시간/날짜 전처리
        df['승인일시'] = pd.to_datetime(df['승인일시'])
        df['hour'] = df['승인일시'].dt.hour
        df['날짜'] = df['승인일시'].dt.date
        df['이용금액'] = pd.to_numeric(df['이용금액'], errors='coerce').fillna(0)

        # --- 5. AI 분석 실행 ---
        # 1) 위험 점수 및 사유 계산
        df[['risk_score', 'violation_type']] = df.apply(
            lambda x: AuditEngine.infer_category_risk(x, night_start, night_end), axis=1
        )
        
        # 2) 분할 결제 탐지
        split_cases = AuditEngine.detect_split_payments(df, split_min)
        
        # --- 6. 결과 화면 구성 (Output) ---
        
        # A. 상단 요약 지표
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 분석 건수", f"{len(df)}건")
        m2.metric("위험(High) 건수", f"{len(df[df['risk_score'] >= 70])}건", delta_color="inverse")
        m3.metric("주의(Mid) 건수", f"{len(df[(df['risk_score'] < 70) & (df['risk_score'] >= 40)])}건")
        m4.metric("분할결제 의심", f"{len(split_cases)}건")

        st.divider()

        # B. 핵심 리스크 리스트 (데이터 에디터)
        st.subheader("🚨 정밀 검토 및 소명 요청 대상")
        target_display = df[df['risk_score'] >= 40].sort_values(by='risk_score', ascending=False)
        
        st.data_editor(
            target_display[['risk_score', 'violation_type', '사용자', '가맹점명', '이용금액', '승인일시']],
            column_config={
                "risk_score": st.column_config.ProgressColumn("위험 점수", min_value=0, max_value=100, format="%d"),
                "violation_type": "위반 사유",
                "이용금액": st.column_config.NumberColumn("금액", format="%d원")
            },
            use_container_width=True,
            hide_index=True,
            key="audit_editor"
        )

        # C. 추가 분석: 분할 결제 의심 상세
        if not split_cases.empty:
            with st.expander("🔗 분할 결제(쪼개기) 의심 상세 내역"):
                st.write("동일 가맹점에서 짧은 시간 내에 연속 결제된 내역입니다.")
                st.table(split_cases[['사용자', '가맹점명', '이용금액', '승인일시', 'time_diff']])

        # D. 오프라인 프로세스 연결 (리포트 내보내기)
        st.divider()
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            csv = target_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 소명 요청용 리스트 다운로드 (CSV)",
                data=csv,
                file_name=f"audit_request_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )
        with col_btn2:
            if st.button("📧 선택 항목 사용자에게 소명 메일 발송 (시뮬레이션)"):
                st.success("해당 실무자들에게 시스템 소명 요청 알림이 발송되었습니다.")

    except Exception as e:
        st.error(f"데이터 분석 중 오류가 발생했습니다. 컬럼명을 확인해주세요. 오류: {e}")
else:
    # 파일 업로드 전 가이드 화면
    st.info("상단에 법인카드 지출 내역 파일을 업로드하면 AI 분석이 시작됩니다.")