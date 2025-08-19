import pandas as pd
import langextract as lx
import textwrap
import os
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("LANGEXTRACT_API_KEY")

# 1. Load data from file
try:
    df = pd.read_csv('ler_structured_with_cfr.csv')
    print("Successfully loaded file. Printing the first 2 rows:")
    print(df.head(2).to_markdown(index=False, numalign="left", stralign="left"))
except FileNotFoundError:
    print("Error: 'ler_structured_with_cfr.csv' file not found. Please ensure the file is in the same directory.")
    exit()

# 2. Define the extraction prompt for the research purpose
prompt_description = textwrap.dedent("""\
    Extract the following structured information from the provided text.
    Return precise, non-paraphrased spans copied from the text (short and specific).
    Use multiple extractions per class if clearly supported by the text.
    If a class is not mentioned, you may omit it EXCEPT for `Cause` (see rules below).

    CLASSES TO EXTRACT
    - `Condition`: The initiating plant condition/state that triggered the event (alarms, sensor states, abnormal parameters).
        • attributes example: {"trigger": "..."}
    - `Procedure_or_Regulation`: The procedure, regulation, or technical specification referenced or applied.
        • attributes example: {"status": "inadequate / applicable / misunderstood / violated / followed"}
    - `Human_Action`: The actual operator/human action taken.
        • attributes example: {"adherence": "followed / not_followed / misinterpreted"}
    - `Outcome`: The consequence/effect resulting from the condition or action.
        • attributes example: {"consequence": "reactor trip / AFW actuation / unnecessary / unintended"}
    - `Cause`: The root cause of the deviation. You MUST always return at least ONE `Cause`.
        • attributes MUST include both `category` and `code` chosen from the scheme below.
        • If the text indicates no procedure-related issue, still return one `Cause` with `category: not_applicable` and `code: NA`, and use a short external-cause span (e.g., "lightning strike").
    - `CorrectiveAction`: Corrective or follow-up actions (procedure revision, training, maintenance, design change, software change).
        • attributes example: {"action_type": "revision / training / maintenance / software change"}

    CAUSE CATEGORY & CODE SCHEME (pick exactly one code for the main/root cause)
    - MA1 (misapplied_procedure): Procedure should have been applied but was NOT applied.
    - MA2 (misapplied_procedure): Procedure should NOT have been applied, but WAS applied (e.g., entry criteria not met).
    - MI  (misinterpreted_procedure): Operator misunderstood/misread the step or intent.
    - CF1 (conflicting_procedure): Procedure assumptions conflict with actual plant conditions (infeasible as-found state).
    - CF2 (conflicting_procedure): Procedure conflicts with other regulations/specs (e.g., Technical Specifications).
    - CF3 (conflicting_procedure): Intrinsic defect/incorrect or wrong step in the procedure.
    - CF4 (conflicting_procedure): Insufficient or ambiguous procedure description.
    - NA  (not_applicable): External cause unrelated to procedures/regulations (e.g., weather, random equipment failure).

    OUTPUT REQUIREMENTS
    - Use the example format provided (one object per extraction): {extraction_class, extraction_text, attributes}.
    - `attributes` for `Cause` MUST include BOTH: {"category": "...", "code": "..."} according to the scheme above.
    - Prefer contiguous spans from the text; do NOT invent or generalize beyond the text.
    - If multiple plausible causes are mentioned, choose the primary/root cause identified in the text.
""")

# 3. Define examples for the model to learn the extraction format
EXAMPLE_JSON_PATH = "examples.json"

def to_list_maybe(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def build_extractions_from_json(example_case):
    """Convert one JSON case into a list of lx.data.Extraction objects.
       Supports single object or list per class key.
    """
    extractions = []
    CLASS_KEYS = [
        "Condition",
        "Procedure_or_Regulation",
        "Human_Action",
        "Outcome",
        "Cause",
        "Corrective_Action",   
    ]
    for cls in CLASS_KEYS:
        if cls in example_case and example_case[cls] is not None:
            for item in to_list_maybe(example_case[cls]):
                extraction_text = item.get("extraction_text", "")
                attributes = item.get("attributes", {}) or {}
                extractions.append(
                    lx.data.Extraction(
                        extraction_class=cls,
                        extraction_text=extraction_text,
                        attributes=attributes
                    )
                )
    return extractions

# Load examples.json
with open(EXAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
    examples_data = json.load(f)

# Match each example's text by LER (CSV 'File Name') to use real Narrative as ExampleData.text
examples = []
missing_ler = []
for case in examples_data:
    ler_id = case.get("ler", "")
    match = df.loc[df["File Name"] == ler_id]
    if match.empty:
        raw_text = case.get("text", "")
        if not raw_text:
            missing_ler.append(ler_id)
            continue
    else:
        raw_text = str(match.iloc[0]["Narrative"] or "")

    exts = build_extractions_from_json(case)
    examples.append(
        lx.data.ExampleData(
            text=raw_text,
            extractions=exts
        )
    )

print(f"[Examples] built: {len(examples)}; missing LER matches: {missing_ler}")
# === End JSON example loader ===

# 4. Run extraction for each document in the dataset
combined_results = []
# To extract the entire dataset, change `df.head(5)` to `df`.
for index, row in df.iterrows():
    input_text = row['Narrative']
    print(f"\n--- Processing Row {index} ---")
    try:
        # Extract information from the text
        result = lx.extract(
            text_or_documents=input_text,
            prompt_description=prompt_description,
            examples=examples,
            model_id="gemini-2.5-flash",
        )
        
        # Helper function to convert the `Extraction` object to a dictionary
        def extraction_to_dict(extraction):
            # Create a dictionary from the CharInterval object's attributes
            char_interval_data = None
            if extraction.char_interval:
                char_interval_data = {
                    'start_pos': extraction.char_interval.start_pos,
                    'end_pos': extraction.char_interval.end_pos
                }
                
            return {
                'extraction_class': extraction.extraction_class,
                'extraction_text': extraction.extraction_text,
                'attributes': extraction.attributes,
                'char_interval': char_interval_data # Store the converted dictionary
            }
            
        # Combine the extracted information with existing DataFrame data
        combined_data = {
            "Facility_Name": row['Facility Name'],
            "Unit": row['Unit'],
            "Title": row['Title'],
            "Event_Date": row['Event Date'],
            "CFR": row['CFR'],
            # Add the value of the "File Name" column to the "ler" key.
            "ler": row['File Name'], 
            "text": row['Narrative'],
            # Convert `Extraction` objects to dictionaries before saving
            "Extractions": [extraction_to_dict(e) for e in result.extractions]
        }
        
        combined_results.append(combined_data)
        print(f"Extraction successful and data combined for row {index}.")
    except Exception as e:
        print(f"Extraction failed for row {index}: {e}")
        # If extraction fails, still include the existing data with an empty extractions list
        combined_results.append({
            "Facility_Name": row['Facility Name'],
            "Unit": row['Unit'],
            "Title": row['Title'],
            "Event_Date": row['Event Date'],
            "CFR": row['CFR'],
            "ler": row['File Name'], # This part is also added
            "text": row['Narrative'],
            "Extractions": []
        })

# 5. Save the combined results to a JSONL file
output_dir = "."
output_name = "extracted.jsonl" # Revert the filename to "extracted.jsonl".
jsonl_path = os.path.join(output_dir, output_name)

# Manually save the list of dictionaries to a JSONL file
with open(jsonl_path, 'w', encoding='utf-8') as f:
    for item in combined_results:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nAll combined results have been saved to the file '{jsonl_path}'.")