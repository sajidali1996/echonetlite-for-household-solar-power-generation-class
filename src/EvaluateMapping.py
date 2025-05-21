"""
EvaluateMapping: ECHONET Lite Property Map Evaluation and PDF Reporting

This script queries ECHONET Lite devices for their property maps (EPC 0x9E and 0x9F), decodes the supported property lists, and generates a professional PDF report summarizing the mapping and descriptions.

Features:
- Query ECHONET Lite devices for Set Property Map (0x9E) and Get Property Map (0x9F)
- Decode property map responses (both list and bitmap formats)
- Cross-reference EPCs with descriptions from EchonetLiteClient.EPC_DETAILS
- Generate a PDF report with tables for both property maps
- Utility functions for parsing, description, and credential management

Functions:
----------
- get_active_values(nth_byte, bytevalue):
    Given a byte index and value, returns a list of EPC hex strings for active bits (for bitmap property maps).
- parse_property_map(edt, is_9f=False):
    Parses the property map EDT (Format 1: list, Format 2: bitmap) and returns a list of EPC integers.
- describe_epc_list(epc_list):
    Returns a table of EPC hex codes and their descriptions.
- get_ip_from_credentials(filename):
    Reads the device IP from a credentials file.
- save_mapping_pdf_report(...):
    Generates a PDF report summarizing the property maps and their decoded tables.
- main():
    Orchestrates the query, parsing, and report generation process.

Usage:
------
    python EvaluateMapping.py

This script is designed for automated testing and reporting. All functions are documented for maintainability and extensibility.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from enl_class import EchonetLiteClient
import datetime
from fpdf import FPDF

def get_active_values(nth_byte, bytevalue):
    """
    Given a byte index (nth_byte) and a byte value, return a list of EPC hex strings for active bits.
    Used for decoding bitmap property maps (Format 2) in ECHONET Lite.

    Args:
        nth_byte (int): Index of the byte (0-15).
        bytevalue (int): Value of the byte (0-255).
    Returns:
        list of str: List of EPC hex strings (e.g., ['80', '81', ...])
    """
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
    Handles both Format 1 (list of EPCs) and Format 2 (bitmap).

    Args:
        edt (bytes or list of int): Property map EDT.
        is_9f (bool): True if parsing 0x9F (Get Property Map), uses get_active_values.
    Returns:
        list of int: List of EPC codes supported.
    Raises:
        ValueError: If property map format or length is invalid.
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
    """
    Given a list of EPC codes, return a table of EPC hex codes and their descriptions.

    Args:
        epc_list (list of int): List of EPC codes.
    Returns:
        list of dict: Each dict has 'EPC' and 'Description'.
    """
    table = []
    for epc in epc_list:
        # epc_list now contains integers, not hex strings
        desc = EchonetLiteClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
        table.append({'EPC': f'0x{epc:02X}', 'Description': desc})
    return table

def get_ip_from_credentials(filename='credentials.txt'):
    """
    Read the device IP address from a credentials file.

    Args:
        filename (str): Path to credentials file (default: 'credentials.txt').
    Returns:
        str: IP address.
    Raises:
        ValueError: If IP is not found in the file.
    """
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('IP='):
                return line.strip().split('=', 1)[1]
    raise ValueError('IP not found in credentials file')

def save_mapping_pdf_report(n9e_table, n9f_table, n9e_epc, n9e_resp, n9f_epc, n9f_resp, filename):
    """
    Generate a PDF report summarizing the Set Property Map (0x9E) and Get Property Map (0x9F).

    Args:
        n9e_table (list of dict): Decoded 0x9E property map table.
        n9f_table (list of dict): Decoded 0x9F property map table.
        n9e_epc (int): EPC code for 0x9E.
        n9e_resp (str): Raw response for 0x9E.
        n9f_epc (int): EPC code for 0x9F.
        n9f_resp (str): Raw response for 0x9F.
        filename (str): Output PDF filename.
    """
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
    """
    Main entry point: queries the device, decodes property maps, and generates a PDF report.
    """
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