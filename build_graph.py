
import json, os, sys

SCHEMA_PATH = os.environ.get("GRAPH_SCHEMA_PATH", "data/graph_schema.json")
INPUT_JSONL = os.environ.get("EXTRACTED_JSONL_PATH", "extracted_keyword.jsonl")
OUTPUT_JSON = os.environ.get("GRAPH_OUTPUT_PATH", "graph_text.json")

def _truncate(s: str, n: int = 60) -> str:
    s = (s or "")
    return s if len(s) <= n else s[: n - 1] + "…"

def load_schema(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(path: str):
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(json.loads(line))
    return docs

def build_graph_for_doc(doc: dict, schema: dict, doc_idx: int):
    extractions = doc.get("Extractions") or []
    disp = schema.get("display", {})
    label_priority = disp.get("label_field_priority", ["extraction_text", "text"])
    trunc_n = int(disp.get("truncate", 60))

    nodes = []
    edges = []
    by_cls = {}

    # 1) nodes
    for i, e in enumerate(extractions):
        cls = e.get("extraction_class") or "Unknown"
        if cls == "Corrective_Action":
            cls = "CorrectiveAction"
        node_id = f"d{doc_idx}_n{i}"
        # label choose by priority
        val = None
        for key in label_priority:
            if e.get(key):
                val = e.get(key)
                break
        label = _truncate(str(val or cls), trunc_n)
        title = str(val or cls)
        nodes.append({
            "id": node_id,
            "label": label,
            "group": cls,
            "title": title,
            "attributes": e.get("attributes", {})
        })
        by_cls.setdefault(cls, []).append(node_id)

    # 2) edges by rules
    rules = schema.get("edge_rules", [])
    for r in rules:
        src_cls, dst_cls = r.get("from"), r.get("to")
        rel = r.get("relation") or ""
        src_ids = by_cls.get(src_cls, [])
        dst_ids = by_cls.get(dst_cls, [])

        # special rule: CorrectiveAction -> Procedure_or_Regulation else Outcome
        if src_cls == "CorrectiveAction" and dst_cls == "Outcome":
            # only create CA->Outcome if there is NO Procedure_or_Regulation
            if by_cls.get("Procedure_or_Regulation"):
                continue

        for s in src_ids:
            for d in dst_ids:
                edges.append({"from": s, "to": d, "label": rel})

    return {"nodes": nodes, "edges": edges}

def main():
    schema = load_schema(SCHEMA_PATH)
    docs = load_jsonl(INPUT_JSONL)

    out = []
    for idx, doc in enumerate(docs):
        ler = doc.get("ler") or doc.get("LER") or f"doc_{idx}"
        graph = build_graph_for_doc(doc, schema, idx)
        out.append({"ler": ler, "graph": graph})

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT_JSON} with {len(out)} graphs.")

if __name__ == "__main__":
    main()
