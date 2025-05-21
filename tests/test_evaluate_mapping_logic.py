"""
Unit tests for property map parsing and description logic (EvaluateMapping.py)

These tests cover the static logic for property map parsing and EPC description, without requiring a live ECHONET Lite server/device.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from src.EvaluateMapping import parse_property_map, describe_epc_list

class TestPropertyMapParsing(unittest.TestCase):
    def test_parse_property_map_format1(self):
        # Format 1: [n, EPC1, EPC2, ...]
        edt = bytes([2, 0x80, 0x81])
        result = parse_property_map(edt, is_9f=False)
        self.assertEqual(result, [0x80, 0x81])

    def test_parse_property_map_format2(self):
        # Format 2: [n, 16 bytes bitmap] (simulate 0x80 and 0x81 set)
        # To set 0x80 and 0x81, set bits 0 and 1 (LSB) in the first byte
        edt = bytes([0x10] + [0b00000011] + [0]*15)  # 0x80 (bit 0), 0x81 (bit 1) set in first byte
        result = parse_property_map(edt, is_9f=False)
        self.assertIn(0x80, result)
        self.assertIn(0x81, result)

    def test_parse_property_map_invalid(self):
        # Invalid: too long
        with self.assertRaises(ValueError):
            parse_property_map(bytes([18] + [0]*18), is_9f=False)

    def test_describe_epc_list(self):
        # Should return a list of dicts with EPC and Description
        epc_list = [0x80, 0x81]
        table = describe_epc_list(epc_list)
        self.assertEqual(table[0]['EPC'], '0x80')  # Accept lower-case x
        self.assertIn('Description', table[0])

if __name__ == "__main__":
    unittest.main()
