"""
batt_epc_report_query_csv.py: Query ECHONET Lite Battery EPCs and Generate CSV Report

This script queries a set of ECHONET Lite battery-related properties (EPCs), collects their values and descriptions, and generates a CSV report for documentation and analysis.

Features:
---------
- Queries a predefined list of battery EPCs from an ECHONET Lite device
- Uses EchonetLiteClient for communication and EPC description lookup
- Handles missing or unresponsive EPCs gracefully
- Outputs a CSV report with EPC, description, and value
- Prints a tabulated summary to the console

Usage:
------
    python batt_epc_report_query_csv.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from enl_batt_class import EchonetLiteClient
import tabulate
import datetime
import csv

# List of supported battery EPCs (from Get Property Map 0x9F Decoded Table)
BATTERY_EPCS = [
    0xD0, 0xA0, 0x80, 0xD1, 0xC1, 0xA1, 0x81, 0xE2, 0xD2, 0xC2, 0xA2, 0x82, 0xD3, 0xA3, 0x83, 0xE4, 0xD4, 0xA4, 0xE5, 0xD5, 0xA5, 0xE6, 0xD6, 0x97, 0xD8, 0xC8, 0xA8, 0x98, 0x88, 0xC9, 0xA9, 0x89, 0xDA, 0xAA, 0x8A, 0xEB, 0xDB, 0xAB, 0xEC, 0x8C, 0x9D, 0x9E, 0xCF, 0x9F
]

def describe_epc(epc, edt):
    """
    Return a dictionary with EPC hex, description, and value (or 'No response').
    """
    desc = EchonetLiteClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
    if edt is None:
        return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': 'No response'}
    value = edt.hex().upper() if isinstance(edt, (bytes, bytearray)) else str(edt)
    return {'EPC': f'0x{epc:02X}', 'Description': desc, 'Value': value}

def get_ip_from_credentials(filename='credentials.txt'):
    """
    Read the device IP address from a credentials file.
    """
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('IP='):
                return line.strip().split('=', 1)[1]
    raise ValueError('IP not found in credentials file')

def save_report_as_csv(report, filename):
    """
    Save the EPC report as a CSV file.
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['EPC', 'Description', 'Value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in report:
            writer.writerow(row)

def main():
    """
    Main entry point: queries battery EPCs, prints a table, and saves a CSV report.
    """
    ip = get_ip_from_credentials()
    client = EchonetLiteClient(ip)
    report = []
    for epc in BATTERY_EPCS:
        client.send_query(0x62, epc)
        resp = client.listen_response(timeout=2)
        edt = None
        if 'properties' in resp:
            for prop in resp['properties']:
                if prop['epc'] == epc:
                    edt = prop['edt']
                    break
        report.append(describe_epc(epc, edt))
    print(tabulate.tabulate(report, headers='keys'))
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'batt_epc_report_{now}.csv'
    save_report_as_csv(report, csv_filename)
    print(f"CSV report saved as {csv_filename}")
    client.close()

if __name__ == '__main__':
    main()
