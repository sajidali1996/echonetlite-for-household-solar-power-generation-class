"""
Monitor all ECHONET Lite UDP packets on port 3610 across the local network.
Logs and matches requests/responses by TID, DEOJ/SEOJ, and ESV pairings.
Outputs to a log file with timestamp, IPs, TID, ESV, match status, and decoded message.
"""
import socket
import struct
import threading
import time
from datetime import datetime

# ECHONET Lite ESV codes
REQUEST_ESV = {0x60, 0x61, 0x62}
RESPONSE_ESV = {0x71, 0x72, 0x73}

# ESV pairing for matching
ESV_PAIR = {
    0x60: 0x71,  # SetI -> Set_Res
    0x61: 0x72,  # SetC -> SetC_SNA
    0x62: 0x72,  # Get -> Get_Res
}

LOG_FILE = "enl_udp_monitor.log"

class ENLPacket:
    def __init__(self, data, addr, direction):
        self.raw = data
        self.addr = addr
        self.direction = direction  # 'in' or 'out'
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.decode()

    def decode(self):
        try:
            if len(self.raw) < 14:
                self.valid = False
                return
            self.ehd1, self.ehd2 = struct.unpack('>BB', self.raw[0:2])
            self.tid = struct.unpack('>H', self.raw[2:4])[0]
            self.seoj = tuple(self.raw[4:7])
            self.deoj = tuple(self.raw[7:10])
            self.esv = self.raw[10]
            self.opc = self.raw[11]
            self.props = []
            idx = 12
            for _ in range(self.opc):
                if idx + 2 > len(self.raw):
                    break
                epc = self.raw[idx]
                pdc = self.raw[idx+1]
                idx += 2
                edt = self.raw[idx:idx+pdc]
                self.props.append({'epc': epc, 'pdc': pdc, 'edt': edt})
                idx += pdc
            self.valid = True
        except Exception:
            self.valid = False

    def summary(self):
        return {
            'timestamp': self.timestamp,
            'ip': self.addr[0],
            'port': self.addr[1],
            'direction': self.direction,
            'tid': self.tid if hasattr(self, 'tid') else None,
            'esv': f"0x{self.esv:02X}" if hasattr(self, 'esv') else None,
            'seoj': getattr(self, 'seoj', None),
            'deoj': getattr(self, 'deoj', None),
            'opc': getattr(self, 'opc', None),
            'props': [
                {
                    'epc': f"0x{p['epc']:02X}",
                    'pdc': p['pdc'],
                    'edt': p['edt'].hex()
                } for p in getattr(self, 'props', [])
            ],
            'raw': self.raw.hex()
        }

class ENLMonitor:
    def __init__(self, port=3610, log_file=LOG_FILE):
        self.port = port
        self.log_file = log_file
        self.requests = {}  # tid: {'packet': ENLPacket, 'time': float, 'matched': False}
        self.responses = {}  # tid: [ENLPacket, ...]
        self.lock = threading.Lock()
        self.running = True

    def log(self, entry):
        with open(self.log_file, 'a') as f:
            f.write(entry + '\n')

    def monitor(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", self.port))
        self.log(f"--- ENL UDP Monitor started at {datetime.now()} ---")
        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                pkt = ENLPacket(data, addr, direction='in')
                if not pkt.valid:
                    continue
                self.handle_packet(pkt)
            except Exception as e:
                self.log(f"Error: {e}")

    def handle_packet(self, pkt):
        with self.lock:
            entry = pkt.summary()
            match_status = ""
            alert = ""
            # Outgoing request
            if pkt.esv in REQUEST_ESV:
                if pkt.tid in self.requests:
                    # TID reused before response
                    alert = f"ALERT: TID {pkt.tid} reused before response. Previous request: {self.requests[pkt.tid]['packet'].summary()}"
                self.requests[pkt.tid] = {'packet': pkt, 'time': time.time(), 'matched': False}
                match_status = "REQUEST"
            # Incoming response
            elif pkt.esv in RESPONSE_ESV:
                req = self.requests.get(pkt.tid)
                if not req:
                    match_status = "UNMATCHED RESPONSE"
                    alert = f"ALERT: Response with TID {pkt.tid} has no matching request."
                else:
                    # Check DEOJ/SEOJ and ESV pairing
                    req_pkt = req['packet']
                    expected_esv = ESV_PAIR.get(req_pkt.esv)
                    if pkt.seoj != req_pkt.deoj:
                        match_status = "MISMATCHED SOURCE"
                        alert = f"ALERT: Response SEOJ {pkt.seoj} does not match request DEOJ {req_pkt.deoj}."
                    elif pkt.esv != expected_esv:
                        match_status = "MISMATCHED ESV"
                        alert = f"ALERT: Response ESV 0x{pkt.esv:02X} does not match expected 0x{expected_esv:02X}."
                    else:
                        match_status = "MATCHED RESPONSE"
                        req['matched'] = True
                    # Check for duplicate responses
                    if pkt.tid in self.responses:
                        alert += f" ALERT: Duplicate response for TID {pkt.tid}."
                        match_status = "DUPLICATE RESPONSE"
                    self.responses.setdefault(pkt.tid, []).append(pkt)
            else:
                match_status = "OTHER"
            log_entry = f"[{entry['timestamp']}] {entry['direction']} {entry['ip']} TID={entry['tid']} ESV={entry['esv']} {match_status}\n  SEOJ={entry['seoj']} DEOJ={entry['deoj']}\n  OPC={entry['opc']} PROPS={entry['props']}\n  RAW={entry['raw']}"
            if alert:
                log_entry += f"\n  {alert}"
            self.log(log_entry)

    def cleanup(self, timeout=5):
        # Remove old requests and alert if not matched
        now = time.time()
        with self.lock:
            for tid, req in list(self.requests.items()):
                if not req['matched'] and now - req['time'] > timeout:
                    self.log(f"ALERT: No response for TID {tid} after {timeout}s. Request: {req['packet'].summary()}")
                    del self.requests[tid]

    def start(self):
        t = threading.Thread(target=self.monitor, daemon=True)
        t.start()
        try:
            while True:
                time.sleep(1)
                self.cleanup()
        except KeyboardInterrupt:
            self.running = False
            self.log("--- ENL UDP Monitor stopped ---")

if __name__ == "__main__":
    monitor = ENLMonitor()
    monitor.start()
