import re
import csv
from datetime import datetime

# Define the regex patterns to match dates in the formats YYYY-MM-DD and DD/MM/YYYY
pattern_yyyymmdd = re.compile(r'\d{4}-\d{2}-\d{2}')
pattern_ddmmyyyy = re.compile(r'\d{2}/\d{2}/\d{4}')

# Function to convert date format from YYYY-MM-DD to MM/DD/YY
def convert_yyyymmdd_to_mmddyy(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%m/%d/%y')

# Function to convert date format from DD/MM/YYYY to MM/DD/YY
def convert_ddmmyyyy_to_mmddyy(date_str):
    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    return date_obj.strftime('%m/%d/%y')

try:
    # Read the CSV file
    with open('NetflixViewingHistory.csv', 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)

    # Process each row to convert date formats
    new_rows = []
    for row in rows:
        new_row = row[:]
        date_str = row[1]
        if pattern_yyyymmdd.match(date_str):
            new_row[1] = convert_yyyymmdd_to_mmddyy(date_str)
        elif pattern_ddmmyyyy.match(date_str):
            new_row[1] = convert_ddmmyyyy_to_mmddyy(date_str)
        new_rows.append(new_row)

    # Write the modified rows to a temporary CSV file
    temp_file = 'NetflixViewingHistory_temp.csv'
    with open(temp_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(new_rows)

    # Replace the original file with the temporary file
    import os
    os.replace(temp_file, 'NetflixViewingHistory.csv')

except PermissionError as e:
    print(f"PermissionError: {e}")
    print("Ensure the file is not open in another program and you have the necessary permissions.")