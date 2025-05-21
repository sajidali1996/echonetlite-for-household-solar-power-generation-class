"""
Unit tests for enl_class.py (ECHONET Lite client logic)

These tests cover the internal logic and static/class data of EchonetLiteClient without requiring a live ECHONET Lite server/device.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from src.enl_class import EchonetLiteClient

class TestEchonetLiteClientStatic(unittest.TestCase):
    def test_epc_details_contains_known_epcs(self):
        # Check that some known EPCs are present and have non-empty descriptions
        for epc in [0x80, 0x81, 0x82, 0xE7, 0xE0]:
            self.assertIn(epc, EchonetLiteClient.EPC_DETAILS)
            self.assertIsInstance(EchonetLiteClient.EPC_DETAILS[epc], str)
            self.assertTrue(len(EchonetLiteClient.EPC_DETAILS[epc]) > 0)

    def test_epc_details_no_duplicates(self):
        # EPC keys should be unique
        keys = list(EchonetLiteClient.EPC_DETAILS.keys())
        self.assertEqual(len(keys), len(set(keys)))

    def test_epc_details_type(self):
        # EPC_DETAILS should be a dict of int to str
        self.assertIsInstance(EchonetLiteClient.EPC_DETAILS, dict)
        for k, v in EchonetLiteClient.EPC_DETAILS.items():
            self.assertIsInstance(k, int)
            self.assertIsInstance(v, str)

if __name__ == "__main__":
    unittest.main()
