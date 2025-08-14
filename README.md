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


## Acknowledgements

This project uses [LangExtract](https://github.com/google/langextract) by Google,  
licensed under the Apache License 2.0.
