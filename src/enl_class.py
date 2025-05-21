import socket
from struct import pack, unpack
import threading
import struct



class EchonetLiteClient:
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

    def __init__(self, ip, port=3610, seoj=(0x05, 0xFF, 0x01), deoj=(0x02, 0x79, 0x01)):
        self.ip = ip
        self.port = port
        self.seoj = pack('>3B', *seoj)
        self.deoj = pack('>3B', *deoj)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        self.tid = 0

    def _build_message(self, esv, epc, edt=b''):
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
        msg = self._build_message(esv, epc, edt)
        self.sock.sendto(msg, (self.ip, self.port))

    def send_query(self, esv, epc):
        msg = self._build_message(esv, epc,edt=b'')
        self.sock.sendto(msg, (self.ip, self.port))

    def parse_response(self, data):
        """
        Parse ECHONET Lite response according to the standard (pv_aif_ver1.20.pdf).
        Returns a dict with header, TID, SEOJ, DEOJ, ESV, OPC, properties, and error info if any.
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
        """Get operation status (EPC: 0x80, ESV: 0x62). Returns dict with status or error."""
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
        """Set operation status (EPC: 0x80, ESV: 0x60). Returns dict with result or error."""
        edt = b'\x30' if on else b'\x31'
        self.send_command(0x60, 0x80, edt)
        resp = self.listen_response()
        return self._extract_property(resp, 0x80, 'Operation Status')

    def get_installation_location(self):
        """Get installation location (EPC: 0x81, ESV: 0x62)."""
        self.send_query(0x62, 0x81)
        resp = self.listen_response()
        return self._extract_property(resp, 0x81, 'Installation Location')

    def set_installation_location(self, location_code):
        """Set installation location (EPC: 0x81, ESV: 0x60)."""
        self.send_command(0x60, 0x81, pack('>B', location_code))
        resp = self.listen_response()
        return self._extract_property(resp, 0x81, 'Installation Location')

    def get_standard_version_info(self):
        """Get standard version info (EPC: 0x82, ESV: 0x62)."""
        self.send_query(0x62, 0x82)
        resp = self.listen_response()
        return self._extract_property(resp, 0x82, 'Standard Version Info')

    def get_fault_status(self):
        """Get fault status (EPC: 0x88, ESV: 0x62)."""
        self.send_query(0x62, 0x88)
        resp = self.listen_response()
        return self._extract_property(resp, 0x88, 'Fault Status')

    def get_manufacturer_code(self):
        """Get manufacturer code (EPC: 0x8A, ESV: 0x62)."""
        self.send_query(0x62, 0x8A)
        resp = self.listen_response()
        return self._extract_property(resp, 0x8A, 'Manufacturer Code')

    # --- Household Solar Power Generation Class (Section 3-228) ---
    def get_instantaneous_power_generation(self):
        """Get instantaneous power generation (EPC: 0xE7, ESV: 0x62)."""
        self.send_query(0x62, 0xE7)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE7, 'Instantaneous Power Generation', fmt='>i')

    def get_cumulative_power_generation(self):
        """Get cumulative power generation (EPC: 0xE0, ESV: 0x62)."""
        self.send_query(0x62, 0xE0)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE0, 'Cumulative Power Generation', fmt='>I')

    def reset_cumulative_power_generation(self):
        """Reset cumulative power generation (EPC: 0xE1, ESV: 0x61)."""
        self.send_command(0x61, 0xE1)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE1, 'Reset Cumulative Power Generation')

    def get_power_generation_limit_setting(self):
        """Get power generation limit setting (EPC: 0xE2, ESV: 0x62)."""
        self.send_query(0x62, 0xE2)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE2, 'Power Generation Limit Setting', fmt='>H')

    def set_power_generation_limit_setting(self, value):
        """Set power generation limit setting (EPC: 0xE2, ESV: 0x60)."""
        self.send_command(0x60, 0xE2, pack('>H', value))
        resp = self.listen_response()
        return self._extract_property(resp, 0xE2, 'Power Generation Limit Setting', fmt='>H')

    def get_system_interconnected_type(self):
        """Get system interconnected type (EPC: 0xE3, ESV: 0x62)."""
        self.send_query(0x62, 0xE3)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE3, 'System Interconnected Type')

    def get_measured_cumulative_amount_of_electric_energy(self):
        """Get measured cumulative amount of electric energy (EPC: 0xE4, ESV: 0x62)."""
        self.send_query(0x62, 0xE4)
        resp = self.listen_response()
        return self._extract_property(resp, 0xE4, 'Measured Cumulative Electric Energy', fmt='>I')

    def _extract_property(self, resp, epc, label, fmt=None):
        """
        Helper to extract and decode a property from parsed response.
        If fmt is given, unpacks EDT accordingly.
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