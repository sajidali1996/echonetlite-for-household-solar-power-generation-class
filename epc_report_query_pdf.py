import tabulate
from enl_class import EchonetLiteClient
import datetime
from fpdf import FPDF

# List of EPCs to query (as integers)
EPCS = [
    0x80, 0x81, 0x82, 0x83, 0x88, 0x89, 0x8A, 0x8C, 0x97, 0x98, 0x9D, 0x9E, 0xA0, 0xA1, 0xA2, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xD0, 0xD1, 0xE0, 0xE1, 0xE3, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9
]

def describe_epc(epc, edt):
    desc = EchonetLiteClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
    if edt is None:
        return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': 'No response'}
    # Show value as hex string
    value = edt.hex().upper() if isinstance(edt, (bytes, bytearray)) else str(edt)
    return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': value}

def get_ip_from_credentials(filename='credentials.txt'):
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('IP='):
                return line.strip().split('=', 1)[1]
    raise ValueError('IP not found in credentials file')

def wrap_text(text, width):
    import textwrap
    return '\n'.join(textwrap.wrap(str(text), width=width))

def save_report_as_pdf(report, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="ECHONET Lite GetMap EPC Report", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(10)
    # Table header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, 'EPC', 1)
    pdf.cell(90, 10, 'Description', 1)
    pdf.cell(60, 10, 'Value', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in report:
        epc = wrap_text(row['EPC'], 18)
        desc = wrap_text(row['Description'], 40)
        value = wrap_text(row['Value'], 30)
        epc_lines = epc.split('\n')
        desc_lines = desc.split('\n')
        value_lines = value.split('\n')
        max_lines = max(len(epc_lines), len(desc_lines), len(value_lines))
        # Ensure all columns have the same number of lines
        epc_lines += [''] * (max_lines - len(epc_lines))
        desc_lines += [''] * (max_lines - len(desc_lines))
        value_lines += [''] * (max_lines - len(value_lines))
        # Calculate cell height based on number of lines
        cell_height = 5  # 5 units per line for compactness
        for i in range(max_lines):
            pdf.cell(40, cell_height, epc_lines[i], border=1)
            pdf.cell(90, cell_height, desc_lines[i], border=1)
            pdf.cell(60, cell_height, value_lines[i], border=1)
            pdf.ln(cell_height)
    pdf.output(filename)

def main():
    ip = get_ip_from_credentials()
    client = EchonetLiteClient(ip)
    report = []
    for epc in EPCS:
        client.send_query(0x62, epc)
        resp = client.listen_response()
        edt = None
        if 'properties' in resp:
            for prop in resp['properties']:
                if prop['epc'] == epc:
                    edt = prop['edt']
                    break
        report.append(describe_epc(epc, edt))
    print(tabulate.tabulate(report, headers='keys'))
    # Save PDF with current date and time
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f'epc_report_{now}.pdf'
    save_report_as_pdf(report, pdf_filename)
    print(f"PDF report saved as {pdf_filename}")
    client.close()

if __name__ == '__main__':
    main()
