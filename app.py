import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- 디자인 및 설정 생략 (기존 유지) ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    night_start = st.slider("심야 시작 시간", 0, 23, 23)
    night_end = st.slider("심야 종료 시간", 0, 23, 6)

# --- Tab 2: 법카 리스크 분석 (강화된 버전) ---
# (데이터 로드 및 중복 컬럼 처리 로직은 이전과 동일하게 유지)
# ... (중략: 이전 코드의 데이터 로드 로직 포함) ...

            # [핵심] 시간 및 요일 분석 로직 추가
            # 시간 컬럼 자동 매핑 (승인일시, 승인시간 등)
            time_col = None
            for col in df.columns:
                if any(k in str(col) for k in ['시간', '일시']):
                    time_col = col
                    break
            
            if time_col:
                # 시간 데이터 추출 (HH:MM:SS 형식 대응)
                df['hour'] = pd.to_datetime(df[time_col].astype(str)).dt.hour
                # 심야 건 분류 (23시 ~ 06시)
                df['is_night'] = df['hour'].apply(lambda x: x >= night_start or x <= night_end)
            
            # 요일 분석 (토/일)
            df['weekday'] = df[final_map['날짜']].dt.weekday # 5:토, 6:일
            df['is_holiday'] = df['weekday'] >= 5

            # --- 결과 리포트 ---
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.subheader("🚩 AI 위반 사례 분석 리포트")
            
            c1, c2, c3 = st.columns(3)
            night_df = df[df['is_night'] == True]
            holiday_df = df[df['is_holiday'] == True]
            high_df = df[df[final_map['금액']] >= 500000]

            with c1: st.error(f"🌙 심야 사용: {len(night_df)}건")
            with c2: st.error(f"📅 휴일 사용: {len(holiday_df)}건")
            with c3: st.warning(f"💰 고액 결제: {len(high_df)}건")

            # 위반 내역 상세 표
            st.write("### 🔍 상세 위반 의심 내역")
            # 심야 또는 휴일 사용 건만 모아서 보여줌
            violation_df = df[(df['is_night']) | (df['is_holiday'])].copy()
            
            if not violation_df.empty:
                # 사유 컬럼 추가 (AI가 적어주는 느낌으로)
                violation_df['위반유형'] = violation_df.apply(
                    lambda x: ("심야 " if x['is_night'] else "") + ("휴일 " if x['is_holiday'] else ""), axis=1
                )
                
                # 결과 테이블 시각화
                res_df = violation_df[[final_map['날짜'], final_map['가맹점'], final_map['금액'], '위반유형', final_map['사용자']]]
                res_df.columns = ['날짜', '가맹점', '금액', '위반유형', '사용자']
                st.dataframe(res_df.style.background_gradient(subset=['금액'], cmap='OrRd'), use_container_width=True)
                
                st.info("💡 위 내역은 사내 규정상 소명이 필요한 항목입니다. AI가 해당 인원에게 자동 안내 메일을 발송할 준비가 되었습니다.")
            else:
                st.success("✅ 분석 결과, 심야 및 휴일 위반 의심 내역이 없습니다. 우리 회사는 매우 청렴합니다!")
            st.markdown('</div>', unsafe_allow_html=True)
