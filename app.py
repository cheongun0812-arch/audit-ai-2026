import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time

# --- 1. 페이지 설정 및 디자인 (강렬한 리스크 강조 테마) ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 50px; font-weight: 900; color: #FFD700; }
    /* 위반 내역 강조 박스 */
    .violation-card { 
        background: #2D0A0A; border: 2px solid #FF4B4B; padding: 25px; 
        border-radius: 15px; margin-bottom: 30px; 
    }
    .red-text { color: #FF4B4B; font-weight: 900; font-size: 24px; }
    .gold-text { color: #FFD700; font-weight: bold; }
    /* 테이블 가독성 */
    .stTable { background-color: #161618 !important; border-radius: 10px; }
    thead tr th { background-color: #FF4B4B !important; color: white !important; font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

# 헤더
st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
st.write("### ⚠️ 실시간 법인카드 규정 위반 모니터링 시스템")

# --- 2. 사이드바 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.markdown("### ⚙️ 감사 기준 설정")
    night_start = st.slider("심야 시작", 0, 23, 23)
    night_end = st.slider("심야 종료", 0, 23, 6)
    high_limit = st.number_input("고액 결제 기준(원)", value=500000)

# --- 3. 데이터 로드 및 분석 로직 ---
uploaded_file = st.file_uploader("파일을 업로드하면 즉시 위반 리스크를 탐지합니다", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file, header=None)
        else:
            raw_df = pd.read_excel(uploaded_file, header=None)
        
        # 헤더 자동 탐색
        header_row = 0
        for i, row in raw_df.head(10).iterrows():
            if any(x in str(row.values) for x in ["금액", "승인", "거래처"]):
                header_row = i
                break
        df = raw_df.iloc[header_row+1:].copy()
        df.columns = [str(c).strip() for c in raw_df.iloc[header_row].values]
        
        # 중복 컬럼 처리 및 매핑 (생략 없이 통합)
        col_map = {'금액':['금액','이용금액','합계'], '날짜':['승인일자','거래일자'], '시간':['승인일시','승인시간'], '가맹점':['거래처명','가맹점명'], '사용자':['사용자','이용자명']}
        f_map = {}
        for k, v in col_map.items():
            for c in df.columns:
                if any(x in str(c) for x in v): f_map[k] = c; break

        # 정제
        df[f_map['금액']] = pd.to_numeric(df[f_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df[f_map['날짜']] = pd.to_datetime(df[f_map['날짜']].astype(str).str.split(' ').str[0])
        
        # 심야/휴일 분석
        df['hour'] = pd.to_datetime(df[f_map['시간']].astype(str)).dt.hour
        df['is_night'] = (df['hour'] >= night_start) | (df['hour'] <= night_end)
        df['is_holiday'] = df[f_map['날짜']].dt.weekday >= 5

        # ---------------------------------------------------------
        # 🚨 [최상단 배치] 위반 리스크 요약 및 리스트
        # ---------------------------------------------------------
        night_df = df[df['is_night']].copy()
        holiday_df = df[df['is_holiday']].copy()
        
        st.markdown('<div class="violation-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="red-text">🚨 위반 리스크 탐지 보고 (심야 {len(night_df)}건 / 휴일 {len(holiday_df)}건)</p>', unsafe_allow_html=True)
        
        if not night_df.empty:
            st.markdown(f"### 🌙 심야 위반 의심 내역 ({len(night_df)}건)")
            night_display = night_df[[f_map['날짜'], f_map['시간'], f_map['가맹점'], f_map['금액'], f_map['사용자']]].copy()
            night_display['위반내용'] = "🌙심야 사용"
            night_display.columns = ['거래일자', '승인시간', '가맹점명', '이용금액', '사용자', '위반내용']
            night_display['거래일자'] = night_display['거래일자'].dt.strftime('%Y-%m-%d')
            
            # 실장님이 원하신 표 형식
            st.table(night_display.style.format({'이용금액': '{:,.0f}원'}))
            st.error("위 건은 업무 시간 외 부정사용 의심 건으로 분류되었습니다. 담당자 소명이 필요합니다.")
        
        if not holiday_df.empty:
            st.markdown(f"### 📅 휴일 사용 내역 ({len(holiday_df)}건)")
            holiday_display = holiday_df[[f_map['날짜'], f_map['시간'], f_map['가맹점'], f_map['금액'], f_map['사용자']]].copy()
            holiday_display['위반내용'] = "📅휴일 사용"
            holiday_display.columns = ['거래일자', '승인시간', '가맹점명', '이용금액', '사용자', '위반내용']
            holiday_display['거래일자'] = holiday_display['거래일자'].dt.strftime('%Y-%m-%d')
            st.table(holiday_display.style.format({'이용금액': '{:,.0f}원'}))

        st.markdown('</div>', unsafe_allow_html=True)

        # 이후 통계 및 그래프 표시
        m1, m2 = st.columns(2)
        m1.metric("총 집행 금액", f"{df[f_map['금액']].sum():,.0f}원")
        m2.metric("전체 거래 건수", f"{len(df)}건")

        daily = df.groupby(f_map['날짜'])[f_map['금액']].sum().reset_index()
        fig = go.Figure(go.Scatter(x=daily[f_map['날짜']], y=daily[f_map['금액']], line=dict(color='#FFD700', width=3)))
        fig.update_layout(title="10월 지출 흐름 분석", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ 데이터 처리 중 오류 발생: {e}")
