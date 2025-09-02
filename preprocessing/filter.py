import pandas as pd
import re

def filter_data(input_file, output_file):
    """
    Reads a CSV file, selects specific columns, removes rows where 'facility_name'
    is empty or contains only specific unwanted characters, removes rows where
    'abstract' exceeds 5000 characters, and removes rows where other columns
    exceed 100 characters. Saves the result.

    Args:
        input_file (str): The path to the input CSV file.
        output_file (str): The path where the filtered CSV file will be saved.
    """
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return

    # Select only the columns to keep
    columns_to_keep = [
        'facility_name', 'unit', 'title', 'event_date', 'abstract',
        'file_name', 'filename', 'cfr'
    ]
    df_selected = df[columns_to_keep]

    # Filter facility_name
    df_filtered = df_selected[
        df_selected['facility_name'].notna() &
        (df_selected['facility_name'].str.strip() != '') &
        (~df_selected['facility_name'].str.strip().str.match(r'^[\s?.,-]*$', na=False))
    ]

    # Filter abstract length <= 5000
    df_filtered = df_filtered[
        df_filtered['abstract'].fillna('').str.len() <= 2500
    ]

    # Filter other columns length <= 100
    other_cols = [col for col in df_filtered.columns if col != 'abstract']
    for col in other_cols:
        df_filtered = df_filtered[df_filtered[col].fillna('').astype(str).str.len() <= 100]

    # Save the filtered DataFrame to a new CSV file.
    df_filtered.to_csv(output_file, index=False)
    print(f"Data successfully filtered. The specified columns and cleaned rows are saved to '{output_file}'.")

if __name__ == '__main__':
    input_csv = '02_preprocessed.csv'
    output_csv = '03_filtered_data.csv'
    filter_data(input_csv, output_csv)
