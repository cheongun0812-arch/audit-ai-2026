import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; }
    .report-box { background: #161618; border-left: 5px solid #FFD700; padding: 20px; border-radius: 10px; margin-top: 10px; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #FFD700 !important; }
    </style>
    """, unsafe_allow_html=True)

# 에니메이션 로드
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_main = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# --- 2. 헤더 ---
st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
if lottie_main: st_lottie(lottie_main, height=100)

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 필터")
    night_start = st.slider("심야 시작 (시)", 0, 23, 23)
    night_end = st.slider("심야 종료 (시)", 0, 23, 6)
    high_limit = st.number_input("고액 결제 기준(원)", value=500000)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- 3. 법카 리스크 분석 (Tab 2) ---
with tab2:
    st.subheader("📊 법인카드 리스크 정밀 진단")
    uploaded_file = st.file_uploader("파일 업로드 (CSV/XLSX)", type=['csv', 'xlsx'])

    if uploaded_file:
        try:
            # 데이터 로드
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file, header=None)
            else:
                raw_df = pd.read_excel(uploaded_file, header=None)
            
            # 헤더 행 찾기
            header_row = 0
            for i, row in raw_df.head(10).iterrows():
                if "금액" in str(row.values) or "승인" in str(row.values):
                    header_row = i
                    break
            
            df = raw_df.iloc[header_row+1:].copy()
            df.columns = [str(c).strip() for c in raw_df.iloc[header_row].values]
            
            # 중복 컬럼 처리
            new_cols = []
            c_counts = {}
            for c in df.columns:
                if c in c_counts:
                    c_counts[c] += 1
                    new_cols.append(f"{c}_{c_counts[c]}")
                else:
                    c_counts[c] = 0
                    new_cols.append(c)
            df.columns = new_cols
            df = df.reset_index(drop=True)

            # 컬럼 매핑
            col_map = {
                '금액': ['금액', '이용금액', '합계'],
                '날짜': ['승인일자', '거래일자', '날짜'],
                '시간': ['승인일시', '승인시간', '시간'],
                '가맹점': ['거래처명', '가맹점명', '상호'],
                '사용자': ['사용자', '이용자명', '성명']
            }
            
            f_map = {}
            for k, v in col_map.items():
                for c in df.columns:
                    if any(x in c for x in v):
                        f_map[k] = c
                        break

            # 데이터 정제
            df[f_map['금액']] = pd.to_numeric(df[f_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
            df[f_map['날짜']] = pd.to_datetime(df[f_map['날짜']].astype(str).str.split(' ').str[0], errors='coerce')
            
            # 심야/휴일 분석
            if '시간' in f_map:
                df['hour'] = pd.to_datetime(df[f_map['시간']].astype(str)).dt.hour
                df['is_night'] = df['hour'].apply(lambda x: x >= night_start or x <= night_end)
            else:
                df['is_night'] = False
            
            df['is_holiday'] = df[f_map['날짜']].dt.weekday >= 5 # 토/일

            # 리스크 요약 보고서
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.subheader("🚩 AI 리스크 탐지 결과")
            c1, c2, c3 = st.columns(3)
            night_cnt = len(df[df['is_night']])
            holiday_cnt = len(df[df['is_holiday']])
            high_cnt = len(df[df[f_map['금액']] >= high_limit])
            
            c1.error(f"🌙 심야 사용: {night_cnt}건")
            c2.error(f"📅 휴일 사용: {holiday_cnt}건")
            c3.warning(f"💰 고액 결제: {high_cnt}건")

            # 위장 가맹점 의심 (단골/업종 키워드)
            risk_keywords = ['유통', '물산', '상사', '도매']
            risk_merchants = df[df[f_map['가맹점']].str.contains('|'.join(risk_keywords), na=False)]
            if not risk_merchants.empty:
                st.error(f"🚨 위장 가맹점 의심 내역: {len(risk_merchants)}건 감지됨")
                st.dataframe(risk_merchants[[f_map['날짜'], f_map['가맹점'], f_map['금액'], f_map['사용자']]])
            
            st.markdown('</div>', unsafe_allow_html=True)

            # 전체 그래프
            daily = df.groupby(f_map['날짜'])[f_map['금액']].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily[f_map['날짜']], y=daily[f_map['금액']], line=dict(color='#FFD700')))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")

# (나머지 탭 생략)
