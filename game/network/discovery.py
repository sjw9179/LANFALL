import socket
import threading
import time
from game.config import DISCOVERY_PORT
from game.network.protocol import encode, decode

class Discovery:
    def __init__(self, port=DISCOVERY_PORT):
        self.port = port
        self.rooms = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='LAN discovery')
        self.thread.start()

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(('0.0.0.0', 0))
            s.settimeout(.2)
            sent = 0
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now - sent >= 1.5:
                    sent = now
                    for host in ('255.255.255.255', '127.0.0.1'):
                        try: s.sendto(encode('DISCOVER_GAME', stamp=now), (host,self.port))
                        except OSError: pass
                try:
                    data, addr = s.recvfrom(4096)
                    p = decode(data)
                    if p['t'] == 'GAME_OFFER' and type(p.get('port')) is int and 0 < p['port'] < 65536:
                        p.update(ip=addr[0], seen=time.monotonic(), ping=max(0,(time.monotonic()-p['stamp'])*1000))
                        with self.lock: self.rooms[(addr[0],p['port'])] = p
                except (OSError,ValueError,KeyError,TypeError): pass

    def list(self):
        with self.lock:
            self.rooms = {k:v for k,v in self.rooms.items() if time.monotonic()-v['seen'] < 5}
            return list(self.rooms.values())

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=1)
