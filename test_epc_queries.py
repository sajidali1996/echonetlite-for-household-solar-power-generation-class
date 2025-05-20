import tabulate
from enl_class import EchonetLiteClient
from fpdf import FPDF
import time

# Detailed EPC descriptions from user-provided table
EPC_DETAILS = {
    0x80: "Operation status",
    0x81: "Installation location",
    0x82: "Standard version information",
    0x83: "Identification number",
    0x88: "Fault status",
    0x8A: "Manufacturer code",
    0x8B: "Product code",
    0x8C: "Production number",
    0x8D: "Production date",
    0x8F: "Power-saving operation setting",
    0x90: "ON timer reservation setting",
    0x91: "ON timer time setting",
    0x92: "ON timer relative time setting",
    0x93: "Remote control setting",
    0x94: "OFF timer reservation setting",
    0x95: "OFF timer time setting",
    0x96: "OFF timer relative time setting",
    0x97: "Current time setting",
    0x98: "Current date setting",
    0x99: "Power limit setting",
    0x9A: "Cumulative operating time",
    0x9B: "SetM property map",
    0x9C: "GetM property map",
    0x9D: "Status change announcement property map",
    0x9E: "Set property map",
    0x9F: "Get property map",
    0xBD: "Fault description",
    0xE0: "System interconnection status",
    0xE1: "Measured instantaneous amount of electricity generated",
    0xE2: "Measured cumulative amount of electric energy generated",
    0xE3: "Maximum amount of electricity that can be sold",
    0xE4: "Maximum amount of electricity that can be bought",
    0xE5: "Measurement time of instantaneous power generation",
    0xE6: "Power generation output limit setting 2",
    0xE7: "Limit setting for the amount of electricity sold",
    0xE8: "Rated power generation output",
    0xE9: "Power generation operation setting",
    0xC0: "Operation power factor setting value",
    0xC1: "FIT contract type",
    0xC2: "Self-consumption type",
    0xC3: "Capacity approved by equipment",
    0xC4: "Conversion coefficient",
    0xD0: "System interconnection status",
    0xD1: "Output power restraint status",
    0xB0: "Output power controlling schedule",
    0x89: "Fault description",
    0xA0: "Output power control setting 1",
    0xA1: "Output power control setting 2",
    0xA2: "Function to control purchase of excess electricity setting",
    0xB1: "Next access date and time",
    0xB2: "Type for function to control purchase of excess electricity",
    0xB3: "Output power change time setting value",
    0xB4: "Upper limit clip setting value",





    
    # Add more EPCs as needed from Annex 1
}
def parse_property_map(edt):
    if not edt or len(edt) == 0:
        return []
    if len(edt) > 17:
        raise ValueError("Property map EDT too long (max 17 bytes)")
    n = edt[0]
    if len(edt) == n + 1 and n < 16:
        return [b for b in edt[1:1+n]]
    elif len(edt) == 17:
        epcs = []
        for i in range(16):
            byte = edt[i+1]
            for bit in range(8):
                if byte & (1 << bit):
                    epcs.append(0x80 + i*8 + bit)
        return epcs
    else:
        raise ValueError("Invalid property map format or length")

def extract_relevant_response(epc, resp):
    # If error, return error string
    if isinstance(resp, dict) and 'error' in resp:
        return resp['error']
    # Find the property for this EPC
    if isinstance(resp, dict) and 'properties' in resp:
        for prop in resp['properties']:
            if prop['epc'] == epc:
                # For ON/OFF (0x80), show ON/OFF
                if epc == 0x80:
                    if prop['edt'] == b'\x30':
                        return 'ON (0x30)'
                    elif prop['edt'] == b'\x31':
                        return 'OFF (0x31)'
                    else:
                        return f'Unknown ({prop["edt"].hex()})'
                # For other EPCs, show hex value of EDT
                return prop['edt'].hex()
    return 'No data'

def save_report_pdf(report, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, "ECHONET Lite EPC Query Report", ln=True, align='C')
    pdf.ln(5)
    # Table header
    headers = ["EPC", "Description", "Query", "Response"]
    col_widths = [20, 60, 40, 60]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, align='C')
    pdf.ln()
    # Table rows
    for row in report:
        pdf.cell(col_widths[0], 8, str(row['EPC']), border=1)
        pdf.cell(col_widths[1], 8, str(row['Description'])[:40], border=1)
        pdf.cell(col_widths[2], 8, str(row['Query'])[:30], border=1)
        resp = str(row['Response'])
        if len(resp) > 40:
            resp = resp[:37] + '...'
        pdf.cell(col_widths[3], 8, resp, border=1)
        pdf.ln()
    pdf.output(filename)

def main():
    client = EchonetLiteClient('192.168.1.192')
    report = []
    # Step 1: Query 0x9F (Get Property Map)
    client.send_query(0x62, 0x9F)
    resp = client.listen_response()
    edt = None
    if 'properties' in resp:
        for prop in resp['properties']:
            if prop['epc'] == 0x9F:
                edt = prop['edt']
                break
    epc_list = parse_property_map(edt) if edt else []
    # Step 2: For each EPC, send a Get (0x62) query and record response
    for epc in epc_list:
        client.send_query(0x62, epc)
        epc_resp = client.listen_response()
        desc = EPC_DETAILS.get(epc, "Unknown/Reserved")
        relevant = extract_relevant_response(epc, epc_resp)
        report.append({
            'EPC': f"0x{epc:02X}",
            'Description': desc,
            'Query': f"Get (0x62) for EPC 0x{epc:02X}",
            'Response': relevant
        })
        print(".")
        time.sleep(1)
    print(tabulate.tabulate(report, headers='keys'))
    save_report_pdf(report, "epc_report.pdf")
    print("PDF report saved as epc_report.pdf")
    client.close()

if __name__ == '__main__':
    main()
