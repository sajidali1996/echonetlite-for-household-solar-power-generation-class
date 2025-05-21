import os
import datetime
from fpdf import FPDF
import subprocess
import PyPDF2

def find_latest_pdf(folder, prefix):
    if not os.path.exists(folder):
        return None
    files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith('.pdf')]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(folder, files[0])

def compare_mapping_reports(latest_path, default_path):
    # Only compare file existence and names, as PDF content comparison is non-trivial without extra libraries
    result = []
    if not latest_path or not default_path:
        return None
    result.append({'Report': 'Latest', 'Path': latest_path, 'Exists': os.path.exists(latest_path)})
    result.append({'Report': 'Default', 'Path': default_path, 'Exists': os.path.exists(default_path)})
    # Optionally, compare file sizes or modification times
    if os.path.exists(latest_path) and os.path.exists(default_path):
        result[0]['Size'] = os.path.getsize(latest_path)
        result[1]['Size'] = os.path.getsize(default_path)
        result[0]['Modified'] = datetime.datetime.fromtimestamp(os.path.getmtime(latest_path)).strftime('%Y-%m-%d %H:%M:%S')
        result[1]['Modified'] = datetime.datetime.fromtimestamp(os.path.getmtime(default_path)).strftime('%Y-%m-%d %H:%M:%S')
    return result

def extract_table_from_pdf(pdf_path, table_title):
    # Extracts lines after the table_title until the next section or end of file
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    lines = text.splitlines()
    table = []
    in_table = False
    for line in lines:
        if table_title in line:
            in_table = True
            continue
        if in_table:
            if line.strip() == '' or 'Table' in line or 'Query/Response' in line:
                break
            # Expecting: EPC  Description
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].startswith('0x'):
                table.append((parts[0], parts[1].strip()))
    return table

def make_mapping_comparison_table(latest, default):
    table = []
    for l, d in zip(latest, default):
        diff = '' if l[1] == d[1] else 'DIFFERENT'
        table.append({
            'EPC': l[0],
            'Latest Description': l[1],
            'Default Description': d[1],
            'Status': diff
        })
    return table

def save_mapping_comparison_pdf(table, filename, section):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 12, txt=f"Mapping Evaluation {section} Table Comparison", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, 'EPC', 1)
    pdf.cell(70, 10, 'Latest Description', 1)
    pdf.cell(70, 10, 'Default Description', 1)
    pdf.cell(25, 10, 'Status', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in table:
        pdf.cell(25, 10, row['EPC'], 1)
        pdf.cell(70, 10, row['Latest Description'][:35], 1)
        pdf.cell(70, 10, row['Default Description'][:35], 1)
        pdf.cell(25, 10, row['Status'], 1)
        pdf.ln()
    pdf.output(filename)

if __name__ == '__main__':
    root_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_folder = os.path.dirname(os.path.abspath(__file__))
    default_folder = os.path.join(root_folder, 'DefaultReports')
    latest_pdf = find_latest_pdf(root_folder, 'mapping_evaluation_')
    if not latest_pdf:
        print('No latest mapping evaluation PDF found. Generating using EvaluateMapping.py...')
        subprocess.run(['python', os.path.join(root_folder, 'src', 'EvaluateMapping.py')], check=True)
        latest_pdf = find_latest_pdf(root_folder, 'mapping_evaluation_')
    default_pdf = find_latest_pdf(default_folder, 'mapping_evaluation_')
    if not latest_pdf or not default_pdf:
        print('Could not find both latest and default mapping evaluation PDF files.')
    else:
        # Compare Set Property Map (0x9E) Table
        latest_n9e = extract_table_from_pdf(latest_pdf, 'Set Property Map (0x9E) Decoded Table')
        default_n9e = extract_table_from_pdf(default_pdf, 'Set Property Map (0x9E) Decoded Table')
        n9e_table = make_mapping_comparison_table(latest_n9e, default_n9e)
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'mapping_evaluation_comparison_n9e_{now}.pdf'
        save_mapping_comparison_pdf(n9e_table, pdf_filename, 'Set Property Map (0x9E)')
        print(f"PDF mapping evaluation comparison report (0x9E) saved as {pdf_filename}")
        # Compare Get Property Map (0x9F) Table
        latest_n9f = extract_table_from_pdf(latest_pdf, 'Get Property Map (0x9F) Decoded Table')
        default_n9f = extract_table_from_pdf(default_pdf, 'Get Property Map (0x9F) Decoded Table')
        n9f_table = make_mapping_comparison_table(latest_n9f, default_n9f)
        pdf_filename = f'mapping_evaluation_comparison_n9f_{now}.pdf'
        save_mapping_comparison_pdf(n9f_table, pdf_filename, 'Get Property Map (0x9F)')
        print(f"PDF mapping evaluation comparison report (0x9F) saved as {pdf_filename}")
