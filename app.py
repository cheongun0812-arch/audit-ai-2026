import streamlit as st
import pandas as pd
import re
from datetime import date, time
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.13 FINAL (KR) - 사용자 클릭 즉시 상세표 노출(하단 선택 제거) + 배타 우선순위(기관기준)"

# =========================================================
# 공휴일(법정/대체) - holidays 라이브러리 사용
# requirements.txt: holidays, openpyxl
# =========================================================
HAS_HOLIDAYS = True
try:
    import holidays  # type: ignore
except Exception:
    HAS_HOLIDAYS = False

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="법인카드 운영기준 위반 점검(최종)", layout="wide")

# =========================================================
# UTILS
# =========================================================
def normalize_text(x) -> str:
    if pd.isna(x):
        return ""
    x = str(x).lower()
    x = re.sub(r"[^a-z0-9가-힣]", "", x)
    return x

def extract_parentheses_name(x: str) -> str:
    if pd.isna(x):
        return ""
    m = re.search(r"\((.*?)\)", str(x))
    return m.group(1).strip() if m else ""

def combine_date_time(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    dt_str = date_series.astype(str).str.strip() + " " + time_series.astype(str).str.strip()
    return pd.to_datetime(dt_str, errors="coerce")

def pick_col(df: pd.DataFrame, *cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

def detect_columns(df: pd.DataFrame) -> dict:
    date_col = pick_col(df, "승인일자", "거래일자", "결제일자", "사용일자", "일자", "날짜", "Approval date")
    time_col = pick_col(df, "승인일시", "승인시간", "거래시간", "결제시간", "시간", "Approval time")
    datetime_col = pick_col(df, "거래일시", "결제일시", "일시", "Approval datetime", "승인일시(일시)")

    return {
        "user": pick_col(df, "사용자", "성명", "사원명", "User"),
        "merchant": pick_col(df, "거래처명", "거래처", "가맹점", "가맹점명", "Customer name"),
        "amount": pick_col(df, "금액", "금액1", "금액.1", "금액(원)", "이용금액", "승인금액", "결제금액", "Amount", "Amount 1"),
        "date": date_col,
        "time": time_col,
        "datetime": datetime_col,
        "title": pick_col(df, "문서 내용(제목)", "문서내용(제목)", "문서 내용", "Document content (title)"),
        "card_name": pick_col(df, "카드명", "Card name"),
    }

def build_datetime(df: pd.DataFrame, m: dict) -> pd.Series:
    if m.get("date") and m.get("time") and m["date"] in df.columns and m["time"] in df.columns:
        return combine_date_time(df[m["date"]], df[m["time"]])
    if m.get("datetime") and m["datetime"] in df.columns:
        return pd.to_datetime(df[m["datetime"]], errors="coerce")
    if m.get("date") and m["date"] in df.columns:
        return pd.to_datetime(df[m["date"]], errors="coerce")
    return pd.to_datetime(pd.Series([pd.NaT] * len(df)), errors="coerce")

def to_excel_bytes(d: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        d.to_excel(writer, index=False, sheet_name="data")
    return out.getvalue()

def download_block(d: pd.DataFrame, key: str):
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            "CSV 다운로드",
            data=d.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            key=f"dl_csv_{key}",
            use_container_width=True
        )
    with b2:
        st.download_button(
            "엑셀 다운로드",
            data=to_excel_bytes(d),
            file_name=f"{key}.xlsx",
            key=f"dl_xlsx_{key}",
            use_container_width=True
        )

# =========================================================
# ENGINE
# =========================================================
def run_audit(
    df_raw: pd.DataFrame,
    include_weekend: bool,
    include_public_holiday: bool,
    exclude_vehicle_from_night: bool,
    restricted_keywords: list[str],
    vehicle_keywords: list[str],
    # ✅ 배타 우선순위(강함→약함): 제한업종 > 주말 > 공휴일 > 심야
    exclusive_priority_high_to_low: list[str],
    exclude_bar_club: bool = True,
    exclude_branch_store: bool = True,
) -> tuple[pd.DataFrame, dict]:
    df = df_raw.copy()
    m = detect_columns(df)

    if not m.get("merchant") or not m.get("amount"):
        raise KeyError(
            "필수 컬럼(거래처명/가맹점, 금액)을 찾지 못했습니다.\n"
            f"현재 컬럼: {list(df.columns)}"
        )

    df["사용자"] = df[m["user"]].astype(str) if m.get("user") else "미지정"
    df["가맹점"] = df[m["merchant"]].astype(str)
    df["일시"] = build_datetime(df, m)

    if df["일시"].notna().mean() < 0.5:
        raise ValueError("일시 파싱 실패(유효 일시 < 50%). '승인일자+승인일시(시간)' 또는 '거래일시/일시' 컬럼을 확인하세요.")

    hour0_ratio = (df["일시"].dt.hour.fillna(-1).eq(0)).mean()
    if hour0_ratio > 0.85 and not m.get("time"):
        raise ValueError(
            "일시에 시간이 거의 없습니다(대부분 00:00:00).\n"
            "승인일자(날짜만)로 분석되고 있을 가능성이 큽니다.\n"
            "시간이 포함된 컬럼(승인일시/거래일시/일시)을 확인하세요."
        )

    df["문서제목"] = df[m["title"]].astype(str) if m.get("title") else ""
    df["카드사용자명(괄호)"] = df[m["card_name"]].astype(str).apply(extract_parentheses_name) if m.get("card_name") else ""

    df["P_AMT"] = pd.to_numeric(
        df[m["amount"]].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
        errors="coerce"
    ).fillna(0).astype(int)

    df["DATE"] = df["일시"].dt.date

    # 차량비(심야 제외)
    vkeys = [normalize_text(k) for k in vehicle_keywords if k.strip()]

    def is_vehicle_row(row) -> bool:
        hay = " ".join([str(row.get("가맹점", "")), str(row.get("문서제목", ""))])
        n = normalize_text(hay)
        return any(k in n for k in vkeys)

    df["F_VEHICLE"] = df.apply(is_vehicle_row, axis=1)

    # ✅ 심야: 23:00:00 ~ 06:00:00 (06:00:00 포함)
    late_start = time(23, 0, 0)
    late_end = time(6, 0, 0)
    tseries = df["일시"].dt.time
    df["F_NIGHT_RAW"] = tseries.apply(lambda x: (x >= late_start) or (x <= late_end) if pd.notna(x) else False)
    df["F_NIGHT"] = df["F_NIGHT_RAW"].copy()

    # 차량비는 심야에서 제외(옵션) + 디버그용 플래그
    if exclude_vehicle_from_night:
        df.loc[df["F_VEHICLE"] == True, "F_NIGHT"] = False
        df["F_NIGHT_EXCL_VEHICLE"] = (df["F_NIGHT_RAW"] & df["F_VEHICLE"])
    else:
        df["F_NIGHT_EXCL_VEHICLE"] = False

    # 주말(토/일)
    df["F_WEEKEND"] = (df["일시"].dt.weekday >= 5) if include_weekend else False

    # 공휴일(법정/대체)
    if include_public_holiday and HAS_HOLIDAYS:
        years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
        kr = holidays.KR(years=years)  # type: ignore
        df["F_HOLIDAY"] = df["DATE"].isin(kr)
    else:
        df["F_HOLIDAY"] = False

    # 제한업종(명시적 유흥만) + bar/club + 지점/점/branch 제외 (+ 디버그 컬럼)
    rkeys = [normalize_text(k) for k in restricted_keywords if k.strip()]

    def restrict_debug(name: str):
        n = normalize_text(name)
        raw_match = any(k in n for k in rkeys) if rkeys else False
        excl_branch = bool(exclude_branch_store and (("지점" in n) or ("branch" in n) or n.endswith("점")))
        excl_bar = bool(exclude_bar_club and any(k in n for k in ["bar", "club", "클럽", "pub", "lounge"]))
        matched = ""
        if raw_match:
            for k in rkeys:
                if k in n:
                    matched = k
                    break
        final = bool(raw_match and (not excl_branch) and (not excl_bar))
        return final, raw_match, excl_branch, excl_bar, matched

    dbg = df["가맹점"].astype(str).apply(restrict_debug)
    df["F_RESTRICT"] = dbg.apply(lambda x: x[0])
    df["F_RESTRICT_RAW"] = dbg.apply(lambda x: x[1])
    df["F_RESTRICT_EXCL_BRANCH"] = dbg.apply(lambda x: x[2])
    df["F_RESTRICT_EXCL_BARCLUB"] = dbg.apply(lambda x: x[3])
    df["RESTRICT_MATCH_KEY"] = dbg.apply(lambda x: x[4])

    # 위반사유(중복 가능)
    def reason(row):
        r = []
        if row["F_NIGHT"]:
            r.append("심야(23:00~06:00)")
        if row["F_WEEKEND"]:
            r.append("휴무일(주말)")
        if row["F_HOLIDAY"]:
            r.append("공휴일(법정/대체)")
        if row["F_RESTRICT"]:
            r.append("제한업종(명시적 유흥)")
        return " / ".join(r)

    df["위반사유"] = df.apply(reason, axis=1)
    df["운영기준위반"] = df["위반사유"] != ""

    # 배타 분류(합계 일치): 강한 위반 우선 부여
    def primary_type(row):
        for p in exclusive_priority_high_to_low:
            if p == "제한업종" and row["F_RESTRICT"]:
                return "제한업종"
            if p == "주말" and row["F_WEEKEND"]:
                return "주말"
            if p == "공휴일" and row["F_HOLIDAY"]:
                return "공휴일"
            if p == "심야" and row["F_NIGHT"]:
                return "심야"
        return ""

    df["주요위반유형(배타)"] = df.apply(primary_type, axis=1)

    features = {
        "mapping": m,
        "exclusive_priority_high_to_low": exclusive_priority_high_to_low,
        "late_start": "23:00:00",
        "late_end": "06:00:00",
        "holiday_enabled": HAS_HOLIDAYS,
    }
    return df, features


# =========================================================
# Q&A (Scoped, Local)
# - 외부 API 호출 없음 (업로드된 데이터프레임만 사용)
# =========================================================
def format_won(x: int) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)

def _safe_date_range(df: pd.DataFrame) -> tuple[date | None, date | None]:
    if "DATE" not in df.columns:
        return None, None
    s = df["DATE"].dropna()
    if s.empty:
        return None, None
    return s.min(), s.max()

def qa_apply_filters(
    base: pd.DataFrame,
    start_d: date | None,
    end_d: date | None,
    user_contains: str = "",
    merchant_contains: str = "",
    min_amt: int | None = None,
    max_amt: int | None = None,
    violations_only: bool = True,
) -> pd.DataFrame:
    d = base.copy()
    if violations_only and "운영기준위반" in d.columns:
        d = d[d["운영기준위반"]].copy()

    # 날짜 필터
    if start_d and end_d and "DATE" in d.columns:
        d = d[(d["DATE"] >= start_d) & (d["DATE"] <= end_d)].copy()

    # 사용자/가맹점 부분일치
    if user_contains:
        d = d[d["사용자"].astype(str).str.contains(user_contains, case=False, na=False)].copy()
    if merchant_contains:
        d = d[d["가맹점"].astype(str).str.contains(merchant_contains, case=False, na=False)].copy()

    # 금액 필터
    if min_amt is not None:
        d = d[d["P_AMT"] >= int(min_amt)].copy()
    if max_amt is not None and int(max_amt) > 0:
        d = d[d["P_AMT"] <= int(max_amt)].copy()

    return d

def qa_kpi(d: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("건수", int(len(d)))
    c2.metric("총금액", format_won(int(d["P_AMT"].sum())) if "P_AMT" in d.columns else "-")
    c3.metric("사용자 수", int(d["사용자"].nunique()) if "사용자" in d.columns else 0)
    c4.metric("가맹점 수", int(d["가맹점"].nunique()) if "가맹점" in d.columns else 0)

def qa_make_tx_label(row: pd.Series, idx) -> str:
    ts = row.get("일시", "")
    user = row.get("사용자", "")
    merch = row.get("가맹점", "")
    amt = row.get("P_AMT", "")
    return f"[{idx}] {ts} | {user} | {merch} | {amt}"


def to_excel_bytes_multi(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Create a multi-sheet Excel file in-memory."""
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        used = set()
        for name, d in sheets.items():
            # Excel sheet name limit: 31 chars
            sname = str(name)[:31] if name else "sheet"
            if sname in used:
                i = 2
                while f"{sname[:28]}_{i}" in used:
                    i += 1
                sname = f"{sname[:28]}_{i}"
            used.add(sname)
            d.to_excel(writer, index=False, sheet_name=sname)
    return out.getvalue()


def qa_run_query(
    qid: str,
    df: pd.DataFrame,
    feat: dict,
    display_cols: list[str],
    params: dict,
) -> dict:
    """
    Returns dict:
      - answer_md (str)
      - summary_df (pd.DataFrame|None)
      - detail_df (pd.DataFrame|None)
      - debug_df (pd.DataFrame|None)
      - qid/title
    """
    # 공통 필터 적용
    base = qa_apply_filters(
        base=df,
        start_d=params.get("start_d"),
        end_d=params.get("end_d"),
        user_contains=params.get("user_contains", ""),
        merchant_contains=params.get("merchant_contains", ""),
        min_amt=params.get("min_amt"),
        max_amt=params.get("max_amt"),
        violations_only=params.get("violations_only", True),
    )

    class_mode = params.get("class_mode", "배타")  # 배타 / 중복(플래그)
    topn = int(params.get("topn", 20))

    answer = ""
    summary_df = None
    detail_df = None
    debug_df = None

    # ---------- A. 필터형 ----------
    if qid == "q01":
        detail_df = base.sort_values("일시")
        answer = f"필터 조건을 만족하는 거래 **{len(detail_df)}건**을 표시합니다."

    elif qid in ("q02", "q03", "q04", "q05"):
        # 유형별(심야/공휴일/주말/제한업종)
        type_map = {"q02": ("심야", "F_NIGHT"), "q03": ("공휴일", "F_HOLIDAY"), "q04": ("주말", "F_WEEKEND"), "q05": ("제한업종", "F_RESTRICT")}
        tname, flag = type_map[qid]
        if class_mode == "배타":
            detail_df = base[base["주요위반유형(배타)"] == tname].copy()
            answer = f"배타 기준으로 **{tname}** 위반 거래 **{len(detail_df)}건**을 표시합니다."
        else:
            detail_df = base[base[flag] == True].copy()
            answer = f"플래그(중복) 기준으로 **{tname}** 위반 거래 **{len(detail_df)}건**을 표시합니다."

    elif qid == "q06":
        # 특정 사용자
        u = params.get("user_pick", "")
        if u:
            detail_df = base[base["사용자"].astype(str) == str(u)].copy()
            answer = f"사용자 **{u}**의 거래 **{len(detail_df)}건**을 표시합니다."
        else:
            detail_df = base.copy()
            answer = "사용자를 선택하지 않아(또는 검색 결과 없음) 현재 필터 범위 전체를 표시합니다."

    elif qid == "q07":
        # 특정 가맹점 키워드
        kw = params.get("merchant_kw", "")
        if kw:
            detail_df = base[base["가맹점"].astype(str).str.contains(kw, case=False, na=False)].copy()
            answer = f"가맹점 키워드 **{kw}**를 포함하는 거래 **{len(detail_df)}건**을 표시합니다."
        else:
            detail_df = base.copy()
            answer = "가맹점 키워드를 입력하지 않아 현재 필터 범위 전체를 표시합니다."

    elif qid == "q08":
        # 금액 조건
        thr = int(params.get("amt_thr", 0))
        detail_df = base[base["P_AMT"] >= thr].copy()
        answer = f"금액 **{format_won(thr)}원 이상** 거래 **{len(detail_df)}건**을 표시합니다."

    # ---------- B. 요약/랭킹 ----------
    elif qid == "q09":
        # 배타 유형별 요약
        s = (
            base.groupby("주요위반유형(배타)", as_index=False)
            .agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum"))
            .sort_values(["건수", "총금액"], ascending=[False, False])
        )
        summary_df = s
        detail_df = base.sort_values(["주요위반유형(배타)", "일시"])
        answer = "배타 유형별 **건수/총금액** 요약과 전체 근거행을 제공합니다."

    elif qid == "q10":
        # 사용자 TopN
        metric = params.get("rank_metric", "건수")
        s = (
            base.groupby("사용자", as_index=False)
            .agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum"))
        )
        if metric == "총금액":
            s = s.sort_values(["총금액", "건수"], ascending=[False, False])
        else:
            s = s.sort_values(["건수", "총금액"], ascending=[False, False])
        summary_df = s.head(topn)
        answer = f"사용자 Top {topn} (기준: {metric}) 요약입니다. 아래 상세는 요약 대상 사용자들만 표시합니다."
        users = summary_df["사용자"].astype(str).tolist()
        detail_df = base[base["사용자"].astype(str).isin(users)].copy().sort_values(["사용자", "일시"])

    elif qid == "q11":
        # 가맹점 TopN
        s = (
            base.groupby("가맹점", as_index=False)
            .agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum"))
            .sort_values(["건수", "총금액"], ascending=[False, False])
        )
        summary_df = s.head(topn)
        answer = f"가맹점 Top {topn} 요약입니다. 아래 상세는 요약 대상 가맹점들만 표시합니다."
        merchs = summary_df["가맹점"].astype(str).tolist()
        detail_df = base[base["가맹점"].astype(str).isin(merchs)].copy().sort_values(["가맹점", "일시"])

    elif qid == "q12":
        # 월별 추세
        d = base.copy()
        d = d[d["일시"].notna()].copy()
        d["월"] = d["일시"].dt.to_period("M").astype(str)
        s = d.groupby("월", as_index=False).agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum")).sort_values("월")
        summary_df = s
        pick_month = params.get("pick_month", "")
        if pick_month and pick_month in set(s["월"].tolist()):
            detail_df = d[d["월"] == pick_month].copy().sort_values("일시")
            answer = f"월별 추세 요약입니다. 선택 월(**{pick_month}**)의 근거행 {len(detail_df)}건을 표시합니다."
        else:
            detail_df = d.sort_values("일시")
            answer = "월별 추세 요약과 전체 근거행을 제공합니다. (월을 선택하면 해당 월만 필터링)"

    elif qid == "q13":
        # 요일 분포
        d = base.copy()
        d = d[d["일시"].notna()].copy()
        d["요일"] = d["일시"].dt.weekday.map({0:"월",1:"화",2:"수",3:"목",4:"금",5:"토",6:"일"})
        s = d.groupby("요일", as_index=False).agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum"))
        order = ["월","화","수","목","금","토","일"]
        s["__o"] = s["요일"].apply(lambda x: order.index(x) if x in order else 99)
        summary_df = s.sort_values("__o").drop(columns="__o")
        pick = params.get("pick_weekday", "")
        if pick and pick in set(order):
            detail_df = d[d["요일"] == pick].copy().sort_values("일시")
            answer = f"요일 분포 요약입니다. 선택 요일(**{pick}**)의 근거행 {len(detail_df)}건을 표시합니다."
        else:
            detail_df = d.sort_values("일시")
            answer = "요일 분포 요약과 전체 근거행을 제공합니다. (요일을 선택하면 해당 요일만 필터링)"

    elif qid == "q14":
        # 시간대 분포
        d = base.copy()
        d = d[d["일시"].notna()].copy()
        d["시"] = d["일시"].dt.hour.astype(int)
        s = d.groupby("시", as_index=False).agg(건수=("P_AMT", "size"), 총금액=("P_AMT", "sum")).sort_values("시")
        summary_df = s
        pick_h = params.get("pick_hour", None)
        if pick_h is not None and str(pick_h).strip() != "":
            try:
                h = int(pick_h)
                detail_df = d[d["시"] == h].copy().sort_values("일시")
                answer = f"시간대 분포 요약입니다. 선택 시간(**{h}시**) 근거행 {len(detail_df)}건을 표시합니다."
            except Exception:
                detail_df = d.sort_values("일시")
                answer = "시간대 분포 요약과 전체 근거행을 제공합니다."
        else:
            detail_df = d.sort_values("일시")
            answer = "시간대 분포 요약과 전체 근거행을 제공합니다."

    elif qid == "q15":
        # 복수위반
        flags = ["F_NIGHT","F_WEEKEND","F_HOLIDAY","F_RESTRICT"]
        d = base.copy()
        for f in flags:
            if f not in d.columns:
                d[f] = False
        d["복수위반"] = (d[flags].sum(axis=1) > 1)
        detail_df = d[d["복수위반"]].copy().sort_values("일시")
        answer = f"복수 위반(2개 이상 동시) 거래 **{len(detail_df)}건**을 표시합니다."

    # ---------- C. 설명/근거 ----------
    elif qid == "q16":
        # 단일 거래 설명
        tx_idx = params.get("tx_idx", None)
        if tx_idx is None or tx_idx not in df.index:
            answer = "거래를 선택하지 않았습니다. 왼쪽에서 거래를 선택한 뒤 실행하세요."
        else:
            r = df.loc[tx_idx]
            reasons = r.get("위반사유", "")
            ptype = r.get("주요위반유형(배타)", "")
            answer = (
                f"선택 거래 설명\n\n"
                f"- 일시: **{r.get('일시','')}**\n"
                f"- 사용자: **{r.get('사용자','')}**\n"
                f"- 가맹점: **{r.get('가맹점','')}**\n"
                f"- 금액: **{format_won(int(r.get('P_AMT',0)))}원**\n"
                f"- 위반사유(중복): **{reasons or '(없음)'}**\n"
                f"- 배타 유형: **{ptype or '(없음)'}**\n"
            )
            detail_df = df.loc[[tx_idx]].copy()

    elif qid == "q17":
        # 배타 분류 근거 설명
        tx_idx = params.get("tx_idx", None)
        if tx_idx is None or tx_idx not in df.index:
            answer = "거래를 선택하지 않았습니다. 왼쪽에서 거래를 선택한 뒤 실행하세요."
        else:
            r = df.loc[tx_idx]
            prio = feat.get("exclusive_priority_high_to_low", [])
            true_flags = []
            for name, flag in [("제한업종","F_RESTRICT"),("주말","F_WEEKEND"),("공휴일","F_HOLIDAY"),("심야","F_NIGHT")]:
                if bool(r.get(flag, False)):
                    true_flags.append(name)
            chosen = r.get("주요위반유형(배타)", "")
            answer = (
                f"배타 분류 설명\n\n"
                f"- True 플래그: **{', '.join(true_flags) if true_flags else '(없음)'}**\n"
                f"- 배타 우선순위(강함→약함): **{' > '.join(prio)}**\n"
                f"- 결과 배타 유형: **{chosen or '(없음)'}**\n"
            )
            detail_df = df.loc[[tx_idx]].copy()

    elif qid == "q18":
        # 제한업종 키워드에는 걸렸지만, 제외 로직(지점/점/branch 또는 bar/club 등)으로 제외된 케이스
        if "F_RESTRICT_RAW" not in base.columns:
            answer = "현재 엔진에 디버그 컬럼(F_RESTRICT_RAW)이 없습니다."
            detail_df = base.iloc[0:0].copy()
        else:
            d = base[(base["F_RESTRICT_RAW"] == True) & (base["F_RESTRICT"] == False)].copy()
            detail_df = d.sort_values("일시")
            s = (
                d.assign(
                    제외사유=d.apply(
                        lambda r: ("지점/점/branch" if bool(r.get("F_RESTRICT_EXCL_BRANCH", False)) else "") +
                                  (" + bar/club/pub/lounge" if bool(r.get("F_RESTRICT_EXCL_BARCLUB", False)) else ""),
                        axis=1
                    )
                )
                .groupby("제외사유", as_index=False)
                .agg(건수=("P_AMT","size"), 총금액=("P_AMT","sum"))
                .sort_values(["건수","총금액"], ascending=[False, False])
            )
            summary_df = s
            answer = f"제한업종 키워드 매칭(원시) 대비 제외 로직으로 빠진 거래 **{len(detail_df)}건**입니다."

    elif qid == "q19":
        # 차량비로 인해 심야에서 제외된 거래
        if "F_NIGHT_RAW" not in base.columns:
            answer = "현재 엔진에 디버그 컬럼(F_NIGHT_RAW)이 없습니다."
            detail_df = base.iloc[0:0].copy()
        else:
            d = base[(base["F_NIGHT_RAW"] == True) & (base["F_NIGHT"] == False) & (base["F_VEHICLE"] == True)].copy()
            detail_df = d.sort_values("일시")
            answer = f"차량비 키워드로 인해 심야에서 제외된 거래 **{len(detail_df)}건**입니다."

    elif qid == "q20":
        # 컬럼 매핑 결과
        answer = "컬럼 자동 인식(매핑) 결과입니다."
        summary_df = pd.DataFrame([feat.get("mapping", {})])
        detail_df = None

    elif qid == "q21":
        # 일시 품질 점검
        total = len(df)
        valid = int(df["일시"].notna().sum()) if "일시" in df.columns else 0
        ratio = (valid / total) if total else 0
        hour0_ratio = float((df["일시"].dt.hour.fillna(-1).eq(0)).mean()) if "일시" in df.columns else 0
        summary_df = pd.DataFrame([{
            "총행수": total,
            "유효 일시 행수": valid,
            "유효 일시 비율": round(ratio, 4),
            "00시(0시) 비율": round(hour0_ratio, 4),
        }])
        bad = df[df["일시"].isna()].copy() if "일시" in df.columns else df.iloc[0:0].copy()
        detail_df = bad.head(200)
        answer = "일시 파싱/품질 요약입니다. 아래는 일시가 비어있는(파싱 실패) 샘플 최대 200행입니다."

    # ---------- D. 패턴 탐지 ----------
    elif qid == "q22":
        # 동일 사용자+가맹점+하루 반복 결제(2회 이상)
        d = base.copy()
        g = (
            d.groupby(["사용자","가맹점","DATE"], as_index=False)
            .agg(반복횟수=("P_AMT","size"), 총금액=("P_AMT","sum"))
        )
        g = g[g["반복횟수"] >= int(params.get("repeat_min", 2))].sort_values(["반복횟수","총금액"], ascending=[False, False])
        summary_df = g.head(topn)
        if not summary_df.empty:
            key = summary_df.iloc[0][["사용자","가맹점","DATE"]].tolist()
            detail_df = d[(d["사용자"]==key[0]) & (d["가맹점"]==key[1]) & (d["DATE"]==key[2])].copy().sort_values("일시")
            answer = f"하루 반복 결제 후보 {len(g)}그룹입니다. 요약 Top {min(topn, len(g))}을 표시하고, 1위 그룹의 근거행을 아래에 보여줍니다."
        else:
            detail_df = d.iloc[0:0].copy()
            answer = "조건(반복횟수) 이상인 그룹이 없습니다."

    elif qid == "q23":
        # 10분(기본) 이내 연속 결제(쪼개기 의심)
        window_min = int(params.get("window_min", 10))
        d = base.copy()
        d = d[d["일시"].notna()].copy()
        d = d.sort_values("일시")
        d["prev_time"] = d.groupby(["사용자","가맹점","DATE"])["일시"].shift(1)
        d["delta_min"] = ((d["일시"] - d["prev_time"]).dt.total_seconds() / 60.0)
        cand = d[(d["delta_min"].notna()) & (d["delta_min"] <= window_min)].copy()
        summary_df = (
            cand.groupby(["사용자","가맹점","DATE"], as_index=False)
            .agg(의심건수=("P_AMT","size"), 총금액=("P_AMT","sum"), 최소간격분=("delta_min","min"))
            .sort_values(["의심건수","총금액"], ascending=[False, False])
            .head(topn)
        )
        if not summary_df.empty:
            k = summary_df.iloc[0][["사용자","가맹점","DATE"]].tolist()
            detail_df = d[(d["사용자"]==k[0]) & (d["가맹점"]==k[1]) & (d["DATE"]==k[2])].copy().sort_values("일시")
            answer = f"{window_min}분 이내 연속 결제 후보(그룹) Top {len(summary_df)}입니다. 1위 그룹의 근거행을 아래에 표시합니다."
        else:
            detail_df = d.iloc[0:0].copy()
            answer = f"{window_min}분 이내 연속 결제 후보가 없습니다."

        debug_df = cand.sort_values(["사용자","가맹점","DATE","일시"]).head(300)

    elif qid == "q24":
        # 사용자별 대표 위반유형(배타)
        d = base.copy()
        s = (
            d.groupby(["사용자","주요위반유형(배타)"], as_index=False)
            .agg(건수=("P_AMT","size"), 총금액=("P_AMT","sum"))
        )
        # 대표 유형 = 건수 최댓값(동률이면 총금액)
        s = s.sort_values(["사용자","건수","총금액"], ascending=[True, False, False])
        rep = s.groupby("사용자", as_index=False).head(1).copy()
        rep = rep.rename(columns={"주요위반유형(배타)":"대표유형"})
        summary_df = rep.sort_values(["건수","총금액"], ascending=[False, False]).head(topn)
        detail_df = base[base["사용자"].astype(str).isin(summary_df["사용자"].astype(str).tolist())].copy().sort_values(["사용자","일시"])
        answer = f"사용자별 대표 위반유형(배타) 요약 Top {topn}입니다."

    else:
        answer = "지원되지 않는 질문입니다."
        detail_df = base.iloc[0:0].copy()

    return {
        "qid": qid,
        "answer_md": answer,
        "summary_df": summary_df,
        "detail_df": detail_df,
        "debug_df": debug_df,
    }

def render_qa(df: pd.DataFrame, feat: dict, display_cols: list[str]):
    st.subheader("Q&A (업로드 데이터 기반 질의응답 · 로컬)")
    st.caption("외부 AI 호출 없이, 업로드된 데이터프레임을 필터/집계하여 답합니다. 결과는 항상 근거행(거래 상세표)로 확인할 수 있습니다.")

    # 공통 필터 UI
    min_d, max_d = _safe_date_range(df)
    if not min_d or not max_d:
        st.warning("DATE 컬럼이 비어있어 기간 필터를 사용할 수 없습니다.")
        min_d = None
        max_d = None

    qa_left, qa_right = st.columns([1, 2], gap="large")

    # 질문 카탈로그
    QA_ITEMS = [
        ("q01", "A-필터", "전체 위반 거래 조회"),
        ("q02", "A-필터", "심야 위반만 조회(배타/플래그)"),
        ("q03", "A-필터", "공휴일 위반만 조회(배타/플래그)"),
        ("q04", "A-필터", "주말 위반만 조회(배타/플래그)"),
        ("q05", "A-필터", "제한업종 위반만 조회(배타/플래그)"),
        ("q06", "A-필터", "특정 사용자 거래 조회(선택)"),
        ("q07", "A-필터", "특정 가맹점 키워드 조회"),
        ("q08", "A-필터", "금액 N원 이상 거래 조회"),
        ("q09", "B-요약", "배타 유형별 건수/총금액 요약"),
        ("q10", "B-요약", "사용자 Top N (건수/총금액)"),
        ("q11", "B-요약", "가맹점 Top N"),
        ("q12", "B-요약", "월별 추세(건수/총금액)"),
        ("q13", "B-요약", "요일 분포(건수/총금액)"),
        ("q14", "B-요약", "시간대 분포(건수/총금액)"),
        ("q15", "B-요약", "복수위반(2개 이상) 거래만"),
        ("q16", "C-설명", "이 거래가 왜 위반인지 설명"),
        ("q17", "C-설명", "이 거래의 배타 분류 근거 설명"),
        ("q18", "C-설명", "제한업종 키워드 매칭됐지만 제외된 케이스"),
        ("q19", "C-설명", "차량비 때문에 심야에서 제외된 케이스"),
        ("q20", "C-설명", "컬럼 자동 인식(매핑) 결과"),
        ("q21", "C-설명", "일시 파싱/품질 점검"),
        ("q22", "D-패턴", "동일 사용자+가맹점 하루 반복 결제(2회+)"),
        ("q23", "D-패턴", "N분 이내 연속 결제(쪼개기 의심)"),
        ("q24", "D-패턴", "사용자별 대표 위반유형(배타)"),
    ]

    # 매핑 dict for selection
    options = [f"[{qid}] {cat} · {title}" for (qid, cat, title) in QA_ITEMS]

    with qa_left:
        st.markdown("### 질문 선택")
        picked = st.selectbox("질문", options=options, index=0, key="qa_pick")
        qid = picked.split("]")[0].replace("[", "").strip()

        with st.expander("공통 필터", expanded=True):
            violations_only = st.radio("범위", ["위반만", "전체거래"], horizontal=True, index=0, key="qa_scope") == "위반만"
            class_mode = st.radio("유형 분류 기준(유형질문에만 적용)", ["배타", "중복(플래그)"], horizontal=True, index=0, key="qa_classmode")

            # 날짜 범위
            if min_d and max_d:
                dr = st.date_input("기간", value=(min_d, max_d), key="qa_daterange")
                if isinstance(dr, (tuple, list)) and len(dr) == 2:
                    start_d, end_d = dr[0], dr[1]
                else:
                    start_d, end_d = dr, dr
            else:
                start_d, end_d = None, None

            user_contains = st.text_input("사용자 포함(부분일치)", value="", key="qa_user_contains")
            merchant_contains = st.text_input("가맹점 포함(부분일치)", value="", key="qa_merch_contains")
            min_amt = st.number_input("최소금액(원)", min_value=0, value=0, step=1000, key="qa_minamt")
            max_amt = st.number_input("최대금액(원, 0=무제한)", min_value=0, value=0, step=1000, key="qa_maxamt")

        # 질문별 추가 파라미터
        topn = 20
        rank_metric = "건수"
        pick_month = ""
        pick_weekday = ""
        pick_hour = None
        repeat_min = 2
        window_min = 10
        user_pick = ""
        merchant_kw = ""
        amt_thr = 0
        tx_idx = None

        st.markdown("### 질문별 옵션")
        if qid in ("q10", "q11", "q22", "q23", "q24"):
            topn = st.slider("Top N", min_value=5, max_value=50, value=20, step=5, key="qa_topn")
        if qid == "q10":
            rank_metric = st.radio("랭킹 기준", ["건수", "총금액"], horizontal=True, index=0, key="qa_rank_metric")
        if qid == "q12":
            # 월 리스트
            dtmp = df[df["일시"].notna()].copy()
            dtmp["월"] = dtmp["일시"].dt.to_period("M").astype(str)
            months = ["(전체)"] + sorted(dtmp["월"].unique().tolist())
            pick_month = st.selectbox("월 선택", options=months, index=0, key="qa_pick_month")
            if pick_month == "(전체)":
                pick_month = ""
        if qid == "q13":
            pick_weekday = st.selectbox("요일 선택", options=["(전체)","월","화","수","목","금","토","일"], index=0, key="qa_pick_wd")
            if pick_weekday == "(전체)":
                pick_weekday = ""
        if qid == "q14":
            pick_hour = st.selectbox("시간 선택", options=["(전체)"] + list(range(0,24)), index=0, key="qa_pick_h")
            if pick_hour == "(전체)":
                pick_hour = None
        if qid == "q06":
            # 사용자 선택(현 필터와 별개로 전체 목록 제공)
            all_users = sorted(df["사용자"].astype(str).unique().tolist())
            user_pick = st.selectbox("사용자 선택", options=["(선택안함)"] + all_users, index=0, key="qa_user_pick")
            if user_pick == "(선택안함)":
                user_pick = ""
        if qid == "q07":
            merchant_kw = st.text_input("가맹점 키워드", value="", key="qa_merch_kw")
        if qid == "q08":
            amt_thr = st.number_input("기준금액(원)", min_value=0, value=300000, step=10000, key="qa_amt_thr")

        # 거래 선택이 필요한 질문 (q16, q17)
        if qid in ("q16", "q17"):
            # 현재 공통 필터로 후보 생성(최대 200건)
            base_candidates = qa_apply_filters(
                df,
                start_d=start_d,
                end_d=end_d,
                user_contains=user_contains,
                merchant_contains=merchant_contains,
                min_amt=int(min_amt) if min_amt else None,
                max_amt=int(max_amt) if max_amt else None,
                violations_only=violations_only,
            ).sort_values("일시").head(200)
            if base_candidates.empty:
                st.warning("현재 필터 범위에 거래가 없습니다.")
            else:
                labels = {qa_make_tx_label(row, idx): idx for idx, row in base_candidates.iterrows()}
                sel_label = st.selectbox("거래 선택(최대 200건)", options=list(labels.keys()), index=0, key="qa_tx_pick")
                tx_idx = labels.get(sel_label)

        if qid == "q22":
            repeat_min = st.slider("반복 최소 횟수", min_value=2, max_value=10, value=2, step=1, key="qa_repeat_min")
        if qid == "q23":
            window_min = st.slider("연속 결제 간격(분)", min_value=1, max_value=60, value=10, step=1, key="qa_window_min")

        run = st.button("실행", type="primary", use_container_width=True, key="qa_run")

        if run:
            params = {
                "start_d": start_d,
                "end_d": end_d,
                "user_contains": user_contains,
                "merchant_contains": merchant_contains,
                "min_amt": int(min_amt) if min_amt else None,
                "max_amt": int(max_amt) if max_amt else None,
                "violations_only": violations_only,
                "class_mode": class_mode,
                "topn": topn,
                "rank_metric": rank_metric,
                "pick_month": pick_month,
                "pick_weekday": pick_weekday,
                "pick_hour": pick_hour,
                "repeat_min": repeat_min,
                "window_min": window_min,
                "user_pick": user_pick,
                "merchant_kw": merchant_kw,
                "amt_thr": amt_thr,
                "tx_idx": tx_idx,
            }
            result = qa_run_query(qid=qid, df=df, feat=feat, display_cols=display_cols, params=params)
            st.session_state["qa_last"] = result
            # history
            hist = st.session_state.get("qa_history", [])
            hist.append({
                "qid": qid,
                "when": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "answer": result.get("answer_md",""),
            })
            st.session_state["qa_history"] = hist[-30:]  # 최근 30개만

    # Right pane: result
    with qa_right:
        st.markdown("### 결과")
        last = st.session_state.get("qa_last")
        if not last:
            st.info("왼쪽에서 질문을 선택하고 **실행**을 눌러주세요.")
        else:
            st.markdown(last.get("answer_md", ""))
            detail_df = last.get("detail_df")
            summary_df = last.get("summary_df")
            debug_df = last.get("debug_df")

            if isinstance(detail_df, pd.DataFrame):
                qa_kpi(detail_df)

            if isinstance(summary_df, pd.DataFrame):
                st.markdown("#### 요약표")
                download_block(summary_df, f"qa_{last.get('qid','')}_summary")
                st.dataframe(summary_df, use_container_width=True, height=260)

            if isinstance(detail_df, pd.DataFrame):
                st.markdown("#### 근거행(거래 상세)")
                # 너무 큰 경우 UI 렌더 성능 고려(표시는 500행, 다운로드는 전체)
                download_block(detail_df[display_cols] if set(display_cols).issubset(detail_df.columns) else detail_df, f"qa_{last.get('qid','')}_detail")
                show_df = detail_df
                if len(show_df) > 500:
                    st.caption("표시는 500행으로 제한됩니다. 전체는 다운로드로 확인하세요.")
                    show_df = show_df.head(500)
                st.dataframe(show_df[display_cols] if set(display_cols).issubset(show_df.columns) else show_df, use_container_width=True, height=520)

            if isinstance(debug_df, pd.DataFrame) and not debug_df.empty:
                with st.expander("디버그(상위 300건)", expanded=False):
                    st.dataframe(debug_df, use_container_width=True, height=360)

        
        st.markdown("---")
        st.markdown("### 보고서팩(저장/다운로드)")
        saved = st.session_state.get("qa_saved", [])

        if last and isinstance(last.get("detail_df"), pd.DataFrame):
            if st.button("현재 결과를 보고서팩에 저장", key="qa_save_pack", use_container_width=True):
                item = {
                    "when": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "qid": last.get("qid", ""),
                    "answer": last.get("answer_md", ""),
                    "summary_df": last.get("summary_df"),
                    "detail_df": last.get("detail_df"),
                }
                saved.append(item)
                st.session_state["qa_saved"] = saved
                st.success("보고서팩에 저장했습니다.")

        saved = st.session_state.get("qa_saved", [])
        if saved:
            pack_rows = []
            for i, it in enumerate(saved, start=1):
                ddf = it.get("detail_df")
                pack_rows.append({
                    "No": i,
                    "저장시각": it.get("when",""),
                    "QID": it.get("qid",""),
                    "건수": int(len(ddf)) if isinstance(ddf, pd.DataFrame) else 0,
                    "총금액": int(ddf["P_AMT"].sum()) if isinstance(ddf, pd.DataFrame) and "P_AMT" in ddf.columns else 0,
                })
            pack_df = pd.DataFrame(pack_rows)
            st.dataframe(pack_df, use_container_width=True, height=220)

            sheets = {"0_Overview": pack_df}
            for i, it in enumerate(saved, start=1):
                qid = it.get("qid","Q")
                s = it.get("summary_df")
                d = it.get("detail_df")
                if isinstance(s, pd.DataFrame) and not s.empty:
                    sheets[f"{i:02d}_{qid}_summary"] = s
                if isinstance(d, pd.DataFrame) and not d.empty:
                    if set(display_cols).issubset(d.columns):
                        sheets[f"{i:02d}_{qid}_detail"] = d[display_cols]
                    else:
                        sheets[f"{i:02d}_{qid}_detail"] = d

            st.download_button(
                "보고서팩 엑셀 다운로드(멀티시트)",
                data=to_excel_bytes_multi(sheets),
                file_name="qa_report_pack.xlsx",
                key="qa_dl_pack",
                use_container_width=True
            )

            if st.button("보고서팩 비우기", key="qa_clear_pack", use_container_width=True):
                st.session_state["qa_saved"] = []
                st.rerun()
        else:
            st.caption("저장된 결과가 없습니다. 위에서 질문을 실행한 뒤 저장해 보세요.")

with st.expander("최근 실행 기록(최대 30개)", expanded=False):
            hist = st.session_state.get("qa_history", [])
            if not hist:
                st.caption("기록이 없습니다.")
            else:
                for h in reversed(hist):
                    st.write(f"- {h['when']} · {h['qid']} · {h['answer'][:80]}")



# =========================================================
# SESSION STATE
# =========================================================
if "focus_exclusive" not in st.session_state:
    st.session_state["focus_exclusive"] = "전체"
if "excluded_users" not in st.session_state:
    st.session_state["excluded_users"] = []
if "selected_user" not in st.session_state:
    st.session_state["selected_user"] = None
if "selection_supported" not in st.session_state:
    st.session_state["selection_supported"] = True
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []
if "qa_last" not in st.session_state:
    st.session_state["qa_last"] = None
if "qa_saved" not in st.session_state:
    st.session_state["qa_saved"] = []
if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "대시보드"

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader("지출결의현황.xlsx (또는 CSV)", type=["xlsx", "csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("화면")
st.sidebar.radio("모드 선택", options=["대시보드", "Q&A"], key="app_mode")

st.sidebar.markdown("---")
st.sidebar.subheader("기준(고정)")
st.sidebar.write("- 심야: **23:00:00 ~ 06:00:00**")
st.sidebar.write("- 휴무일: **토/일**")
st.sidebar.write("- 공휴일: **법정/대체(holidays.KR)**")
if not HAS_HOLIDAYS:
    st.sidebar.warning("공휴일 판정을 위해 `holidays` 패키지 설치가 필요합니다.")

include_weekend = st.sidebar.checkbox("휴무일(주말) 포함", value=True, key="opt_weekend")
include_public_holiday = st.sidebar.checkbox("공휴일 포함", value=True, key="opt_holiday")
exclude_vehicle_from_night = st.sidebar.checkbox("차량비는 심야 위반에서 제외", value=True, key="opt_vehicle_excl")

st.sidebar.markdown("---")
st.sidebar.subheader("배타 분류(기관 기준)")
st.sidebar.write("우선순위(강함→약함): **제한업종 > 주말 > 공휴일 > 심야**")
exclusive_priority_high_to_low = ["제한업종", "주말", "공휴일", "심야"]

st.sidebar.markdown("---")
st.sidebar.subheader("제한업종 키워드(명시적 유흥만)")
restricted_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="유흥주점\n단란주점\n나이트클럽\n안마시술소\n안마\n마사지",
    height=110,
    key="kw_restricted"
)
restricted_keywords = [x.strip() for x in re.split(r"[,\n]+", restricted_text) if x.strip()]

st.sidebar.subheader("차량비 키워드(심야 제외용)")
vehicle_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="차량운전비,차량,유류,주유,하이패스,통행료,주차,주차비,택시,대리운전,카카오T,렌터카,고속도로,정비,세차",
    height=90,
    key="kw_vehicle"
)
vehicle_keywords = [x.strip() for x in re.split(r"[,\n]+", vehicle_text) if x.strip()]

# =========================================================
# MAIN
# =========================================================
st.title("법인카드 운영기준 위반 점검(최종)")
st.caption(f"BUILD: {BUILD} | 공휴일판정: {'활성' if HAS_HOLIDAYS else '비활성'}")

if not uploaded:
    st.info("왼쪽에서 RAW DATA 파일을 업로드하세요.")
    st.stop()

# LOAD
try:
    if uploaded.name.lower().endswith(".xlsx"):
        df_raw = pd.read_excel(uploaded)
    else:
        try:
            df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"파일 로드 실패: {e}")
    st.stop()

# AUDIT
try:
    df, feat = run_audit(
        df_raw=df_raw,
        include_weekend=include_weekend,
        include_public_holiday=include_public_holiday,
        exclude_vehicle_from_night=exclude_vehicle_from_night,
        restricted_keywords=restricted_keywords,
        vehicle_keywords=vehicle_keywords,
        exclusive_priority_high_to_low=exclusive_priority_high_to_low,
    )
except Exception as e:
    st.error(str(e))
    st.stop()

with st.expander("컬럼 자동 인식 결과", expanded=False):
    st.json(feat["mapping"])

# =========================================================
# DATA PREP
# =========================================================
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유", "주요위반유형(배타)", "문서제목", "카드사용자명(괄호)"]
viol = df[df["운영기준위반"]].copy()

# =========================================================
# MODE SWITCH
# =========================================================
if st.session_state.get("app_mode") == "Q&A":
    render_qa(df=df, feat=feat, display_cols=DISPLAY_COLS)
    st.stop()

# =========================================================
# ① TOP SUMMARY (배타 클릭형)
# =========================================================
st.subheader("① 위반 요약(배타 분류: 합계 일치)")
st.caption("아래 버튼을 누르면 해당 배타 분류 위반 사례가 즉시 표시됩니다.")

total_unique = int(viol.shape[0])
counts_excl = viol["주요위반유형(배타)"].value_counts().reindex(["심야", "공휴일", "주말", "제한업종"]).fillna(0).astype(int)
dup_rows = int((viol[["F_NIGHT","F_WEEKEND","F_HOLIDAY","F_RESTRICT"]].sum(axis=1) > 1).sum())

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("전체 위반(유니크)", total_unique)
m2.metric("심야(배타)", int(counts_excl.get("심야", 0)))
m3.metric("공휴일(배타)", int(counts_excl.get("공휴일", 0)))
m4.metric("주말(배타)", int(counts_excl.get("주말", 0)))
m5.metric("제한업종(배타)", int(counts_excl.get("제한업종", 0)))
m6.metric("복수위반 행", dup_rows)

st.markdown("**배타 우선순위(강함→약함): 제한업종 > 주말 > 공휴일 > 심야**")

b0, b1, b2, b3, b4 = st.columns(5)
if b0.button(f"전체 보기 ({total_unique})", key="btn_focus_all", use_container_width=True):
    st.session_state["focus_exclusive"] = "전체"
if b1.button(f"심야 보기 ({int(counts_excl.get('심야',0))})", key="btn_focus_night", use_container_width=True):
    st.session_state["focus_exclusive"] = "심야"
if b2.button(f"공휴일 보기 ({int(counts_excl.get('공휴일',0))})", key="btn_focus_holiday", use_container_width=True):
    st.session_state["focus_exclusive"] = "공휴일"
if b3.button(f"주말 보기 ({int(counts_excl.get('주말',0))})", key="btn_focus_weekend", use_container_width=True):
    st.session_state["focus_exclusive"] = "주말"
if b4.button(f"제한업종 보기 ({int(counts_excl.get('제한업종',0))})", key="btn_focus_restrict", use_container_width=True):
    st.session_state["focus_exclusive"] = "제한업종"

focus = st.session_state["focus_exclusive"]

# =========================================================
# ② FOCUSED CASES
# =========================================================
st.markdown("---")
st.subheader(f"② 선택된 배타 분류 위반 사례: {focus}")
if focus == "전체":
    focus_df = viol.copy()
else:
    focus_df = viol[viol["주요위반유형(배타)"] == focus].copy()

download_block(focus_df[DISPLAY_COLS], f"exclusive_{focus}")
st.dataframe(focus_df[DISPLAY_COLS], use_container_width=True, height=320)

# =========================================================
# ③ USER SUMMARY + 즉시 상세 표시(하단 선택 제거)
# =========================================================
st.markdown("---")
st.subheader("③ 사용자별 위반 현황(클릭 즉시 상세 표시)")
st.caption("사용자 행을 클릭하면, 바로 아래에 해당 사용자의 위반 사례가 즉시 표시됩니다. (하단 선택창 없음)")

excluded = set(st.session_state.get("excluded_users", []))
user_summary = (
    focus_df.groupby("사용자", as_index=False)
    .agg(
        위반건수=("운영기준위반", "count"),
        심야=("F_NIGHT", "sum"),
        주말=("F_WEEKEND", "sum"),
        공휴일=("F_HOLIDAY", "sum"),
        제한업종=("F_RESTRICT", "sum"),
        총금액=("P_AMT", "sum"),
    )
    .sort_values(["위반건수", "총금액"], ascending=[False, False])
)
user_summary_view = user_summary[~user_summary["사용자"].astype(str).isin(excluded)].copy() if excluded else user_summary.copy()

# 제외 목록 관리(상단에만)
x1, x2, x3 = st.columns([2, 2, 1])
with x1:
    st.write(f"제외(검토완료) 사용자: **{len(excluded)}명**")
with x2:
    st.session_state["excluded_users"] = st.multiselect(
        "제외 사용자 관리(검토완료)",
        options=sorted(user_summary["사용자"].astype(str).unique().tolist()),
        default=sorted(list(excluded)),
        key="ms_excluded_users"
    )
with x3:
    if st.button("제외 목록 초기화", key="btn_clear_excluded", use_container_width=True):
        st.session_state["excluded_users"] = []
        st.session_state["selected_user"] = None
        st.rerun()

# 사용자 클릭 선택
selected_user = st.session_state.get("selected_user")
selection_supported = st.session_state.get("selection_supported", True)

sel_rows = []
if selection_supported:
    try:
        event = st.dataframe(
            user_summary_view,
            use_container_width=True,
            height=300,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="df_user_summary_select"
        )
        sel_rows = event.selection.rows  # type: ignore
    except Exception:
        # 클릭 선택 미지원 환경
        st.session_state["selection_supported"] = False
        selection_supported = False

if not selection_supported:
    st.warning("현재 실행 환경의 Streamlit 버전에서는 '표 클릭 선택'이 제한됩니다. 아래에서 사용자만 선택해 주세요(하단 선택창은 없습니다).")
    all_users = user_summary_view["사용자"].astype(str).tolist()
    if all_users:
        selected_user = st.selectbox("사용자 선택", options=all_users, index=0, key="sb_user_inline")
        st.session_state["selected_user"] = selected_user

if sel_rows:
    idx = sel_rows[0]
    if 0 <= idx < len(user_summary_view):
        selected_user = str(user_summary_view.iloc[idx]["사용자"])
        st.session_state["selected_user"] = selected_user

# 선택 사용자 제외 버튼
bb1, bb2 = st.columns([1, 3])
with bb1:
    if st.button("선택 사용자 제외(검토완료)", key="btn_exclude_selected", use_container_width=True):
        if st.session_state.get("selected_user"):
            cur = str(st.session_state["selected_user"])
            cur_list = set(st.session_state.get("excluded_users", []))
            cur_list.add(cur)
            st.session_state["excluded_users"] = sorted(list(cur_list))
            st.session_state["selected_user"] = None
            st.rerun()
with bb2:
    if not selected_user:
        st.info("사용자 표에서 행을 클릭하면, 바로 아래에 위반 사례가 표시됩니다.")

# ✅ 바로 아래에 사용자 위반사례 즉시 표시
st.markdown("#### 사용자 위반 사례(즉시 표시)")
if selected_user:
    st.write(f"선택 사용자: **{selected_user}**  |  배타 분류: **{focus}**")
    detail_df = focus_df[focus_df["사용자"].astype(str) == str(selected_user)].copy()
else:
    st.write(f"선택 사용자: (없음)  |  배타 분류: **{focus}**")
    detail_df = focus_df.copy()

download_block(detail_df[DISPLAY_COLS], f"detail_{focus}_{selected_user or 'all'}")
st.dataframe(detail_df[DISPLAY_COLS], use_container_width=True, height=520)

# =========================================================
# ④ 유형별 탭(선택 사항)
# =========================================================
st.markdown("---")
st.subheader("④ 위반 유형별 전체 목록(다운로드)")

def tab_df(mode: str) -> pd.DataFrame:
    if mode == "전체":
        return viol.copy()
    if mode == "심야":
        return df[df["F_NIGHT"]].copy()
    if mode == "주말":
        return df[df["F_WEEKEND"]].copy()
    if mode == "공휴일":
        return df[df["F_HOLIDAY"]].copy()
    if mode == "제한업종":
        return df[df["F_RESTRICT"]].copy()
    if mode == "배타":
        return viol.sort_values(["주요위반유형(배타)", "일시"]).copy()
    return df.iloc[0:0].copy()

tabs = st.tabs(["전체(위반)", "심야", "공휴일", "주말", "제한업종", "배타(합계일치)"])

tab_keys = ["전체", "심야", "공휴일", "주말", "제한업종", "배타"]
for i, tname in enumerate(tab_keys):
    with tabs[i]:
        d = tab_df(tname)
        download_block(d[DISPLAY_COLS], f"tab_{tname}")
        st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

st.caption("엑셀 다운로드: openpyxl 필요 | 공휴일 판정: holidays 필요")
