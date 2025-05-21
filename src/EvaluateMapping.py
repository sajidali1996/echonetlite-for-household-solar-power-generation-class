import tabulate
from enl_class import EchonetLiteClient
import datetime
from fpdf import FPDF
#fix
def get_active_values(nth_byte, bytevalue):
    table = {
        (row, bit): (0x80 | bit << 4 | row)  # auto generate if pattern holds
        for row in range(16)
        for bit in reversed(range(8))
    }
    # Overriding specific mismatches from the table you provided (e.g., (13,6): 0xED instead of 0xED)
    table[(13, 6)] = 0xED  # fix for typo

    # Convert the bytevalue to 8-bit binary string
    binary_str = f"{bytevalue:08b}"

    # From MSB to LSB (bit 7 to bit 0), get values for bits that are '1'
    result = []
    for i, bit in enumerate(binary_str):
        if bit == '1':
            # bit index is 7 - i (MSB is at index 0)
            result.append(table.get((nth_byte, 7 - i)))
    #print("DEBUG :",    [hex(num)[2:].zfill(2) for num in result])
    return  [hex(num)[2:].zfill(2) for num in result]

def parse_property_map(edt, is_9f=False):
    """
    Parse property map (EDT) for ECHONET Lite (EPC 0x9F, 0x9E, etc.)
    For 0x9F, use get_active_values for each byte in the bitmap.
    For 0x9E, use standard logic.
    Returns a list of EPC integers.
    """
    #print the length of edt
    #print(f"parse_property_map: length of edt={len(edt)}")
    if not edt or len(edt) == 0:
        return []
    if len(edt) > 17:
        raise ValueError("Property map EDT too long (max 17 bytes)")
    n = edt[0]
    if len(edt) == n + 1 and n < 16:
        # Format 1: list of EPCs
        return [b for b in edt[1:1+n]]
    elif len(edt) == 17:
        if is_9f:
            # Use get_active_values for each byte in the bitmap
            epc_hex = []
            for i in range(16):
                epc_hex.extend(get_active_values(i, edt[i+1]))
            # Convert hex strings to integers
            return [int(e, 16) for e in epc_hex]
        else:
            # Standard Format 2: bitmap (next 16 bytes, LSB first)
            epcs = []
            for i in range(16):
                byte = edt[i+1]
                for bit in range(8):
                    if byte & (1 << bit):
                        epcs.append(0x80 + i*8 + bit)
            return epcs
    else:
        raise ValueError("Invalid property map format or length")

def describe_epc_list(epc_list):
    table = []
    for epc in epc_list:
        # epc_list now contains integers, not hex strings
        desc = EchonetLiteClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
        table.append({'EPC': f'0x{epc:02X}', 'Description': desc})
    return table

def get_ip_from_credentials(filename='credentials.txt'):
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('IP='):
                return line.strip().split('=', 1)[1]
    raise ValueError('IP not found in credentials file')

def save_mapping_pdf_report(n9e_table, n9f_table, n9e_epc, n9e_resp, n9f_epc, n9f_resp, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 12, txt="Echonet lite mapping evaluation", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(8)
    # Show EPC and response for 0x9E
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, 'Set Property Map (0x9E) Query/Response:', ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, f"Query EPC: 0x{n9e_epc:02X}\nResponse: {n9e_resp}")
    pdf.ln(2)
    # Table for 0x9E
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Set Property Map (0x9E) Decoded Table', ln=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, 'EPC', 1)
    pdf.cell(120, 10, 'Description', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in n9e_table:
        epc = row['EPC']
        desc = row['Description']
        desc_lines = []
        while len(desc) > 60:
            desc_lines.append(desc[:60])
            desc = desc[60:]
        desc_lines.append(desc)
        max_lines = len(desc_lines)
        for i in range(max_lines):
            pdf.cell(40, 10, epc if i == 0 else '', 1)
            pdf.cell(120, 10, desc_lines[i], 1)
            pdf.ln()
    pdf.ln(5)
    # Show EPC and response for 0x9F
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, 'Get Property Map (0x9F) Query/Response:', ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, f"Query EPC: 0x{n9f_epc:02X}\nResponse: {n9f_resp}")
    pdf.ln(2)
    # Table for 0x9F
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Get Property Map (0x9F) Decoded Table', ln=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, 'EPC', 1)
    pdf.cell(120, 10, 'Description', 1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for row in n9f_table:
        epc = row['EPC']
        desc = row['Description']
        desc_lines = []
        while len(desc) > 60:
            desc_lines.append(desc[:60])
            desc = desc[60:]
        desc_lines.append(desc)
        max_lines = len(desc_lines)
        for i in range(max_lines):
            pdf.cell(40, 10, epc if i == 0 else '', 1)
            pdf.cell(120, 10, desc_lines[i], 1)
            pdf.ln()
    pdf.output(filename)

def main():
    ip = get_ip_from_credentials()
    client = EchonetLiteClient(ip)
    property_maps = [
        (0x9E, 'Set Property Map'),
        (0x9F, 'Get Property Map'),
    ]
    n9e_table = []
    n9f_table = []
    n9e_epc = 0x9E
    n9f_epc = 0x9F
    n9e_resp = ''
    n9f_resp = ''
    for epc, label in property_maps:
        client.send_query(0x62, epc)
        resp = client.listen_response(parse=False)
        resp_hex = resp.hex().upper() if isinstance(resp, (bytes, bytearray)) else ''
        edt = None
        parsed = client.parse_response(resp) if isinstance(resp, (bytes, bytearray)) else resp
        if 'properties' in parsed:
            for prop in parsed['properties']:
                if prop['epc'] == epc:
                    edt = prop['edt']
                    break
        if epc == 0x9F:
            n9f_resp = resp_hex
            epc_list = parse_property_map(edt, is_9f=True) if edt else []
            n9f_table = describe_epc_list(epc_list)
        else:
            n9e_resp = resp_hex
            epc_list = parse_property_map(edt, is_9f=False) if edt else []
            n9e_table = describe_epc_list(epc_list)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f'mapping_evaluation_{now}.pdf'
    save_mapping_pdf_report(n9e_table, n9f_table, n9e_epc, n9e_resp, n9f_epc, n9f_resp, pdf_filename)
    print(f"PDF report saved as {pdf_filename}")
    client.close()

if __name__ == '__main__':
    main()