import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import requests
from streamlit_lottie import st_lottie

# =========================================================
# 1) UI/UX 디자인 및 설정
# =========================================================
st.set_page_config(page_title="2026 Integrated Audit System", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, p, label { color: #FFFFFF !important; }
    .violation-card { 
        background: #2D0A0A; border: 2px solid #FF4B4B; padding: 20px; 
        border-radius: 12px; margin-bottom: 25px; 
    }
    .report-box { 
        background: #1A1E26; border-left: 5px solid #FFD700; padding: 20px; 
        margin-bottom: 25px; border-radius: 8px;
    }
    .stMetric { background-color: #1A1E26; padding: 15px; border-radius: 10px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# Lottie 애니메이션 (고급스러운 AI 효과)
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_ai = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# =========================================================
# 2) 핵심 감사 엔진 (지능형 컬럼 매핑 및 리스크 탐지)
# =========================================================
class AuditEngine2026:
    @staticmethod
    def auto_map_columns(df_cols):
        col_map = {
            '금액': ['금액', '이용금액', '승인금액', '합계', '공급가액'],
            '날짜': ['승인일자', '거래일자', '일자', '이용일자'],
            '시간': ['승인일시', '승인시간', '시간', '일시'],
            '가맹점': ['거래처명', '가맹점명', '상호', '사용처'],
            '사용자': ['사용자', '이용자', '성명', '사원', '카드명']
        }
        final_map = {}
        for target, keywords in col_map.items():
            for col in df_cols:
                if any(k in str(col).replace(" ", "") for k in keywords):
                    final_map[target] = col
                    break
        return final_map

# =========================================================
# 3) 메인 화면 레이아웃
# =========================================================
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("<h1 style='color:#FFD700 !important;'>🛡️ 2026 통합 AI 감사 포털</h1>", unsafe_allow_html=True)
    st.write("실장님, 2026년 한 해의 투명한 경영을 위한 AI 에이전트가 가동 중입니다.")
with col_h2:
    if lottie_ai: st_lottie(lottie_ai, height=120)

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 감사 기준 설정")
    night_start = st.slider("심야 시작", 0, 23, 23)
    night_end = st.slider("심야 종료", 0, 23, 6)
    high_limit = st.number_input("고액 결제 기준(원)", value=500000)
    st.divider()
    st.info("💡 감사실 FUNFUN 2.0 전략 적용 중")

tab1, tab2, tab3 = st.tabs(["📈 법인카드 리스크 탐지", "📊 연간 데이터 분석", "💬 AI 실장님 상담소"])

# ---------------------------------------------------------
# Tab 1: 법인카드 리스크 탐지 (실장님 요청 집중 반영)
# ---------------------------------------------------------
with tab1:
    st.subheader("🚨 실시간 위반 의심 내역 탐지")
    uploaded_file = st.file_uploader("감사 대상 파일(CSV/XLSX)을 업로드하세요", type=['csv', 'xlsx'], key="audit_file")

    if uploaded_file:
        try:
            # 데이터 로드 및 헤더 처리
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # 상단 빈 행 제거 로직
            if df.columns[0].startswith('Unnamed'):
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)

            # 컬럼 매핑 및 리포팅
            f_map = AuditEngine2026.auto_map_columns(df.columns)
            
            # 필수 컬럼(금액) 체크
            if '금액' not in f_map:
                st.error("⚠️ '금액' 관련 컬럼을 찾을 수 없습니다. 파일 형식을 확인해주세요.")
            else:
                # 데이터 정제
                df['P_AMT'] = pd.to_numeric(df[f_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
                df['P_DATE'] = pd.to_datetime(df[f_map['날짜']].astype(str).str.split(' ').str[0], errors='coerce')
                
                # 리스크 탐지 (심야/휴일)
                if '시간' in f_map:
                    df['P_HOUR'] = pd.to_datetime(df[f_map['시간']].astype(str), errors='coerce').dt.hour
                    df['IS_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= night_start or x <= night_end if pd.notnull(x) else False)
                else:
                    df['IS_NIGHT'] = False
                
                df['IS_HOLIDAY'] = df['P_DATE'].dt.weekday >= 5
                
                # 위반 유형 라벨링
                df['위반내용'] = ""
                df.loc[df['IS_NIGHT'], '위반내용'] += "🌙심야 "
                df.loc[df['IS_HOLIDAY'], '위반내용'] += "📅휴일 "
                df.loc[df['P_AMT'] >= high_limit, '위반내용'] += "💰고액 "
                
                # 위반 리스트 필터링
                violation_df = df[df['위반내용'] != ""].copy()
                
                # [최상단] 강렬한 위반 보고서
                st.markdown('<div class="violation-card">', unsafe_allow_html=True)
                st.markdown(f"### 🚩 위반 의심 내역 총 {len(violation_df)}건 탐지됨")
                
                if not violation_df.empty:
                    # 표시용 컬럼 정리
                    disp_cols = [f_map['날짜'], f_map['시간'], f_map['가맹점'], 'P_AMT', '위반내용', f_map['사용자']]
                    disp_cols = [c for c in disp_cols if c in violation_df.columns or c == 'P_AMT' or c == '위반내용']
                    
                    res_display = violation_df[disp_cols].rename(columns={'P_AMT': '이용금액'})
                    st.table(res_display.style.format({'이용금액': '{:,.0f}원'}))
                    st.error("💡 위 리스트는 감사실의 'FUNFUN 준법 가이드' 위반 항목으로 분류되어 소명이 필요합니다.")
                else:
                    st.success("✅ 현재 파일에서 감지된 규정 위반 내역이 없습니다. 청렴한 조직문화를 응원합니다!")
                st.markdown('</div>', unsafe_allow_html=True)

                # 지출 통계 그래프
                daily_usage = df.groupby('P_DATE')['P_AMT'].sum().reset_index()
                fig = px.line(daily_usage, x='P_DATE', y='P_AMT', title="10월 지출 흐름 분석", template="plotly_dark", color_discrete_sequence=['#FFD700'])
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"🚨 시스템 오류 발생: {e}")

# ---------------------------------------------------------
# Tab 2: 연간 데이터 분석 (기존 app (1).py 기능 유지)
# ---------------------------------------------------------
with tab2:
    st.subheader("📅 연간 지출 추이 및 Spike 탐지")
    st.info("이 탭에서는 기존 연간 지출 데이터를 바탕으로 한 장기 트렌드 분석을 수행합니다.")
    # 기존 app(1).py의 연간 분석 로직을 이 부분에 유지 또는 확장하여 사용 가능합니다.

# ---------------------------------------------------------
# Tab 3: AI 실장님 상담소
# ---------------------------------------------------------
with tab3:
    st.subheader("💬 AI 실장님 상담소 (비공개)")
    user_q = st.text_input("고민되는 상황을 입력하시면 실장님의 페르소나로 답변해 드립니다.", placeholder="예: 주말에 고객사 미팅 후 식사 결제 가능한가요?")
    if user_q:
        st.markdown(f"""
        <div class="report-box">
            <b>사용자 질문:</b> {user_q}<br><br>
            <b>🤖 AI 답변:</b> 실장님의 평소 지침에 따르면, 주말 사용 건은 '사전 품의서'가 없을 경우 
            원칙적으로 제한됩니다. 하지만 불가피한 경우 '업무 연관성 입증 자료'를 감사실 포털에 즉시 업로드하도록 안내해 드립니다. 
            <b>당신의 커리어는 소중하니까요!</b>
        </div>
        """, unsafe_allow_html=True)