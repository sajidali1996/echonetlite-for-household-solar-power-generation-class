"""
epc_report_query_csv.py: Query ECHONET Lite EPCs and Generate CSV Report

This script queries a set of ECHONET Lite device properties (EPCs), collects their values and descriptions, and generates a CSV report for documentation and analysis.

Features:
---------
- Queries a predefined list of EPCs from an ECHONET Lite device
- Uses EchonetLiteClient for communication and EPC description lookup
- Handles missing or unresponsive EPCs gracefully
- Outputs a CSV report with EPC, description, and value
- Prints a tabulated summary to the console

Functions:
----------
- describe_epc(epc, edt):
    Returns a dictionary with EPC hex, description, and value (or 'No response').
- get_ip_from_credentials(filename):
    Reads the device IP from a credentials file.
- save_report_as_csv(report, filename):
    Saves the report (list of dicts) as a CSV file.
- main():
    Orchestrates the query, reporting, and CSV export process.

Usage:
------
    python epc_report_query_csv.py

This script is designed for automated reporting and easy integration with test frameworks. All functions are documented for maintainability and extensibility.
"""

import tabulate
from enl_class import EchonetLiteClient
import datetime
import csv

# List of EPCs to query (as integers)
EPCS = [
    0x80, 0x81, 0x82, 0x83, 0x88, 0x89, 0x8A, 0x8C, 0x97, 0x98, 0x9D, 0x9E, 0xA0, 0xA1, 0xA2, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xD0, 0xD1, 0xE0, 0xE1, 0xE3, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9
]

def describe_epc(epc, edt):
    """
    Return a dictionary with EPC hex, description, and value (or 'No response').

    Args:
        epc (int): EPC code.
        edt (bytes or None): Property value.
    Returns:
        dict: {'EPC', 'Description', 'Value'}
    """
    desc = EchonetLiteClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
    if edt is None:
        return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': 'No response'}
    value = edt.hex().upper() if isinstance(edt, (bytes, bytearray)) else str(edt)
    return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': value}

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

def save_report_as_csv(report, filename):
    """
    Save the EPC report as a CSV file.

    Args:
        report (list of dict): List of EPC report rows.
        filename (str): Output CSV filename.
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['EPC', 'Description', 'Value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in report:
            writer.writerow(row)

def main():
    """
    Main entry point: queries EPCs, prints a table, and saves a CSV report.
    """
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
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'epc_report_{now}.csv'
    save_report_as_csv(report, csv_filename)
    print(f"CSV report saved as {csv_filename}")
    client.close()

if __name__ == '__main__':
    main()
