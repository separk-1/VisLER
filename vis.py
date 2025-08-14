import json
import os

def create_visualization_html(jsonl_path, html_output_path):
    """
    Reads a JSONL file and generates an HTML file visualizing the extracted entities with improved styling and English text.
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LER Analysis</title>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Montserrat', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.7; color: #333; background-color: #f4f4f4; margin: 0; padding: 0; display: flex; justify-content: center; align-items: flex-start; min-height: 100vh; }
            .container { width: 80%; max-width: 1200px; padding: 30px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); margin-top: 20px; }
            h1 { font-family: 'Montserrat', sans-serif; color: #19181d; margin-bottom: 20px; text-align: center; } /* CMU Red */
            .document-container { border: 1px solid #e0e0e0; border-nav-button: 6px; padding: 15px; margin-bottom: 20px; background-color: #fff; }
            .metadata { font-size: 0.9em; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .metadata span { font-weight: bold; color: #555; }
            h2 { font-size: 1.5em; color: #555; margin-top: 0; margin-bottom: 10px; }
            .text-content { white-space: pre-wrap; word-wrap: break-word; font-size: 1em; line-height: 1.6; }
            
            /* Base highlight styling for a pill-shaped look */
            .highlight { color: #333; padding: 2px 5px; border-radius: 9999px; font-weight: bold; cursor: pointer; transition: background-color 0.2s; }
            .highlight:hover { opacity: 0.8; }
            
            /* New pastel CSS classes for different extraction types and their colors */
            .highlight-Condition { background-color: #d1e9f7; } /* lighter blue */
            .highlight-Procedure_or_Regulation { background-color: #d1f7e9; } /* lighter green */
            .highlight-Human_Action { background-color: #e9d1f7; } /* lighter purple */
            .highlight-Outcome { background-color: #f7d1d1; } /* lighter red/pink */
            .highlight-Cause { background-color: #f7f1d1; } /* lighter yellow */
            .highlight-CorrectiveAction { background-color: #d1f7f7; } /* lighter cyan */

            /* New CSS for the legend to match the pill-shaped style */
            .legend { margin-top: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 6px; }
            .legend h3 { font-family: 'Montserrat', sans-serif; margin-top: 0; color: #555; font-size: 1.2em; }
            .legend ul { list-style-type: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 10px; }
            .legend li { 
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 0.8em; /* Smaller font size */
                color: #555;
                padding: 5px 12px;
                border-radius: 9999px;
                font-weight: normal; /* Remove bold */
            }
            
            /* New CSS for the click-to-underline feature */
            .clicked-underline {
                text-decoration: underline;
                color: #C41230; /* CMU Red */
            }

            /* New CSS for the details box */
            #details-box {
                min-height: 50px;
                border: 1px solid #ddd;
                padding: 10px;
                margin-top: 10px;
                background-color: #f9f9f9;
                border-radius: 4px;
                font-size: 0.9em;
            }
            #details-box h3 { margin-top: 0; }
            #details-box p { margin: 5px 0; }
            #details-box strong { color: #377cf5; }
            #details-box .no-selection-message { color: #777; }

            /* New CSS for the attribute explanation box */
            #attribute-explanation {
                margin-top: 30px;
                padding: 15px;
                background-color: #fff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 0.9em;
            }
            #attribute-explanation h3 { font-family: 'Montserrat', sans-serif; margin-top: 0; color: #555; font-size: 1.2em; }
            #attribute-explanation p { margin: 5px 0; }
            #attribute-explanation strong { color: #377cf5; }


            .entity-box { border: 1px solid #ddd; padding: 10px; margin-top: 10px; background-color: #f9f9f9; border-radius: 4px; font-size: 0.9em; }
            .entity-box strong { color: #377cf5; }
            .navigation { text-align: center; margin-top: 30px; margin-bottom: 20px; } /* Added margin-bottom */
            .nav-button { padding: 10px 25px; font-size: 16px; margin: 0 10px; cursor: pointer; background-color: #377cf5; color: #fff; border: none; border-radius: 6px; transition: background-color 0.3s ease; font-family: 'Montserrat', sans-serif; }
            .nav-button:hover { background-color: #2962ff; }
            #doc-counter { font-size: 1em; color: #555; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LER Reports Analysis</h1>
            {legend_content}
            <div class="navigation">
                <button class="nav-button" onclick="prevDocument()">Previous</button>
                <span id="doc-counter"></span>
                <button class="nav-button" onclick="nextDocument()">Next</button>
            </div>
            {content}
            <div id="details-box">
                <p class="no-selection-message">Click on a highlighted entity to see its details.</p>
            </div>
            <div id="attribute-explanation">
                <h3>Attributes Definition</h3>
                <p>Extracted items on this page may contain a dictionary of additional information called <strong>attributes</strong>.</p>
                <p>This field provides a secondary classification or detailed context for an extracted entity. For example:</p>
                <ul>
                    <li>The <strong>Cause</strong> entity includes an attribute named <strong>category</strong> (e.g., conflicting_procedure) to describe the type of cause.</li>
                    <li>The <strong>CorrectiveAction</strong> entity includes an attribute named <strong>action_type</strong> (e.g., revision) to describe the nature of the action.</li>
                </ul>
                </div>
        </div>
        <script>
            // JavaScript for document navigation
            const documents = document.querySelectorAll('.document-container');
            let currentIndex = 0;


            function showDocument(index) {
                documents.forEach((doc, i) => {
                    doc.style.display = (i === index) ? 'block' : 'none';
                });
                document.getElementById('doc-counter').textContent = `Document ${index + 1}/${documents.length}`;
            }


            function nextDocument() {
                currentIndex = (currentIndex + 1) % documents.length;
                showDocument(currentIndex);
            }


            function prevDocument() {
                currentIndex = (currentIndex - 1 + documents.length) % documents.length;
                showDocument(currentIndex);
            }


            if (documents.length > 0) {
                showDocument(currentIndex);
            }
            
            // New JavaScript for click-to-underline functionality and details box
            document.addEventListener('DOMContentLoaded', () => {
                const detailsBox = document.getElementById('details-box');
                let lastClickedElement = null;

                document.querySelectorAll('.text-content').forEach(container => {
                    container.addEventListener('click', (event) => {
                        if (event.target.classList.contains('highlight')) {
                            // Clear previous underline and apply new one
                            if (lastClickedElement) {
                                lastClickedElement.classList.remove('clicked-underline');
                            }
                            event.target.classList.add('clicked-underline');
                            lastClickedElement = event.target;

                            // Display details in the details box
                            const extractionData = JSON.parse(event.target.dataset.details);
                            let attributesHtml = '';
                            if (extractionData.attributes) {
                                attributesHtml = '<br>Attributes: ' + JSON.stringify(extractionData.attributes);
                            }
                            detailsBox.innerHTML = `
                                <h3>Extraction Details</h3>
                                <p><strong>Class:</strong> ${extractionData.extraction_class}</p>
                                <p><strong>Text:</strong> "${extractionData.extraction_text}"</p>
                                <p><strong>Attributes:</strong> ${JSON.stringify(extractionData.attributes)}</p>
                            `;
                        }
                    });
                });

                // Clear details box when navigating
                document.querySelectorAll('.nav-button').forEach(button => {
                    button.addEventListener('click', () => {
                        detailsBox.innerHTML = '<p class="no-selection-message">Click on a highlighted entity to see its details.</p>';
                        if (lastClickedElement) {
                            lastClickedElement.classList.remove('clicked-underline');
                            lastClickedElement = null;
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    """

    all_docs_html = []
    
    # Define the extraction classes for the legend with new pastel colors
    extraction_classes = {
        "Condition": "#d1e9f7", 
        "Procedure_or_Regulation": "#d1f7e9", 
        "Human_Action": "#e9d1f7", 
        "Outcome": "#f7d1d1", 
        "Cause": "#f7f1d1", 
        "CorrectiveAction": "#d1f7f7"
    }
    
    # Generate the legend HTML
    legend_items_html = "".join(
        [f'<li style="background-color: {color};">{cls}</li>' for cls, color in extraction_classes.items()]
    )
    legend_html = f"""
    <div class="legend">
        <h3>Highlights Legend</h3>
        <ul>
            {legend_items_html}
        </ul>
    </div>
    """

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            doc = json.loads(line)
            
            # Read metadata from the JSONL structure
            facility_name = doc.get("Facility_Name", "N/A")
            unit = doc.get("Unit", "N/A")
            ler = doc.get("ler", "N/A")
            title = doc.get("Title", "N/A")
            event_date = doc.get("Event_Date", "N/A")
            cfr = doc.get("CFR", "N/A")
            text = doc.get('text', '')
            
            extractions = doc.get('Extractions', [])

            # Generate the combined metadata HTML, reordered as requested
            metadata_html = f"""
            <div class="metadata">
                <span>LER Code:</span> {ler}<br>
                <span>Title:</span> {title}<br>
                <span>Facility/Unit:</span> {facility_name} / {unit}<br>
                <span>Event Date:</span> {event_date}<br>
                <span>Reported Basis:</span> {cfr}<br>
            </div>
            """
            highlightable_extractions = [e for e in extractions if e.get('char_interval')]
            highlightable_extractions.sort(key=lambda x: x['char_interval']['start_pos'])

            highlighted_text = ""
            current_pos = 0

            if text:
                for extraction in highlightable_extractions:
                    start = extraction['char_interval']['start_pos']
                    end = extraction['char_interval']['end_pos']
                    extraction_text = extraction['extraction_text']
                    extraction_class = extraction['extraction_class']

                    # Pass all extraction details as a data attribute on the span
                    details_json = json.dumps(extraction, ensure_ascii=False)
                    
                    highlighted_text += text[current_pos:start]
                    highlighted_text += (
                        f'<span class="highlight highlight-{extraction_class}" '
                        f'data-details=\'{details_json}\' '
                        f'title="{extraction_class}">'
                        f'{extraction_text}'
                        '</span>'
                    )
                    current_pos = end

                highlighted_text += text[current_pos:]
            else:
                highlighted_text = "No narrative text available."

            doc_html = f"""
            <div class="document-container">
                {metadata_html}
                <div class="text-content">{highlighted_text}</div>
            </div>
            """
            all_docs_html.append(doc_html)

    # Replace the content and legend placeholders in the template
    final_html_content = html_template.replace("{content}", "".join(all_docs_html)).replace("{legend_content}", legend_html)

    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(final_html_content)


# Script execution
jsonl_file_path = 'extracted.jsonl'
html_file_path = 'index.html'

if os.path.exists(jsonl_file_path):
    create_visualization_html(jsonl_file_path, html_file_path)
    print(f"Successfully generated '{html_file_path}' from '{jsonl_file_path}'.")
else:
    print(f"Error: '{jsonl_file_path}' not found. Please check the path.")