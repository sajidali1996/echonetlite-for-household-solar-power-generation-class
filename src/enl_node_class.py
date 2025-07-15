"""
EchonetLiteClient: ECHONET Lite UDP Client for Household Solar Power Generation Class

This module provides a Python class to interact with ECHONET Lite-compliant devices, specifically for the household solar power generation class (as per ECHONET Lite specifications).

Features:
- Send and receive ECHONET Lite UDP packets
- Query and set device properties (EPCs) for solar power generation
- Parse and interpret ECHONET Lite responses
- Centralized EPC descriptions for reporting and documentation

Class: EchonetLiteClient
------------------------
Attributes:
    EPC_DETAILS (dict): Mapping of EPC codes to their descriptions.
    ip (str): Target device IP address.
    port (int): UDP port (default: 3610).
    seoj (bytes): Source ECHONET object code.
    deoj (bytes): Destination ECHONET object code.
    sock (socket.socket): UDP socket for communication.
    tid (int): Transaction ID for ECHONET Lite messages.

Methods:
    __init__(ip, port, seoj, deoj): Initialize the client.
    _build_message(esv, epc, edt): Build ECHONET Lite UDP message.
    send_command(esv, epc, edt): Send a command to the device.
    send_query(esv, epc): Send a query to the device.
    parse_response(data): Parse a UDP response from the device.
    listen_response(timeout, parse): Listen for a response from the device.
    get_operation_status(): Get device ON/OFF status.
    set_operation_status(on): Set device ON/OFF status.
    get_installation_location(): Get installation location.
    set_installation_location(location_code): Set installation location.
    get_standard_version_info(): Get standard version info.
    get_fault_status(): Get device fault status.
    get_manufacturer_code(): Get manufacturer code.
    get_instantaneous_power_generation(): Get instantaneous power generation value.
    get_cumulative_power_generation(): Get cumulative power generation value.
    reset_cumulative_power_generation(): Reset cumulative power generation counter.
    get_power_generation_limit_setting(): Get power generation limit setting.
    set_power_generation_limit_setting(value): Set power generation limit.
    get_system_interconnected_type(): Get system interconnection type.
    get_measured_cumulative_amount_of_electric_energy(): Get measured cumulative electric energy.
    _extract_property(resp, epc, label, fmt): Helper to extract and decode a property from response.
    close(): Close the UDP socket.

Usage:
    client = EchonetLiteClient('192.168.1.192')
    status = client.get_operation_status()
    client.close()

This file is designed for automated test generation: all public methods are documented and have clear input/output behavior. EPC codes and their descriptions are centralized for easy reference and reporting.
"""

import socket
from struct import pack, unpack
import threading
import struct


class EchonetLiteClient:
    # Detailed EPC descriptions from user-provided table
    EPC_DETAILS = {
        0x80: "Operating status",
        0x82: "Version information",
        0x83: "Identification number",
        0x88: "Fault status",
        0x8A: "Manufacturer code",
        0x8C: "Product code",
        0x8D: "Production number",
        0x8E: "Production date",
        0x9D: "Status change announcement property map",
        0x9E: "Set property map",
        0x9F: "Get property map",
        0xD3: "Number of self-node instances",
        0xD4: "Number of self-node classes",
        0xD5: "Instance list notification",
        0xD6: "Self-node instance list S",
        0xD7: "Self-node class list S",
    }

    def __init__(self, ip, port=3610, seoj=(0x05, 0xFF, 0x01), deoj=(0x0E, 0xF0, 0x01)):
        """
        Initialize the EchonetLiteClient.

        Args:
            ip (str): Target device IP address.
            port (int, optional): UDP port (default: 3610).
            seoj (tuple, optional): Source ECHONET object code (default: (0x05, 0xFF, 0x01)).
            deoj (tuple, optional): Destination ECHONET object code (default: (0x02, 0x79, 0x01)).
        """
        self.ip = ip
        self.port = port
        self.seoj = pack('>3B', *seoj)
        self.deoj = pack('>3B', *deoj)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        self.tid = 0

    def _build_message(self, esv, epc, edt=b''):
        """
        Build an ECHONET Lite UDP message.

        Args:
            esv (int): ECHONET Service code.
            epc (int): ECHONET Property code.
            edt (bytes, optional): Property data (default: empty).
        Returns:
            bytes: Encoded UDP message.
        """
        EHD1 = 0x10
        EHD2 = 0x81
        TID = pack('>H', self.tid)
        OPC = 1
        PDC = len(edt)
        message = (
            pack('>B', EHD1) +
            pack('>B', EHD2) +
            TID +
            self.seoj +
            self.deoj +
            pack('>B', esv) +
            pack('>B', OPC) +
            pack('>B', epc) +
            pack('>B', PDC) +
            edt
        )
        self.tid = (self.tid + 1) % 0xFFFF
        return message

    def send_command(self, esv, epc, edt=b'\x00'):
        """
        Send a command (write) to the device.

        Args:
            esv (int): ECHONET Service code.
            epc (int): ECHONET Property code.
            edt (bytes, optional): Property data (default: b'\x00').
        """
        msg = self._build_message(esv, epc, edt)
        self.sock.sendto(msg, (self.ip, self.port))

    def send_query(self, esv, epc):
        """
        Send a query (read) to the device.

        Args:
            esv (int): ECHONET Service code.
            epc (int): ECHONET Property code.
        """
        msg = self._build_message(esv, epc,edt=b'')
        self.sock.sendto(msg, (self.ip, self.port))

    def parse_response(self, data):
        """
        Parse ECHONET Lite response according to the standard (pv_aif_ver1.20.pdf).

        Args:
            data (bytes): UDP response data.
        Returns:
            dict: Parsed response with header, TID, SEOJ, DEOJ, ESV, OPC, properties, and error info if any.
        """
        try:
            if len(data) < 14:
                return {'error': 'Malformed packet: too short'}
            ehd1, ehd2 = unpack('>BB', data[0:2])
            tid = unpack('>H', data[2:4])[0]
            seoj = tuple(data[4:7])
            deoj = tuple(data[7:10])
            esv = data[10]
            opc = data[11]
            props = []
            idx = 12
            for _ in range(opc):
                if idx + 2 > len(data):
                    return {'error': 'Malformed property block'}
                epc = data[idx]
                pdc = data[idx+1]
                idx += 2
                if idx + pdc > len(data):
                    return {'error': 'Malformed property data'}
                edt = data[idx:idx+pdc]
                props.append({'epc': epc, 'pdc': pdc, 'edt': edt})
                idx += pdc
            # ESV error codes: 0x50, 0x51, 0x52
            if esv in (0x50, 0x51, 0x52):
                return {
                    'header': (ehd1, ehd2),
                    'tid': tid,
                    'seoj': seoj,
                    'deoj': deoj,
                    'esv': esv,
                    'opc': opc,
                    'properties': props,
                    'error': f'ESV error code: 0x{esv:02X}'
                }
            return {
                'header': (ehd1, ehd2),
                'tid': tid,
                'seoj': seoj,
                'deoj': deoj,
                'esv': esv,
                'opc': opc,
                'properties': props
            }
        except Exception as e:
            return {'error': f'Exception during parsing: {e}'}

    def listen_response(self, timeout=2, parse=True):
        """
        Listen for a UDP response from the device.

        Args:
            timeout (int, optional): Timeout in seconds (default: 2).
            parse (bool, optional): Whether to parse the response (default: True).
        Returns:
            dict or bytes: Parsed response or raw data.
        """
        self.sock.settimeout(timeout)
        try:
            data, addr = self.sock.recvfrom(1024)
            if parse:
                return self.parse_response(data)
            return data
        except socket.timeout:
            return {'error': 'Timeout waiting for response'}
        except Exception as e:
            return {'error': f'Exception: {e}'}

    # --- Device Object Super Class Requirements (Section 2-1) ---
    def get_operation_status(self):
        """
        Get operation status (EPC: 0x80, ESV: 0x62).

        Returns:
            dict: {'Operation Status': 'ON'/'OFF'/hex} or error info.
        """
        self.send_query(0x62, 0x80)
        resp = self.listen_response()
        # Interpret ON/OFF according to ECHONET Lite spec: 0x30 = ON, 0x31 = OFF
        result = self._extract_property(resp, 0x80, 'Operation Status')
        if 'Operation Status' in result:
            val = result['Operation Status']
            if val in (b'0', b'\x30') or val == b'\x30':
                result['Operation Status'] = 'ON'
            elif val in (b'1', b'\x31') or val == b'\x31':
                result['Operation Status'] = 'OFF'
            else:
                # Show hex value if unknown
                result['Operation Status'] = f'Unknown (0x{val.hex()})'
        return result

    def set_operation_status(self, on=True):
        """
        Set operation status (EPC: 0x80, ESV: 0x60).

        Args:
            on (bool): True for ON, False for OFF.
        Returns:
            dict: Result or error info.
        """
        edt = b'\x30' if on else b'\x31'
        self.send_command(0x60, 0x80, edt)
        resp = self.listen_response()
        return self._extract_property(resp, 0x80, 'Operation Status')

    def get_installation_location(self):
        """
        Get installation location (EPC: 0x81, ESV: 0x62).

        Returns:
            dict: Installation location or error info.
        """
        self.send_query(0x62, 0x81)
        resp = self.listen_response()
        return self._extract_property(resp, 0x81, 'Installation Location')

    def set_installation_location(self, location_code):
        """
        Set installation location (EPC: 0x81, ESV: 0x60).

        Args:
            location_code (int): Location code as per ECHONET Lite spec.
        Returns:
            dict: Result or error info.
        """
        self.send_command(0x60, 0x81, pack('>B', location_code))
        resp = self.listen_response()
        return self._extract_property(resp, 0x81, 'Installation Location')

    def get_standard_version_info(self):
        """
        Get standard version info (EPC: 0x82, ESV: 0x62).

        Returns:
            dict: Standard version info or error info.
        """
        self.send_query(0x62, 0x82)
        resp = self.listen_response()
        return self._extract_property(resp, 0x82, 'Standard Version Info')

    def get_fault_status(self):
        """
        Get fault status (EPC: 0x88, ESV: 0x62).

        Returns:
            dict: Fault status or error info.
        """
        self.send_query(0x62, 0x88)
        resp = self.listen_response()
        return self._extract_property(resp, 0x88, 'Fault Status')

    def get_manufacturer_code(self):
        """
        Get manufacturer code (EPC: 0x8A, ESV: 0x62).

        Returns:
            dict: Manufacturer code or error info.
        """
        self.send_query(0x62, 0x8A)
        resp = self.listen_response()
        return self._extract_property(resp, 0x8A, 'Manufacturer Code')

    # --- Household Solar Power Generation Class (Section 3-228) ---
    def get_instantaneous_power_generation(self):
        """
        Get instantaneous power generation (EPC: 0xE7, ESV: 0x62).

        Returns:
            dict: Instantaneous power generation value or error info.
        """
        self.send_query(0x62, 0xE7)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE7, 'Instantaneous Power Generation', fmt='>i')

    def get_cumulative_power_generation(self):
        """
        Get cumulative power generation (EPC: 0xE0, ESV: 0x62).

        Returns:
            dict: Cumulative power generation value or error info.
        """
        self.send_query(0x62, 0xE0)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE0, 'Cumulative Power Generation', fmt='>I')

    def reset_cumulative_power_generation(self):
        """
        Reset cumulative power generation (EPC: 0xE1, ESV: 0x61).

        Returns:
            dict: Result or error info.
        """
        self.send_command(0x61, 0xE1)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE1, 'Reset Cumulative Power Generation')

    def get_power_generation_limit_setting(self):
        """
        Get power generation limit setting (EPC: 0xE2, ESV: 0x62).

        Returns:
            dict: Power generation limit or error info.
        """
        self.send_query(0x62, 0xE2)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE2, 'Power Generation Limit Setting', fmt='>H')

    def set_power_generation_limit_setting(self, value):
        """
        Set power generation limit setting (EPC: 0xE2, ESV: 0x60).

        Args:
            value (int): Power generation limit value.
        Returns:
            dict: Result or error info.
        """
        self.send_command(0x60, 0xE2, pack('>H', value))
        resp = self.listen_response()
        return self._extract_property(resp, 0xE2, 'Power Generation Limit Setting', fmt='>H')

    def get_system_interconnected_type(self):
        """
        Get system interconnected type (EPC: 0xE3, ESV: 0x62).

        Returns:
            dict: System interconnected type or error info.
        """
        self.send_query(0x62, 0xE3)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE3, 'System Interconnected Type')

    def get_measured_cumulative_amount_of_electric_energy(self):
        """
        Get measured cumulative amount of electric energy (EPC: 0xE4, ESV: 0x62).

        Returns:
            dict: Measured cumulative electric energy or error info.
        """
        self.send_query(0x62, 0xE4)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE4, 'Measured Cumulative Electric Energy', fmt='>I')

    def _extract_property(self, resp, epc, label, fmt=None):
        """
        Helper to extract and decode a property from parsed response.

        Args:
            resp (dict): Parsed response from parse_response().
            epc (int): EPC code to extract.
            label (str): Label for the property.
            fmt (str, optional): struct format string for unpacking EDT.
        Returns:
            dict: {label: value} or error info.
        """
        if 'error' in resp:
            return {'error': resp['error']}
        for prop in resp.get('properties', []):
            if prop['epc'] == epc:
                if fmt and len(prop['edt']) == struct.calcsize(fmt):
                    try:
                        value = unpack(fmt, prop['edt'])[0]
                        return {label: value}
                    except Exception as e:
                        return {'error': f'Failed to unpack {label}: {e}'}
                return {label: prop['edt']}
        return {'error': f'{label} (EPC: 0x{epc:02X}) not found in response'}

    def close(self):
        """
        Close the UDP socket.
        """
        self.sock.close()

if __name__ == "__main__":
    # Example usage
    client = EchonetLiteClient('192.168.1.192')
    print(client.get_operation_status())
    client.close()
                               
# Example usage:
# client = EchonetLiteClient('192.168.1.192')
# print(client.get_operation_status())
# client.close()