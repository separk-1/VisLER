#!/usr/bin/env python3
# extract_component_failure.py
import re, json, argparse
from pathlib import Path

# ---------------------------
# 1) 추출 규칙 (원본 유지)
# ---------------------------
HDR = re.compile(
    r'cause\s+system\s+component\s+manufactur(?:er)?\s+reportable\s+to\s+i[r][il][s5]',
    re.I
)
YESNO = {"Y":"Yes","YES":"Yes","N":"No","NO":"No"}
MAX_MFR_LEN = 20

def norm(s:str)->str:
    if s is None: return ""
    s = s.replace('\u00a0',' ').replace('\uf0b7',' ')
    s = re.sub(r'\r\n?','\n',s)
    s = re.sub(r'[ \t]+',' ',s)
    return s.strip()

def after_last_header(txt:str)->str:
    last = None
    for m in HDR.finditer(txt): last = m
    return txt[last.end():] if last else txt

def parse_line_tokens(line:str):
    toks = line.strip().split()
    if len(toks) < 5:
        return None
    rep_raw = toks[-1].upper()
    if rep_raw not in YESNO:
        return None
    cause, system, component = toks[0], toks[1], toks[2]
    manuf = " ".join(toks[3:-1]).strip()
    return {
        "Cause": cause,
        "System": system,
        "Component": component,
        "Manufacturer": manuf,
        "Reportable_to_IRIS": YESNO[rep_raw]
    }

def extract_one(text:str):
    t = norm(text)
    body = after_last_header(t)
    # 번호 섹션(14.,15. …) 이전까지만
    body = re.split(r'\n\s*(?:1[0-9]|[2-9])\.[^\n]*', body, maxsplit=1)[0]
    lines = [ln for ln in body.splitlines() if ln.strip()]

    # 1) 헤더 다음 첫 3줄 후보
    for ln in lines[:3]:
        out = parse_line_tokens(ln)
        if out: return out

    # 2) Yes/No 포함 라인 재시도
    for ln in lines:
        if re.search(r'\b(?:Y|N|Yes|No)\b', ln, re.I):
            out = parse_line_tokens(ln)
            if out: return out

    # 3) 제조사 줄바꿈 케이스: 1~4줄 합쳐 시도
    joined = " ".join(lines[:4])
    out = parse_line_tokens(joined)
    if out: return out
    return None

def process_dir(input_dir:Path):
    results, miss = [], []
    for p in sorted(input_dir.glob('*.txt')):
        txt = p.read_text(encoding='utf-8', errors='ignore')
        rec = extract_one(txt)
        if rec:
            rec = {"ler": p.stem, **rec}
            results.append(rec)
        else:
            miss.append(p.stem)
    return results, miss

# ---------------------------
# 2) 클린 규칙 (추가)
# ---------------------------
NULL_TOKENS = {
    "", "n/a", "na", "-", "--", "—", "none", "null",
    "(cid:9)", "(cid:10)", "n/a n/a", "n/a n/a n/a"
}
YES_MAP = {"y":"Yes","yes":"Yes","true":"Yes","1":"Yes","yes.":"Yes"}
NO_MAP  = {"n":"No","no":"No","false":"No","0":"No","no.":"No"}

SYS_BAD_WORDS = {"LICENSEE","EVENT","REPORT","LER","SUPPLEMENTAL"}
CMP_BAD_WORDS = {"LICENSEE","EVENT","REPORT","LER","SUPPLEMENTAL"}

MFR_FIXES = [
    (re.compile(r"\bFlowsery\b", re.I), "Flowserve"),
    (re.compile(r"\bFlowserv\b", re.I), "Flowserve"),
    (re.compile(r"\bU\.?S\.?\s+Motors\b", re.I), "US Motors"),
]
SUSPECT_MFR_CODE = re.compile(r"^(?:[A-Z]\d{2,5}|[A-Z0-9]{2,6}|\d{2,4})$")

def _norm(s):
    if s is None: return None
    s = str(s).replace("\u00a0"," ").replace("\uf0b7"," ")
    s = re.sub(r"[ \t]+"," ", s).strip(" ,;")
    if s.lower() in NULL_TOKENS: return None
    return s.strip()

def _norm_yesno(v):
    v = _norm(v)
    if v is None: return None
    s = v.lower()
    if s in YES_MAP: return "Yes"
    if s in NO_MAP:  return "No"
    if s in ("yes","no"): return s.capitalize()
    return None

def _norm_code(v, up=True, maxlen=None, letters_only=False):
    v = _norm(v)
    if v is None: return None
    if up: v = v.upper()
    v = v.replace(" ", "")
    if letters_only:
        v = re.sub(r"[^A-Z]", "", v)
    if maxlen: v = v[:maxlen]
    return v or None

def _is_gibberish_mfr(s: str) -> bool:
    if not s: return True
    n = len(s)
    letters = sum(ch.isalpha() for ch in s)
    digits  = sum(ch.isdigit() for ch in s)
    if n > 120: return True
    if letters / max(1,n) < 0.45 and digits > 0:
        return True
    if re.search(r"(?:\b[A-Za-z]\b[ ,;:\-]*){6,}", s):  # 한 글자 토큰 연속
        return True
    if re.search(r"(?:[A-Za-z]\s+){10,}", s):          # 한 글자+공백 반복
        return True
    return False

def _validate_system(s):
    if not s: return None, "system_missing"
    if s in SYS_BAD_WORDS: return None, "system_header_leak"
    if not re.fullmatch(r"[A-Z]{1,4}", s): return None, "system_bad_format"
    return s, None

def _validate_component(c):
    if not c: return None, "component_missing"
    if c in CMP_BAD_WORDS: return None, "component_header_leak"
    if not re.fullmatch(r"[A-Z0-9\-]{1,12}", c): return None, "component_bad_format"
    return c, None

def clean_record(r: dict) -> dict:
    flags = []

    # --- 기본 정규화 ---
    ler = _norm(r.get("ler"))

    # Cause: 대문자 1글자만 허용
    cause = _norm_code(r.get("Cause"), up=True, maxlen=3, letters_only=True)
    if not cause or not re.fullmatch(r"[A-Z]", cause):
        flags.append("bad_cause")
        cause = None

    # System
    system_raw = _norm_code(r.get("System"), up=True, maxlen=8, letters_only=True)
    system = None
    if system_raw:
        if system_raw in SYS_BAD_WORDS:
            flags.append("system_header_leak")
        elif not re.fullmatch(r"[A-Z]{1,4}", system_raw):
            flags.append("system_bad_format")
        else:
            system = system_raw
    else:
        flags.append("system_missing")

    # Component
    component_raw = _norm_code(r.get("Component"), up=True, maxlen=20, letters_only=False)
    component = None
    if component_raw:
        if component_raw in CMP_BAD_WORDS:
            flags.append("component_header_leak")
        elif not re.fullmatch(r"[A-Z0-9\-]{1,12}", component_raw):
            flags.append("component_bad_format")
        else:
            component = component_raw
    else:
        flags.append("component_missing")

    # Manufacturer
    mfr = _norm(r.get("Manufacturer"))
    if mfr:
        # 흔한 오탈자 보정
        for pat, repl in MFR_FIXES:
            mfr = pat.sub(repl, mfr)
        mfr = re.sub(r"\s{2,}", " ", mfr).strip(" ,;")

        # 길이 제한
        if len(mfr) > MAX_MFR_LEN:
            flags.append("manufacturer_over_len")
            mfr = None

        # 코드/가비지 의심 (mfr가 남아있을 때만 검사)
        if mfr is not None:
            if SUSPECT_MFR_CODE.fullmatch(mfr) or _is_gibberish_mfr(mfr):
                flags.append("manufacturer_gibberish_or_code")
                mfr = None
    else:
        flags.append("manufacturer_missing")

    # IRIS
    iris = _norm_yesno(r.get("Reportable_to_IRIS"))
    if iris is None:
        flags.append("iris_missing")

    # 최종 출력
    out = {
        "ler": ler,
        "Cause": cause,
        "System": system,
        "Component": component,
        "Manufacturer": mfr,
        "Reportable_to_IRIS": iris,
        "flags": flags
    }

    # 품질 플래그
    hard_missing = sum(out[k] is None for k in ("System","Component","Manufacturer"))
    if hard_missing >= 2:
        out["flags"].append("record_low_quality")

    return out


def clean_and_dedup(records: list) -> list:
    cleaned = [clean_record(r) for r in records]
    # ler 중복 시 마지막으로 덮어쓰기
    dedup = {}
    for rec in cleaned:
        key = rec.get("ler")
        if key: dedup[key] = rec
    return list(dedup.values())

# ---------------------------
# 3) main
# ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", nargs="?", default="../data/ler_texts",
                    help="LER 텍스트 폴더 (기본: ../data/ler_texts)")
    ap.add_argument("-o","--output", default="component_failure.json",
                    help="원본 추출 JSON (기본: component_failure.json)")
    ap.add_argument("--clean-output", default=None,
                    help="클린 결과 JSON (기본: <output>.cleaned.json)")
    args = ap.parse_args()

    # 추출
    results, miss = process_dir(Path(args.input_dir))
    Path(args.output).write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"Wrote {len(results)} (raw) -> {args.output}")
    if miss:
        print("[WARN] no match:", ", ".join(miss[:10]) + (" ..." if len(miss)>10 else ""))

    # 클린
    cleaned = clean_and_dedup(results)
    clean_path = args.clean_output
    if not clean_path:
        # output.json -> output.cleaned.json
        if args.output.lower().endswith(".json"):
            clean_path = args.output[:-5] + ".cleaned.json"
        else:
            clean_path = args.output + ".cleaned.json"

    Path(clean_path).write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    # 간단 통계
    null_counts = {
        k: sum(1 for r in cleaned if r.get(k) is None)
        for k in ("Cause","System","Component","Manufacturer","Reportable_to_IRIS")
    }
    flag_counts = {}
    for r in cleaned:
        for f in r.get("flags", []):
            flag_counts[f] = flag_counts.get(f, 0) + 1

    print(f"Wrote {len(cleaned)} (cleaned) -> {clean_path}")
    print("Null counts:", null_counts)
    print("Flag counts:", {k:v for k,v in sorted(flag_counts.items(), key=lambda x:-x[1])})

if __name__ == "__main__":
    main()
