
#!/usr/bin/env python3
# analyze_cause_patterns_extracted.py (category extension)

import json, argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                continue
    return rows

def to_df_jsonl_meta(rows):
    keep = ["ler", "Facility_Name", "Unit", "Event_Date", "CFR", "Title"]
    return pd.DataFrame([{k:r.get(k) for k in keep} for r in rows])

def load_system_map(sys_json):
    with open(sys_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    sysmap, alias_to_code = {}, {}
    for s in data.get("systems", []):
        code = (s.get("code") or "").upper()
        if not code: 
            continue
        sysmap[code] = {
            "name": s.get("name"),
            "category": s.get("category", "unknown"),
            "aliases": [a.upper() for a in (s.get("aliases") or [])]
        }
        for a in sysmap[code]["aliases"]:
            alias_to_code[a] = code
    return sysmap, alias_to_code

def map_system_category(system_code, sysmap, aliasmap):
    if not isinstance(system_code, str) or not system_code:
        return "unknown", None
    sc = system_code.upper()
    if sc in sysmap:
        return sysmap[sc].get("category","unknown"), sc
    if sc in aliasmap:
        base = aliasmap[sc]
        return sysmap.get(base,{}).get("category","unknown"), base
    return "unknown", None

def tidy_dates(df):
    def parse_date(x):
        if not isinstance(x, str): return pd.NaT
        x = x.strip()
        for fmt in ("%Y-%m-%d","%m/%d/%Y","%Y/%m/%d","%d-%b-%Y","%b %d, %Y"):
            try: return pd.to_datetime(x, format=fmt)
            except Exception: pass
        try: return pd.to_datetime(x)
        except Exception: return pd.NaT
    df["Event_Date_parsed"] = df["Event_Date"].apply(parse_date)
    df["Event_YYYYMM"] = df["Event_Date_parsed"].dt.to_period("M").astype(str)
    df["Event_Year"] = df["Event_Date_parsed"].dt.year
    return df

def extract_cause_from_jsonl(rows):
    recs = []
    for r in rows:
        ler = r.get("ler") or r.get("LER")
        if not ler: 
            continue
        for e in r.get("Extractions", []) or []:
            if (e or {}).get("extraction_class") == "Cause":
                attrs = e.get("attributes") or {}
                recs.append({
                    "ler": ler,
                    "extraction_text": e.get("extraction_text"),
                    "extraction_category": attrs.get("category"),
                    "extraction_code": attrs.get("code"),
                })
    df = pd.DataFrame(recs)
    if df.empty:
        return df, df
    df["has_both"] = df["extraction_code"].notna() & df["extraction_category"].notna()
    df["has_code"] = df["extraction_code"].notna()
    df = df.sort_values(by=["ler","has_both","has_code"], ascending=[True,False,False])
    df_primary = df.groupby("ler", as_index=False).first().drop(columns=["has_both","has_code"])
    return df, df_primary

# plotting helpers
def barplot(pdf, x, y, title, outpng, rotate=45):
    plt.figure(figsize=(8,4))
    plt.bar(pdf[x].astype(str), pdf[y].values)
    plt.title(title); plt.xlabel(x); plt.ylabel(y)
    plt.xticks(rotation=rotate, ha="right")
    plt.tight_layout(); plt.savefig(outpng, dpi=150); plt.close()

def lineplot_multi(pdf, x, ycols, title, outpng):
    plt.figure(figsize=(8,4))
    for col in ycols:
        plt.plot(pdf[x].astype(str), pdf[col].values, label=str(col))
    plt.title(title); plt.xlabel(x); plt.ylabel("count")
    plt.xticks(rotation=45, ha="right")
    plt.legend(); plt.tight_layout(); plt.savefig(outpng, dpi=150); plt.close()

def heatmap(piv, title, outpng):
    fig = plt.figure(figsize=(8,5)); ax = plt.gca()
    im = ax.imshow(piv.values, aspect="auto")
    ax.set_xticks(np.arange(piv.shape[1])); ax.set_xticklabels(piv.columns, rotation=45, ha="right")
    ax.set_yticks(np.arange(piv.shape[0])); ax.set_yticklabels(piv.index)
    ax.set_title(title); fig.tight_layout(); plt.savefig(outpng, dpi=150); plt.close()

def hhi(series_counts):
    s = series_counts.astype(float)
    tot = s.sum()
    if tot == 0: return np.nan
    shares = s / tot
    return float((shares**2).sum())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cf", default="./preprocessing/component_failure.cleaned.json")
    ap.add_argument("--sys", default="./data/system_codes.json")
    ap.add_argument("--mode", default="./data/operating_mode.json")
    ap.add_argument("--ler", default="./extracted_text.jsonl")
    ap.add_argument("--outdir", default="./out_extracted_code")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # load
    cf = pd.read_json(args.cf)
    sysmap, aliasmap = load_system_map(args.sys)
    rows = load_jsonl(args.ler)
    meta = tidy_dates(to_df_jsonl_meta(rows))
    df_c_multi, df_c_primary = extract_cause_from_jsonl(rows)

    # base join
    df = pd.merge(cf, meta, on="ler", how="left")
    cats, bases = [], []
    for v in df["System"].fillna(""):
        cat, base = map_system_category(v, sysmap, aliasmap)
        cats.append(cat); bases.append(base)
    df["System_Category"] = cats; df["System_BaseCode"] = bases
    df["is_quality_ok"] = ~df["flags"].apply(lambda x: isinstance(x, list) and ("record_low_quality" in x))

    if not df_c_primary.empty:
        df = pd.merge(df, df_c_primary.rename(columns={
            "extraction_text":"Extracted_Cause_Text",
            "extraction_category":"Extracted_Cause_Category",
            "extraction_code":"Extracted_Cause_Code"
        }), on="ler", how="left")

    # ============= CATEGORY-LEVEL PATTERNS =============
    if not df_c_multi.empty:
        # 1) Category distribution
        cat_counts = (df_c_multi[df_c_multi["extraction_category"].notna()]
                      .groupby("extraction_category", as_index=False)
                      .size().rename(columns={"size":"count"})
                      .sort_values("count", ascending=False))
        cat_counts.to_csv(outdir/"cat_counts.csv", index=False)
        if not cat_counts.empty:
            barplot(cat_counts, "extraction_category", "count", "Extracted Cause category counts",
                    outdir/"cat_counts.png")

        # 2) Category × System Category (heatmap top)
        if "Extracted_Cause_Category" in df.columns:
            cxs = (df[df["Extracted_Cause_Category"].notna()]
                   .groupby(["Extracted_Cause_Category","System_Category"], as_index=False)
                   .size().rename(columns={"size":"count"}))
            cxs.to_csv(outdir/"cat_by_system_category.csv", index=False)
            # limit to top 8 categories & top 8 system-cats
            top_cats = (cxs.groupby("Extracted_Cause_Category")["count"].sum()
                          .sort_values(ascending=False).head(8).index.tolist())
            top_syscats = (cxs.groupby("System_Category")["count"].sum()
                              .sort_values(ascending=False).head(8).index.tolist())
            piv = (cxs[cxs["Extracted_Cause_Category"].isin(top_cats) &
                       cxs["System_Category"].isin(top_syscats)]
                   .pivot(index="Extracted_Cause_Category", columns="System_Category", values="count").fillna(0)
                   .reindex(index=top_cats, columns=top_syscats))
            if not piv.empty:
                heatmap(piv, "Category × System category (Top)", outdir/"cat_by_system_category_heatmap.png")

        # 3) Category × Component (Top-10 per category)
        if "Component" in df.columns and "Extracted_Cause_Category" in df.columns:
            comp = (df[df["Extracted_Cause_Category"].notna() & df["Component"].notna()]
                    .groupby(["Extracted_Cause_Category","Component"], as_index=False)
                    .size().rename(columns={"size":"count"}))
            comp_top = (comp.sort_values(["Extracted_Cause_Category","count"], ascending=[True,False])
                             .groupby("Extracted_Cause_Category").head(10))
            comp_top.to_csv(outdir/"cat_by_component_top10.csv", index=False)

        # 4) Category × IRIS (ratio + bar)
        if "Reportable_to_IRIS" in df.columns and "Extracted_Cause_Category" in df.columns:
            iris = (df[df["Extracted_Cause_Category"].notna() & df["Reportable_to_IRIS"].notna()]
                    .groupby(["Extracted_Cause_Category","Reportable_to_IRIS"], as_index=False)
                    .size().rename(columns={"size":"count"}))
            iris.to_csv(outdir/"cat_by_iris.csv", index=False)
            piv = iris.pivot(index="Extracted_Cause_Category", columns="Reportable_to_IRIS", values="count").fillna(0)
            if not piv.empty and "Yes" in piv.columns:
                piv["total"] = piv.sum(axis=1)
                piv = piv[piv["total"] >= 3]  # only with enough support
                piv["yes_ratio"] = (piv["Yes"] / piv["total"]).fillna(0)
                piv2 = piv.sort_values("total", ascending=False).reset_index()[["Extracted_Cause_Category","yes_ratio"]]
                barplot(piv2, "Extracted_Cause_Category", "yes_ratio",
                        "IRIS Yes ratio by Category", outdir/"cat_iris_ratio.png")

        # 5) Category 월별 추이 (Top categories)
        if "Event_YYYYMM" in df.columns and "Extracted_Cause_Category" in df.columns:
            monthly = (df[df["Extracted_Cause_Category"].notna() & df["Event_YYYYMM"].notna()]
                       .groupby(["Event_YYYYMM","Extracted_Cause_Category"], as_index=False)
                       .size().rename(columns={"size":"count"}))
            monthly.to_csv(outdir/"cat_monthly_counts.csv", index=False)
            # pivot for top categories
            if not cat_counts.empty:
                topcats = cat_counts.head(5)["extraction_category"].tolist()
                pivm = (monthly[monthly["Extracted_Cause_Category"].isin(topcats)]
                        .pivot(index="Event_YYYYMM", columns="Extracted_Cause_Category", values="count")
                        .fillna(0).reset_index().sort_values("Event_YYYYMM"))
                if not pivm.empty:
                    ycols = [c for c in pivm.columns if c != "Event_YYYYMM"]
                    lineplot_multi(pivm, "Event_YYYYMM", ycols,
                                   "Monthly trend (Top categories)", outdir/"cat_monthly_trend_top.png")

        # 6) 집중도 지표(HHI): 카테고리별 시스템카테고리 분포 집중도
        if "Extracted_Cause_Category" in df.columns:
            hhi_rows = []
            for cat in df["Extracted_Cause_Category"].dropna().unique():
                q = df[df["Extracted_Cause_Category"]==cat]
                counts = q["System_Category"].value_counts()
                h = hhi(counts)
                hhi_rows.append({"Extracted_Cause_Category": cat, "HHI_SystemCategory": h, "N": int(counts.sum())})
            hhi_df = pd.DataFrame(hhi_rows).sort_values("N", ascending=False)
            hhi_df.to_csv(outdir/"cat_system_category_hhi.csv", index=False)
            # plot HHI for categories with N>=3
            hplot = hhi_df[hhi_df["N"]>=3].sort_values("HHI_SystemCategory", ascending=False)
            if not hplot.empty:
                barplot(hplot, "Extracted_Cause_Category", "HHI_SystemCategory",
                        "System-category concentration (HHI) by Category", outdir/"cat_system_category_hhi.png")

    # save merged for reference
    df.to_csv(outdir/"merged_metadata_with_extracted.csv", index=False)

    print("Category-level outputs written to:", outdir)

if __name__ == "__main__":
    main()
