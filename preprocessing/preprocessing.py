import pandas as pd
import re

def full_preprocessing(input_file, output_file):
    """
    Performs all requested preprocessing steps on the original data.

    Args:
        input_file (str): The path to the original CSV file.
        output_file (str): The path where the final preprocessed CSV file will be saved.
    """
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return

    # 1. Clean the 'Facility Name' column by removing quotes and extra spaces
    if 'Facility Name' in df.columns:
        # A more robust regex to remove various types of quotes and extra spaces.
        df['Facility Name'] = df['Facility Name'].str.strip().str.replace(r"['\"“”‘’]", '', regex=True)

    # 2. Extract Unit information and create a new 'Unit' column
    df['Unit'] = df['Facility Name'].str.extract(r'(?:Unit No\.\s*|Unit\s*)(\d+)')
    df['Unit'] = df['Unit'].fillna('Unknown Unit')
    
    # 3. Remove the unit information and LER-related numbers from 'Facility Name'
    df['Facility Name'] = df['Facility Name'].str.replace(r'Unit No\.\s*\d+|Unit\s*\d+', '', regex=True, flags=re.IGNORECASE)
    df['Facility Name'] = df['Facility Name'].str.replace(r'\s*\d+\s+OF\s+\d+|\s*\d+', '', regex=True, flags=re.IGNORECASE)
    df['Facility Name'] = df['Facility Name'].str.replace(r'^\s*,\s*', '', regex=True)
    df['Facility Name'] = df['Facility Name'].str.strip().str.rstrip(',')
    df['Facility Name'] = df['Facility Name'].str.replace(r'^\d+\s*', '', regex=True)
    df['Facility Name'] = df['Facility Name'].str.strip()
    
    # 4. Rename columns as requested
    df = df.rename(columns={'content_3': 'cfr_desc_1', 'content_4': 'cfr_desc_2'})
    df.columns = df.columns.str.lower().str.replace(' ', '_', regex=False)

    # 5. Reorder columns to place 'unit' immediately after 'facility_name'
    cols = df.columns.tolist()
    if 'unit' in cols and 'facility_name' in cols:
        cols.remove('unit')
        idx = cols.index('facility_name')
        cols.insert(idx + 1, 'unit')
        df = df[cols]

    # 6. Save the cleaned DataFrame to the fixed output file name
    df.to_csv(output_file, index=False)
    print(f"All preprocessing steps successfully completed and data saved to '{output_file}'.")

if __name__ == '__main__':
    input_csv = '01_merged.csv'
    output_csv = '02_preprocessed.csv'
    full_preprocessing(input_csv, output_csv)