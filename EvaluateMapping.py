import tabulate
from enl_class import EchonetLiteClient
# Add this mapping based on Annex 1 and your device class
EPC_DESCRIPTIONS = {
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
        desc = EPC_DESCRIPTIONS.get(epc, "Unknown/Reserved")
        table.append({'EPC': f'0x{epc:02X}', 'Description': desc})
    return table

def main():
    client = EchonetLiteClient('192.168.1.192')
    property_maps = [
        (0x9E, 'Set Property Map'),
        (0x9F, 'Get Property Map'),
    ]
    for epc, label in property_maps:
        client.send_query(0x62, epc)
        resp = client.listen_response()
        print(resp)
        edt = None
        if 'properties' in resp:
            for prop in resp['properties']:
                if prop['epc'] == epc:
                    edt = prop['edt']
                    break
        if epc == 0x9F:
            epc_list = parse_property_map(edt, is_9f=True) if edt else []
        else:
            epc_list = parse_property_map(edt, is_9f=False) if edt else []
        if epc_list:
            print("Decoded EPCs:", " ".join(f"{epc:02X}" for epc in epc_list))
        desc_table = describe_epc_list(epc_list)
        print(f"\n{label} (EPC 0x{epc:02X}):")
        print(tabulate.tabulate(desc_table, headers='keys'))
    client.close()

if __name__ == '__main__':
    main()