"""
node_epc_report_query_csv.py: Query ECHONET Lite Node Profile EPCs and Generate CSV Report

This script queries a set of ECHONET Lite node profile properties (EPCs), collects their values and descriptions, and generates a CSV report for documentation and analysis.

Features:
---------
- Queries a predefined list of node profile EPCs from an ECHONET Lite device
- Uses EchonetLiteNodeClient for communication and EPC description lookup
- Handles missing or unresponsive EPCs gracefully
- Outputs a CSV report with EPC, description, and value
- Prints a tabulated summary to the console

Usage:
------
    python node_epc_report_query_csv.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from enl_node_class import EchonetLiteClient as EchonetLiteNodeClient
import tabulate
import datetime
import csv

def describe_epc(epc, edt):
    """
    Return a dictionary with EPC hex, description, and value (or 'No response').
    """
    desc = EchonetLiteNodeClient.EPC_DETAILS.get(epc, "Unknown/Reserved")
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
    Main entry point: queries node profile EPCs, prints a table, and saves a CSV report.
    """
    ip = get_ip_from_credentials()
    client = EchonetLiteNodeClient(ip)
    report = []
    for epc in EchonetLiteNodeClient.EPC_DETAILS.keys():
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
    csv_filename = f'node_epc_report_{now}.csv'
    save_report_as_csv(report, csv_filename)
    print(f"CSV report saved as {csv_filename}")
    client.close()

if __name__ == '__main__':
    main()
