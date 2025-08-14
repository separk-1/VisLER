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
    Extract the following structured information from the provided text:
    - `Procedure_or_Regulation`: The name or description of the official procedure, regulation, or technical specification.
    - `Cause`: The root cause of the deviation, which explains why the human's decision-making differed from the formal procedure.
    - The `Cause` entity must be categorized into one of the following four classes, based on the text:
        - `misapplied_procedure`: The human didn't know the procedure should be applied, or applied it when they shouldn't have. (e.g., Unclear goal state)
        - `misinterpreted_procedure`: The human misunderstood the procedure and applied it incorrectly. (e.g., Unclear interpretation)
        - `conflicting_procedure`: The procedure itself was flawed, inadequate, or conflicted with other regulations, making it difficult to follow. (e.g., Unclear solution path)
        - `not_applicable`: The deviation was caused by an external factor not related to a procedure or regulation described in the text.
    
    Provide precise, non-paraphrased extractions. Your output must strictly follow the provided example format.""")

# 3. Define examples for the model to learn the extraction format
examples = [
    lx.data.ExampleData(
        # A portion of the original text for AI to analyze
        text="""EVENT CAUSE ANALYSIS The cause of this event was determined to be an inadequate procedure step. The procedure 3-AOP-202 required a manual actuation of the RPS, when responding to low gland steam pressure, without first checking status of the reactor trip breakers. Since the reactor trip breakers were already open, the procedurally directed reactor trip was an unnecessary RPS actuation. ... CORRECTIVE ACTIONS Procedure 3-AOP-202, "Condensate System Malfunctions," was revised...""",
        
        # The structure and content of the result that the AI should extract from the text above
        extractions=[
            # 1. Condition
            lx.data.Extraction(
                extraction_class="Condition",
                extraction_text="low gland steam pressure",
                attributes={"trigger": "manual actuation"}
            ),
            # 2. Procedure_or_Regulation
            lx.data.Extraction(
                extraction_class="Procedure_or_Regulation",
                extraction_text='Procedure 3-AOP-202, "Condensate System Malfunctions,"',
                attributes={"status": "inadequate"}
            ),
            # 3. Human_Action
            lx.data.Extraction(
                extraction_class="Human_Action",
                extraction_text="manual actuation of the RPS",
                attributes={"adherence": "followed"}
            ),
            # 4. Outcome
            lx.data.Extraction(
                extraction_class="Outcome",
                extraction_text="an unnecessary RPS actuation",
                attributes={"consequence": "unnecessary"}
            ),
            # 5. Cause (same as before)
            lx.data.Extraction(
                extraction_class="Cause",
                extraction_text="inadequate procedure step",
                attributes={"category": "conflicting_procedure"}
            ),
            # 6. Corrective_Action
            lx.data.Extraction(
                extraction_class="CorrectiveAction",
                extraction_text='Procedure 3-AOP-202, "Condensate System Malfunctions," was revised to require checking reactor trip breakers are not open prior to manually tripping the reactor when responding to gland steam pressure below the AOP\'s established limit.',
                attributes={"action_type": "revision"}
            ),
        ]
    )
]

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