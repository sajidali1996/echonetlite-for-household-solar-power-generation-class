import os
import csv
from fpdf import FPDF
import datetime
import subprocess

def find_latest_csv(folder):
    files = [f for f in os.listdir(folder) if f.startswith('epc_report_') and f.endswith('.csv')]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(folder, files[0])

def read_csv_rows(filepath):
    rows = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append((row['EPC'], row['Description'], row['Value']))
    return rows

def make_comparison_table(latest, default):
    table = []
    for l, d in zip(latest, default):
        diff = '' if l[2] == d[2] else 'DIFFERENT'
        table.append({
            'EPC': l[0],
            'Description': l[1],
            'Latest Value': l[2],
            'Default Value': d[2],
            'Status': diff
        })
    return table

def save_comparison_pdf(table, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 12, txt="EPC Report Comparison", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, 'EPC', 1)
    pdf.cell(60, 10, 'Description', 1)
    pdf.cell(35, 10, 'Latest Value', 1)
    pdf.cell(35, 10, 'Default Value', 1)
    pdf.cell(25, 10, 'Status', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in table:
        pdf.cell(25, 10, row['EPC'], 1)
        pdf.cell(60, 10, row['Description'][:30], 1)
        pdf.cell(35, 10, row['Latest Value'][:16], 1)
        pdf.cell(35, 10, row['Default Value'][:16], 1)
        pdf.cell(25, 10, row['Status'], 1)
        pdf.ln()
    pdf.output(filename)

if __name__ == '__main__':
    # Fix: root_folder should be the project root, not the tests folder
    root_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_folder = os.path.dirname(os.path.abspath(__file__))
    default_folder = os.path.join(root_folder, 'DefaultReports')
    latest_csv = find_latest_csv(root_folder)
    if not latest_csv:
        # Generate latest CSV if not present
        print('No latest CSV found. Generating using epc_report_query_csv.py...')
        subprocess.run(['python', os.path.join(root_folder, 'src', 'epc_report_query_csv.py')], check=True)
        latest_csv = find_latest_csv(root_folder)
    default_csv = find_latest_csv(default_folder)
    if not latest_csv or not default_csv:
        print('Could not find both latest and default CSV files.')
    else:
        latest_rows = read_csv_rows(latest_csv)
        default_rows = read_csv_rows(default_csv)
        table = make_comparison_table(latest_rows, default_rows)
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'epc_report_comparison_{now}.pdf'
        save_comparison_pdf(table, pdf_filename)
        print(f"PDF comparison report saved as {pdf_filename}")
