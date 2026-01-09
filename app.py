import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 페이지 설정 및 UI 테마 (시인성 극대화) ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

st.markdown("""
    <style>
    /* 배경 및 기본 텍스트 시인성 확보 */
    .stApp { background-color: #0A0A0B; color: #FFFFFF; }
    
    /* 제목 및 헤더 박스 */
    .header-box { 
        background-color: #161618; padding: 25px; border-radius: 12px; 
        border: 1px solid #333; margin-bottom: 30px; text-align: center;
    }
    .main-title { font-size: 48px; font-weight: 900; color: #FFD700; margin: 0; }
    
    /* 메트릭 텍스트 강조 */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800 !important; font-size: 32px !important; }
    [data-testid="stMetricLabel"] { color: #FFD700 !important; font-weight: bold !important; }
    
    /* 데이터프레임 가독성 */
    .stDataFrame { border: 1px solid #444 !important; background-color: #161618 !important; }
    h1, h2, h3, h4, p, span, div { color: #FFFFFF !important; }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] { background-color: #111112 !important; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 감사 로직 엔진 (Audit Logic) ---
class AuditSystem:
    @staticmethod
    def get_standard_mapping(df):
        """가공된 표준 데이터를 우선적으로 매핑"""
        mapping = {}
        standard_cols = {
            '사용자': ['사용자', '성명', '이용자', '사원명', '성함', 'User'],
            '가맹점': ['가맹점명', '거래처', '상호', '가맹점', '지점명', 'Merchant'],
            '금액': ['이용금액', '금액', '결제금액', '승인금액', '합계', 'Amount'],
            '일시': ['승인일시', '결제일시', '일시', '날짜', '거래일시', 'Date']
        }
        for key, aliases in standard_cols.items():
            for col in df.columns:
                if str(col).strip() in aliases:
                    mapping[key] = col
                    break
        return mapping

    @staticmethod
    def analyze_risk(df, m, n_start, n_end, h_limit):
        """AI 기반 리스크 스코어링"""
        # 데이터 클렌징: 숫자 외 문자 제거 후 변환
        df['P_AMT'] = pd.to_numeric(df[m['금액']].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[m['일시']], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        def calc_score(row):
            score = 0
            reasons = []
            # 1. 심야 시간대 위반
            is_night = (row['P_HOUR'] >= n_start) or (row['P_HOUR'] <= n_end)
            if is_night:
                score += 40
                reasons.append("🌙심야")
            # 2. 고액 결제 위반
            if row['P_AMT'] >= h_limit:
                score += 30
                reasons.append("💰고액")
            # 3. 위장 가맹점 패턴 추론
            fake_keywords = ['유통', '기획', '네트웍스', '컨설팅', '종합']
            if any(k in str(row[m['가맹점']]) for k in fake_keywords) and is_night:
                score += 30
                reasons.append("🔍위장의심")
            
            return pd.Series([score, ", ".join(reasons)])

        df[['risk_score', 'violation']] = df.apply(calc_score, axis=1)
        return df

# --- 3. UI 메인 프로세스 ---
st.markdown('<div class="header-box"><p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p><p style="color:#FFD700; font-size:18px;">통합 감사 데이터 분석 시스템 v1.3</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 감사 기준 설정")
    night_range = st.slider("심야 시간 설정", 0, 23, (23, 6))
    h_limit = st.number_input("고액 기준(원)", value=500000, step=50000)
    st.divider()
    st.markdown("### 📋 표준 규격 안내")
    st.info("파일 내에 [사용자, 가맹점명, 이용금액, 승인일시] 컬럼이 포함되어야 합니다.")

uploaded_file = st.file_uploader("가공된 엑셀(XLSX) 또는 CSV 파일을 업로드하세요.", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # 1. 파일 타입에 따른 로드 및 시트 선택
        if uploaded_file.name.endswith('.xlsx'):
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox("📝 데이터가 있는 시트를 선택하세요", sheet_names)
            else:
                selected_sheet = sheet_names[0]
            df_raw = excel_file.parse(selected_sheet)
        else:
            df_raw = pd.read_csv(uploaded_file)
        
        # 2. 분석 엔진 작동
        audit = AuditSystem()
        mapping = audit.get_standard_mapping(df_raw)
        
        if len(mapping) < 3:
            st.error("❗ 필수 컬럼을 찾을 수 없습니다. 시트 내 컬럼명을 확인해 주세요.")
        else:
            df_analyzed = audit.analyze_risk(df_raw, mapping, night_range[0], night_range[1], h_limit)
            
            # 3. 대시보드 출력 (Metric)
            st.subheader("📊 감사 요약 대시보드")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("총 분석 건수", f"{len(df_analyzed):,}건")
            with c2: st.metric("고위험 대상(High)", f"{len(df_analyzed[df_analyzed['risk_score']>=70])}건")
            with c3: st.metric("주의 대상(Mid)", f"{len(df_analyzed[df_analyzed['risk_score']>=40])}건")

            st.divider()
            
            # 4. 분석 결과 테이블 (Data Editor)
            st.subheader("📋 정밀 검토 대상 리스트 (Risk Score 순)")
            report_df = df_analyzed[df_analyzed['risk_score'] >= 40].sort_values(by='risk_score', ascending=False)
            
            st.data_editor(
                report_df[[mapping['사용자'], mapping['가맹점'], 'P_AMT', mapping['일시'], 'risk_score', 'violation']],
                column_config={
                    "risk_score": st.column_config.ProgressColumn("위험점수", min_value=0, max_value=100, format="%d점"),
                    "P_AMT": st.column_config.NumberColumn("결제금액", format="%d원"),
                    "violation": "위반 사유"
                },
                use_container_width=True, hide_index=True
            )

            # 5. 결과 내보내기
            st.divider()
            csv = report_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 분석 보고서 다운로드 (소명 요청용)",
                data=csv,
                file_name=f"Audit_Report_{datetime.now().strftime('%m%d_%H%M')}.csv",
                mime='text/csv'
            )
            
    except Exception as e:
        st.error(f"⚠️ 데이터를 처리하는 중 오류가 발생했습니다: {e}")
else:
    st.info("💡 파일을 업로드하면 자동으로 AI 분석이 시작됩니다.")
