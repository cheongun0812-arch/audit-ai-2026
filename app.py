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
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@100;400;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 50px; font-weight: 900; color: #FFD700; text-shadow: 2px 2px 5px #000; }
    .report-box { 
        background: #161618; border-left: 6px solid #FFD700; padding: 25px; 
        border-radius: 12px; margin-top: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.5); 
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #FFD700 !important; font-weight: bold; }
    [data-testid="stFileUploader"] section { background-color: #000 !important; border: 1.5px dashed #FFD700 !important; }
    .stMetric { background-color: #1A1A1B; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# 에니메이션 로드
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_audit = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# --- 2. 헤더 ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
    st.write("“디지털 기술로 증명하는 청렴한 조직 문화의 시작”")
with col_h2:
    if lottie_audit: st_lottie(lottie_audit, height=100)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- 3. 법카 리스크 분석 (Tab 2) ---
with tab2:
    st.subheader("📊 법인카드 지출 패턴 정밀 진단")
    uploaded_file = st.file_uploader("25년 10월 법인카드 사용 내역 파일을 업로드하세요", type=['csv', 'xlsx'])

    if uploaded_file:
        try:
            # 데이터 로드 (헤더 찾기 포함)
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file, header=None)
            else:
                raw_df = pd.read_excel(uploaded_file, header=None)
            
            header_row = 0
            for i, row in raw_df.head(10).iterrows():
                if any(x in str(row.values) for x in ["금액", "승인", "거래처"]):
                    header_row = i
                    break
            
            df = raw_df.iloc[header_row+1:].copy()
            df.columns = [str(c).strip() for c in raw_df.iloc[header_row].values]
            
            # 컬럼 중복 방지
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

            # 지능형 컬럼 매핑
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

            # 데이터 변환
            df[f_map['금액']] = pd.to_numeric(df[f_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
            df[f_map['날짜']] = pd.to_datetime(df[f_map['날짜']].astype(str).str.split(' ').str[0], errors='coerce')
            
            # 심야 분석 (23시 ~ 06시)
            if '시간' in f_map:
                df['hour'] = pd.to_datetime(df[f_map['시간']].astype(str)).dt.hour
                df['is_night'] = (df['hour'] >= 23) | (df['hour'] <= 6)
            else:
                df['is_night'] = False
            
            # 요약 지표
            m1, m2, m3 = st.columns(3)
            night_df = df[df['is_night']].copy()
            m1.metric("총 지출액", f"{df[f_map['금액']].sum():,.0f}원")
            m2.error(f"🌙 심야 결제: {len(night_df)}건")
            m3.warning(f"🚨 고액 결제(50만↑): {len(df[df[f_map['금액']] >= 500000])}건")

            # --- 실장님 요청: 심야 위반 리스트 표시 ---
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            if not night_df.empty:
                st.subheader(f"🌙 심야 위반 의심 내역 ({len(night_df)}건)")
                
                # 표시용 컬럼 재구성
                night_display = night_df[[f_map['날짜'], f_map['시간'], f_map['가맹점'], f_map['금액'], f_map['사용자']]].copy()
                night_display['위반내용'] = "🌙심야 사용"
                
                # 컬럼명 변경 (실장님 요청 형식)
                night_display.columns = ['거래일자', '승인시간', '가맹점명', '이용금액', '사용자', '위반내용']
                
                # 날짜 형식 정리 (2025-10-17)
                night_display['거래일자'] = night_display['거래일자'].dt.strftime('%Y-%m-%d')
                
                # 표 출력
                st.table(night_display.style.format({'이용금액': '{:,.0f}원'}))
                st.error("💡 해당 건은 업무 시간 외(심야) 사용으로, 즉각적인 소명 요청이 필요합니다.")
            else:
                st.success("✅ 심야 시간대(23:00~06:00) 위반 내역이 발견되지 않았습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 그래프
            daily = df.groupby(f_map['날짜'])[f_map['금액']].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily[f_map['날짜']], y=daily[f_map['금액']], line=dict(color='#FFD700', width=3)))
            fig.update_layout(title="10월 지출 흐름 분석", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"⚠️ 분석 오류: {e}")

# 나머지 탭은 단순 가이드로 유지
with tab1: st.info("📄 AI 계약서 검토 기능이 준비 중입니다.")
with tab3: st.info("💬 AI 실장님 상담소: 실무 질문을 입력하세요.")
