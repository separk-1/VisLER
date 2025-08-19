# VisLER: LER Analysis Tool

VisLER processes CSV-formatted **Licensee Event Reports (LERs)** to extract key information and present it through interactive visualizations.

**Live Demo:** [https://vis-ler.vercel.app/](https://vis-ler.vercel.app/)
![LER analysis visualization](./images/lervis.png)



## Installation

### 1. Create and Activate Conda Environment
```bash
conda create -n visler python=3.10
conda activate visler
```

### 2. Install Dependencies

You can install dependencies individually:
```bash
pip install langextract
pip install tabulate
pip install python-dotenv
```

Or install all at once using `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Store API Key Securely
Create a `.env` file in the project root:
   ```env
   LANGEXTRACT_API_KEY=YOUR_API_KEY
   ```

## Features

- **NER-based Data Extraction**  
  `run.py` processes LER data and extracts structured entities such as:
  - `Cause`
  - `Procedure_or_Regulation`
  - `Condition`

- **HTML Visualization**  
  `vis.py` generates a HTML report (`index.html`) that visualizes extracted entities.

- **Interactive Report**  
  - Custom highlighting of entities
  - Legend explaining entity types
  - Clickable entities that display details in a side panel


## Extraction Schema

### Classes
| Class | Description | Example attributes |
|---|---|---|
| **Condition** | Initiating plant condition/state (alarms, sensor states, abnormal parameters) | `{"trigger": "..."}` |
| **Procedure_or_Regulation** | Procedure, regulation, or technical specification referenced/applied | `{"status": "inadequate / applicable / misunderstood / violated / followed"}` |
| **Human_Action** | Actual operator action | `{"adherence": "followed / not_followed / misinterpreted"}` |
| **Outcome** | Consequence/effect from the condition or action | `{"consequence": "reactor trip / AFW actuation / unnecessary / unintended"}` |
| **Cause** | Root cause (must **always** include) | `{"category": "...", "code": "MA1/MA2/MI/CF1/CF2/CF3/CF4/NA"}` |
| **CorrectiveAction** | Corrective/follow-up actions | `{"action_type": "revision / training / maintenance / software change"}` |

### Cause Category & Code Scheme
| Code | Category | Description |
|---|---|---|
| **MA1** | misapplied_procedure | Procedure should have been applied but was **not applied** |
| **MA2** | misapplied_procedure | Procedure should **not** have been applied, but **was applied** (e.g., entry criteria not met) |
| **MI** | misinterpreted_procedure | Operator misunderstood/misread step or intent |
| **CF1** | conflicting_procedure | Procedure assumptions conflict with **actual plant conditions** (infeasible as-found) |
| **CF2** | conflicting_procedure | Procedure conflicts with **other regulations/specs** (e.g., TS) |
| **CF3** | conflicting_procedure | **Intrinsic defect/incorrect** step in the procedure |
| **CF4** | conflicting_procedure | **Insufficient/ambiguous** procedure description |
| **NA** | not_applicable | External cause unrelated to procedures/regulations (e.g., weather, random equipment failure) |

---

## Acknowledgements

This project uses [LangExtract](https://github.com/google/langextract) by Google,  
licensed under the Apache License 2.0.
