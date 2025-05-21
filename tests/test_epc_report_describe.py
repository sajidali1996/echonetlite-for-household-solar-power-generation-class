"""
Unit tests for CSV and PDF report logic (epc_report_query_csv.py, epc_report_query_pdf.py)

These tests cover the static logic for EPC description and report row formatting, without requiring a live ECHONET Lite server/device.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from src.epc_report_query_csv import describe_epc as describe_epc_csv
from src.epc_report_query_pdf import describe_epc as describe_epc_pdf

class TestEpcReportDescribeEpc(unittest.TestCase):
    def test_describe_epc_csv(self):
        # Should return a dict with EPC, Description, Value
        row = describe_epc_csv(0x80, b'\x30')
        self.assertEqual(row['EPC'], '0x80')  # Accept lower-case x
        self.assertIn('Description', row)
        self.assertEqual(row['Value'], '30')

    def test_describe_epc_pdf(self):
        # Should return a dict with EPC, Description, Value
        row = describe_epc_pdf(0x81, b'\x01')
        self.assertEqual(row['EPC'], '0x81')  # Accept lower-case x
        self.assertIn('Description', row)
        self.assertEqual(row['Value'], '01')

    def test_describe_epc_none(self):
        # Should handle None EDT
        row = describe_epc_csv(0x82, None)
        self.assertEqual(row['Value'], 'No response')

if __name__ == "__main__":
    unittest.main()
