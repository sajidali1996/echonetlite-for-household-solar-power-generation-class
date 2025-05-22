"""
new_physical_property_test.py: Automated Physical Property Test for Settable EPCs

This script tests the settable EPCs listed in 'new physical test.txt' by:
- Reading and storing the initial value
- Setting a new value within the allowed range
- Waiting 1 second
- Reading the updated value
- Reverting to the initial value
- Recording Pass/Fail verdict
- Generating a PDF report with EPC, initial value, updated value, verdict, and timestamp

Usage:
    python new_physical_property_test.py
"""
import sys
import os
import time
import datetime
from fpdf import FPDF
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from enl_class import EchonetLiteClient

# List of settable EPCs and their value ranges (from new physical test.txt)
EPC_TESTS = [
    # (EPC, description, allowed_values or (min, max), bytes_len, example_new_value)
    (0x80, "Operation status", [0x30, 0x31], 1, 0x30),
    (0x81, "Installation location", None, 1, 0x01),  # Example: set to 0x01
    (0x97, "Current time setting", None, 2, b'\x12\x34'),  # Example: 12:34
    (0x98, "Current date setting", None, 4, b'\x07\xE9\x05\x16'),  # Example: 2025-05-22
    (0xA0, "Output power control setting 1", (0x00, 0x64), 1, 0x01),
    (0xA1, "Output power control setting 2", (0x0000, 0xFFFD), 2, 0x0001),
    (0xA2, "Function to control purchase of excess electricity", [0x41, 0x42], 1, 0x41),
    (0xC1, "FIT contract type", [0x41, 0x42, 0x43], 1, 0x41),
    (0xE2, "Reset cumulative amount of electric energy generated", [0x00], 1, 0x00),
    (0xE4, "Reset cumulative amount of electric energy sold", [0x00], 1, 0x00),
    (0xE5, "Power generation output as % of rated", (0x00, 0x64), 1, 0x01),
    (0xE6, "Power generation output in watts", (0x0000, 0xFFFD), 2, 0x0001),
    (0xE7, "Electricity sold in watts", (0x0000, 0xFFFD), 2, 0x0001),
    (0xE8, "Rated power output (system-interconnection)", (0x0000, 0xFFFD), 2, 0x0001),
    (0xE9, "Rated power output (independent)", (0x0000, 0xFFFD), 2, 0x0001),
]

# Helper to get device IP from credentials.txt
def get_ip_from_credentials(filename='credentials.txt'):
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('IP='):
                return line.strip().split('=', 1)[1]
    raise ValueError('IP not found in credentials file')

def to_bytes(val, length):
    if isinstance(val, bytes):
        return val
    return val.to_bytes(length, 'big')

def from_bytes(val):
    if isinstance(val, bytes):
        return val.hex().upper()
    return str(val)

def save_report_as_pdf(report, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="ECHONET Lite Physical Property Test Report", ln=True, align='C')
    pdf.cell(0, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 10, 'EPC', 1)
    pdf.cell(60, 10, 'Description', 1)
    pdf.cell(40, 10, 'Initial Value', 1)
    pdf.cell(40, 10, 'Updated Value', 1)
    pdf.cell(20, 10, 'Verdict', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in report:
        pdf.cell(20, 10, row['EPC'], 1)
        pdf.cell(60, 10, row['Description'][:30], 1)
        pdf.cell(40, 10, row['Initial Value'], 1)
        pdf.cell(40, 10, row['Updated Value'], 1)
        pdf.cell(20, 10, row['Verdict'], 1)
        pdf.ln()
    pdf.output(filename)

def main():
    ip = get_ip_from_credentials()
    report = []
    for epc, desc, allowed, length, example_new in EPC_TESTS:
        client = EchonetLiteClient(ip)  # Re-instantiate client for each EPC
        # 1. Read initial value
        client.send_query(0x62, epc)
        print(f"Testing EPC: 0x{epc:02X} - {desc}")
        resp = client.listen_response(timeout=2)
        print(f"Response: {resp}")
        initial_val = None
        if 'properties' in resp:
            for prop in resp['properties']:
                if prop['epc'] == epc:
                    initial_val = prop['edt']
                    break
        initial_val_str = from_bytes(initial_val) if initial_val else 'No response'
        # 2. Set new value (different from initial if possible)
        if allowed is not None:
            if isinstance(allowed, list):
                new_val = allowed[0] if initial_val is None or initial_val != to_bytes(allowed[0], length) else allowed[-1]
            elif isinstance(allowed, tuple):
                minv, maxv = allowed
                new_val = minv if initial_val is None or int.from_bytes(initial_val, 'big') != minv else minv+1
            else:
                new_val = example_new
        else:
            new_val = example_new
        new_val_bytes = to_bytes(new_val, length)
        # 3. Write new value
        client.send_command(0x60, epc, new_val_bytes)
        #time.sleep(2)
        # 4. Read updated value
        client.send_query(0x62, epc)
        resp2 = client.listen_response(timeout=2)
        updated_val = None
        if 'properties' in resp2:
            for prop in resp2['properties']:
                if prop['epc'] == epc:
                    updated_val = prop['edt']
                    break
        updated_val_str = from_bytes(updated_val) if updated_val else 'No response'
        # 5. Verdict
        verdict = 'Pass' if initial_val != updated_val and updated_val is not None else 'Fail'
        # 6. Revert to initial value if possible
        if initial_val is not None:
            client.send_command(0x60, epc, initial_val)
            time.sleep(2)
        report.append({
            'EPC': f'0x{epc:02X}',
            'Description': desc,
            'Initial Value': initial_val_str,
            'Updated Value': updated_val_str,
            'Verdict': verdict
        })
        client.close()
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f'physical_property_test_report_{now}.pdf'
    save_report_as_pdf(report, pdf_filename)
    print(f"PDF report saved as {pdf_filename}")

if __name__ == '__main__':
    main()
