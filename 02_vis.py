import json
import os
import html

def _truncate(s, n=40):
    s = str(s or "")
    return s if len(s) <= n else s[:n-1] + "…"

def build_graph_from_extractions(extractions):
    """
    Extractions만으로 간단 그래프 생성:
      Condition → Human_Action
      Procedure_or_Regulation → Human_Action
      Human_Action → Outcome
      Cause → Outcome
      CorrectiveAction → Procedure_or_Regulation (없으면 Outcome)
    """
    nodes, edges = [], []
    by_cls = {}
    # 노드: 추출 항목 하나당 1개
    for idx, e in enumerate(extractions or []):
        cls = e.get("extraction_class") or "Unknown"
        if cls == "Corrective_Action":
            cls = "CorrectiveAction"
        node_id = f"e{idx}"
        label = _truncate(e.get("extraction_text") or e.get("text") or "")
        title = (e.get("extraction_text") or "")  # 툴팁
        nodes.append({
            "id": node_id,
            "label": label or cls,
            "group": cls,
            "title": title
        })
        by_cls.setdefault(cls, []).append(node_id)

    def connect(src_cls, dst_cls):
        for s in by_cls.get(src_cls, []):
            for d in by_cls.get(dst_cls, []):
                edges.append({"from": s, "to": d})

    # 규칙 연결
    connect("Condition", "Human_Action")
    connect("Procedure_or_Regulation", "Human_Action")
    connect("Human_Action", "Outcome")
    connect("Cause", "Outcome")
    if by_cls.get("CorrectiveAction"):
        if by_cls.get("Procedure_or_Regulation"):
            connect("CorrectiveAction", "Procedure_or_Regulation")
        else:
            connect("CorrectiveAction", "Outcome")

    return {"nodes": nodes, "edges": edges}


def create_visualization_html(jsonl_path, html_output_path):
    """
    LER 시각화 HTML 생성 (Text / Graph 라디오 토글은 네비게이션 위로 분리, Lock 버튼 제거)
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Licensee Event Reports Analysis</title>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style>
            body { font-family: 'Montserrat','Segoe UI',Tahoma,Geneva,Verdana,sans-serif; line-height: 1.7; color:#333; background:#f4f4f4; margin:0; padding:0; display:flex; flex-direction:column; min-height:100vh; }
            .container { width:80%; max-width:1200px; padding:30px; background:#fff; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1); margin:20px auto 16px; }
            h1 { color:#19181d; margin:0 0 20px; text-align:center; }
            .document-container { border:1px solid #e0e0e0; border-radius:6px; padding:15px; margin-bottom:20px; background:#fff; display:none; }
            .metadata { font-size:.9em; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid #eee; }
            .metadata span { font-weight:bold; color:#555; }

            .view-controls { display:flex; align-items:center; justify-content:center; gap:14px; margin:8px 0 10px; }
            .view-controls label { font-size:0.95em; }

            .navigation { text-align:center; margin:12px 0 12px; display:flex; align-items:center; justify-content:center; gap:10px; flex-wrap:wrap; }
            .nav-button { padding:10px 22px; font-size:16px; cursor:pointer; background:#377cf5; color:#fff; border:none; border-radius:6px; }
            .nav-button:hover { filter:brightness(.95); }
            #doc-counter { font-size:1em; color:#555; margin:0 6px; }

            .tabs { display:flex; border-bottom:2px solid #ddd; margin-bottom:10px; gap:6px; }
            .tab-button { padding:8px 14px; cursor:pointer; background:#f1f1f1; border:1px solid #ddd; border-bottom:none; border-top-left-radius:6px; border-top-right-radius:6px; font-size:.95em; }
            .tab-button.active { background:#fff; color:#000; font-weight:600; }
            .tab-content { display:none; }
            .tab-content.active { display:block; }

            .graph-container { width:100%; height:600px; border:1px solid #ddd; border-radius:4px; }

            .text-content { white-space:pre-wrap; word-wrap:break-word; font-size:1em; line-height:1.6; }
            .highlight { color:#333; padding:2px 6px; border-radius:9999px; font-weight:600; cursor:pointer; transition:opacity .2s; }
            .highlight:hover { opacity:.85; }
            .highlight-Condition { background:#d1e9f7; }
            .highlight-Procedure_or_Regulation { background:#d1f7e9; }
            .highlight-Human_Action { background:#e9d1f7; }
            .highlight-Outcome { background:#f7d1d1; }
            .highlight-Cause { background:#f7f1d1; }
            .highlight-CorrectiveAction { background:#d1f7f7; }
            .clicked-underline { text-decoration:underline; color:#C41230; }

            .legend { margin:0 0 16px; padding:15px; background:#f0f0f0; border-radius:6px; }
            .legend h3 { margin:0 0 8px; font-size:1.05em; color:#555; }
            .legend ul { list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; gap:10px; }
            .legend li { display:inline-flex; align-items:center; gap:6px; font-size:.85em; color:#555; padding:5px 12px; border-radius:9999px; background:#fff; border:1px solid #e6e6e6; }

            #details-box { min-height:50px; border:1px solid #ddd; padding:10px; margin-top:14px; background:#f9f9f9; border-radius:4px; font-size:.92em; }
            #details-box h3 { margin:0 0 6px; }
            #details-box .no-selection-message { color:#777; }

            #attribute-explanation { width:80%; max-width:1200px; margin:0 auto 28px; padding:15px; background:#fff; border:1px solid #e0e0e0; border-radius:6px; font-size:.9em; }
            #attribute-explanation h3 { margin:0 0 8px; color:#555; font-size:1.2em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Licensee Event Reports Analysis</h1>
            {legend_content}

            <div class="view-controls">
                <label><input type="radio" name="view-mode" value="text" checked> Text</label>
                <label><input type="radio" name="view-mode" value="graph"> Graph</label>
            </div>

            <div class="navigation">
                <button class="nav-button" onclick="prevDocument()">Previous</button>
                <span id="doc-counter"></span>
                <button class="nav-button" onclick="nextDocument()">Next</button>
            </div>

            {content}

            <div id="details-box">
                <p class="no-selection-message">Click on a highlighted entity to see its details.</p>
            </div>
        </div>

        <div id="attribute-explanation">
            <h3>Attributes Definition</h3>
            <p>Extracted items may include an <strong>attributes</strong> dictionary providing secondary classification or context.</p>
            <ul>
                <li><strong>Cause</strong> may include <code>category</code> (e.g., <code>conflicting_procedure</code>).</li>
                <li><strong>CorrectiveAction</strong> may include <code>action_type</code> (e.g., <code>revision</code>).</li>
            </ul>
        </div>

        <script>
          const documents = document.querySelectorAll('.document-container');
          let currentIndex = 0;
          let activeTab = {};
          let lastTab = 'text';
          const entityColors = {"Condition":"#d1e9f7","Procedure_or_Regulation":"#d1f7e9","Human_Action":"#e9d1f7","Outcome":"#f7d1d1","Cause":"#f7f1d1","CorrectiveAction":"#d1f7f7"};
          const networks = {};

          function getRadioView() {
            const r = document.querySelector('input[name="view-mode"]:checked');
            return r ? r.value : 'text';
          }
          function setRadioView(v) {
            const el = document.querySelector('input[name="view-mode"][value="'+v+'"]');
            if (el) el.checked = true;
          }

          function drawGraph(container, graphData) {
            if (!container || !graphData || !Array.isArray(graphData.nodes)) return;
            if (networks[container.id]) return;
            const data = { nodes: new vis.DataSet(graphData.nodes), edges: new vis.DataSet(graphData.edges || []) };
            const options = {
              nodes: { shape:'box', margin:10, widthConstraint:{maximum:220}, font:{size:14} },
              edges: { arrows:{to:{enabled:true, scaleFactor:1}}, smooth:{type:'cubicBezier'} },
              layout: { hierarchical:{ enabled:true, levelSeparation:220, nodeSpacing:140, treeSpacing:220, direction:'LR', sortMethod:'directed' } },
              physics: { enabled:false },
              groups: Object.keys(entityColors).reduce((a,k)=>{ a[k]={ color:{ background:entityColors[k], border:'#aaa' }}; return a; },{})
            };
            networks[container.id] = new vis.Network(container, data, options);
          }

          function switchTab(docIndex, tabName) {
            const doc = documents[docIndex];
            if (!doc) return;
            doc.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            const btn = doc.querySelector('.tab-button[data-tab="'+tabName+'"]');
            if (btn) btn.classList.add('active');
            doc.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const panel = doc.querySelector('.tab-content[data-tab="'+tabName+'"]');
            if (panel) panel.classList.add('active');
            activeTab[docIndex] = tabName;
            setRadioView(tabName);
            if (tabName === 'graph') {
              const graphContainer = doc.querySelector('.graph-container');
              if (graphContainer && graphContainer.dataset.graph) {
                try {
                  const graphData = JSON.parse(graphContainer.dataset.graph);
                  drawGraph(graphContainer, graphData);
                } catch(e) {}
              }
            }
          }

          function showDocument(index) {
          documents.forEach((doc,i)=>{ doc.style.display = (i===index)?'block':'none'; });
          const dc = document.getElementById('doc-counter');
          if (dc) dc.textContent = 'Document ' + (index + 1) + '/' + documents.length;

          const desired = activeTab[index] || lastTab;  // ★ 전역 라디오값(getRadioView) 쓰지 않음
          setRadioView(desired);             // ★ 라디오 UI는 표시만 맞춤
          switchTab(index, desired);

          resetDetailsBox();
          clearUnderlines();
        }



          function nextDocument() { currentIndex = (currentIndex + 1) % documents.length; showDocument(currentIndex); }
          function prevDocument() { currentIndex = (currentIndex - 1 + documents.length) % documents.length; showDocument(currentIndex); }

          function resetDetailsBox() {
            const d = document.getElementById('details-box');
            if (d) d.innerHTML = '<p class="no-selection-message">Click on a highlighted entity to see its details.</p>';
          }
          function clearUnderlines() {
            document.querySelectorAll('.clicked-underline').forEach(el => el.classList.remove('clicked-underline'));
          }

          document.addEventListener('DOMContentLoaded', () => {
            const detailsBox = document.getElementById('details-box');

            documents.forEach((doc, idx) => {
              doc.querySelectorAll('.tab-button').forEach(btn => {
                btn.addEventListener('click', () => {
                  const tab = btn.getAttribute('data-tab');
                  activeTab[idx] = tab;     // ★ 문서별 상태 갱신
                  lastTab = tab; 
                  setRadioView(tab);        // 라디오 표시 동기화
                  switchTab(idx, tab);      // 실제 전환
                });

              });
            });


            document.querySelectorAll('input[name="view-mode"]').forEach(r => {
              r.addEventListener('change', () => {
                const v = getRadioView();
                activeTab[currentIndex] = v;
                lastTab = v; 
                switchTab(currentIndex, v);
              });
            });

            document.querySelectorAll('.text-content').forEach(container => {
              container.addEventListener('click', (event) => {
                const t = event.target;
                if (t && t.classList && t.classList.contains('highlight')) {
                  clearUnderlines();
                  t.classList.add('clicked-underline');
                  let data = {};
                  try { data = JSON.parse(t.dataset.details || '{}'); } catch(e) {}
                  if (detailsBox) {
                    detailsBox.innerHTML =
                      '<h3>Extraction Details</h3>'
                      + '<p><strong>Class:</strong> ' + (data.extraction_class || '') + '</p>'
                      + '<p><strong>Text:</strong> "' + (data.extraction_text || '') + '"</p>'
                      + '<p><strong>Attributes:</strong> ' + JSON.stringify((data.attributes || {})) + '</p>';
                  }
                }
              });
            });

            if (documents.length > 0) { showDocument(currentIndex); }
          });
        </script>
    </body>
    </html>
    """

    all_docs_html = []

    extraction_classes = {
        "Condition": "#d1e9f7",
        "Procedure_or_Regulation": "#d1f7e9",
        "Human_Action": "#e9d1f7",
        "Outcome": "#f7d1d1",
        "Cause": "#f7f1d1",
        "CorrectiveAction": "#d1f7f7",
    }

    legend_items_html = "".join(
        [f'<li style="background:{color}">{cls.replace("_"," ")}</li>' for cls, color in extraction_classes.items()]
    )
    legend_html = f'<div class="legend"><h3>Highlights Legend</h3><ul>{legend_items_html}</ul></div>'
        # --- graph.json 불러오기 (LER → graph 매핑) ---
    graph_index = {}
    graph_json_path = 'graph.json'
    if os.path.exists(graph_json_path):
        try:
            with open(graph_json_path, 'r', encoding='utf-8') as gf:
                garr = json.load(gf)  # [{"ler": "...", "graph": {...}}, ...]
                for g in garr:
                    ler_id = g.get("ler")
                    gobj = g.get("graph")
                    if ler_id and isinstance(gobj, dict) and gobj.get("nodes"):
                        graph_index[str(ler_id)] = gobj
        except Exception:
            graph_index = {}

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            doc = json.loads(line)

            facility_name = doc.get("Facility_Name", "N/A")
            unit = doc.get("Unit", "N/A")
            ler = doc.get("ler", "N/A")
            title = doc.get("Title", "N/A")
            event_date = doc.get("Event_Date", "N/A")
            cfr = doc.get("CFR", "N/A")
            text = doc.get("text", "") or ""

            extractions = doc.get("Extractions", []) or []

            # 1) JSONL에 graph 있으면 사용
            graph_data = doc.get("graph") or {}

            # 2) 없거나 비어 있으면 graph.json에서 LER 매칭
            if not (isinstance(graph_data, dict) and graph_data.get("nodes")):
                graph_data = graph_index.get(str(ler), {}) or {}

            # 3) 둘 다 없으면 Extractions 기반 자동 생성
            if not (isinstance(graph_data, dict) and graph_data.get("nodes")):
                graph_data = build_graph_from_extractions(extractions)


            graph_json = json.dumps(graph_data, ensure_ascii=False)


            metadata_html = f"""
            <div class="metadata">
                <span>LER Code:</span> {html.escape(str(ler))}<br>
                <span>Title:</span> {html.escape(str(title))}<br>
                <span>Facility/Unit:</span> {html.escape(str(facility_name))} / {html.escape(str(unit))}<br>
                <span>Event Date:</span> {html.escape(str(event_date))}<br>
                <span>Reported Basis:</span> {html.escape(str(cfr))}
            </div>
            """

            highlightable = [e for e in extractions if e.get("char_interval")]
            highlightable.sort(key=lambda x: x["char_interval"]["start_pos"])
            highlighted_parts = []
            cur = 0
            for e in highlightable:
                start = int(e["char_interval"]["start_pos"])
                end = int(e["char_interval"]["end_pos"])
                cls = e.get("extraction_class", "Unknown")
                if cls == "Corrective_Action":
                    cls = "CorrectiveAction"
                details_json = json.dumps(e, ensure_ascii=False)

                highlighted_parts.append(html.escape(text[cur:start]))
                highlighted_parts.append(
                    f'<span class="highlight highlight-{cls}" data-details=\'{details_json}\' title="{html.escape(str(cls))}">'
                    f'{html.escape(e.get("extraction_text",""))}'
                    f'</span>'
                )
                cur = end
            if text:
                highlighted_parts.append(html.escape(text[cur:]))
                highlighted_text = "".join(highlighted_parts)
            else:
                highlighted_text = "No narrative text available."

            doc_html = f"""
            <div class="document-container" id="doc-{i}">
                {metadata_html}
                <div class="tabs">
                    <button class="tab-button" data-tab="text">Text View</button>
                    <button class="tab-button" data-tab="graph">Graph View</button>
                </div>
                <div class="tab-content" data-tab="text">
                    <div class="text-content">{highlighted_text}</div>
                </div>
                <div class="tab-content" data-tab="graph">
                    <div id="graph-container-{i}" class="graph-container" data-graph='{graph_json}'></div>
                </div>
            </div>
            """
            all_docs_html.append(doc_html)

    final_html = (
        html_template
        .replace("{content}", "".join(all_docs_html))
        .replace("{legend_content}", legend_html)
    )

    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)


# Default script execution
jsonl_file_path = 'extracted_keyword.jsonl'
html_file_path = 'index.html'

if os.path.exists(jsonl_file_path):
    create_visualization_html(jsonl_file_path, html_file_path)
    print(f"Successfully generated '{html_file_path}' from '{jsonl_file_path}'.")
else:
    print(f"Error: '{jsonl_file_path}' not found. Please check the path.")
