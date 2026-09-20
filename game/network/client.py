"""Network worker owns sockets; Ursina consumes an event queue on its main thread."""
import queue
import select
import socket
import threading
import time
from game.network.protocol import Framer, frame, encode, decode

class Connection:
    def __init__(self, host, port, name, code='', owner=''):
        self.address = (socket.gethostbyname(host), int(port))
        self.events = queue.Queue(maxsize=2048)
        self.outgoing = queue.Queue(maxsize=256)
        self.latest = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.id = None
        self.token = ''
        self.seq = 0
        self.tick = -1
        self.last_recv = time.monotonic()
        self.tx = self.rx = self.lost = 0
        self.ping = 0
        self.thread = threading.Thread(target=self.run,args=(name,code,owner),daemon=True,name='Game client')
        self.thread.start()

    def send(self, kind, **data):
        try: self.outgoing.put_nowait(frame(kind, **data))
        except queue.Full: self.close()

    def controls(self, **data):
        with self.lock: self.latest = data

    def emit(self, p):
        try: self.events.put_nowait(p)
        except queue.Full:
            try: self.events.get_nowait()
            except queue.Empty: pass
            self.events.put_nowait(p)

    def run(self, name, code, owner):
        tcp = udp = None
        try:
            tcp = socket.create_connection(self.address, timeout=4)
            tcp.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            tcp.setblocking(False)
            udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            udp.bind(('0.0.0.0',0)); udp.setblocking(False)
            pending = bytearray(frame('join',name=name,code=code,owner=owner))
            parser = Framer(); last_input = 0; heartbeat = 0; fragments = {}
            while not self.stop_event.is_set():
                now = time.monotonic()
                while not self.outgoing.empty(): pending.extend(self.outgoing.get_nowait())
                readable,writable,_ = select.select([tcp,udp],[tcp] if pending else [],[],.01)
                if writable:
                    count=tcp.send(pending); del pending[:count]
                if tcp in readable:
                    data=tcp.recv(65536)
                    if not data: raise ConnectionError('Host disconnected')
                    self.last_recv=now
                    for p in parser.feed(data):
                        if p['t']=='welcome': self.id=p['id']; self.token=p['token']
                        if p['t']=='pong': self.ping=(now-p['stamp'])*1000
                        self.emit(p)
                if udp in readable:
                    for _ in range(128):
                        try: data,addr=udp.recvfrom(65536)
                        except BlockingIOError: break
                        if addr!=self.address: continue
                        try: p=decode(data)
                        except ValueError: continue
                        if p.get('t')!='snapshot' or p.get('token')!=self.token: continue
                        tick=p.get('tick',-1)
                        if type(tick)!=int or tick<=self.tick: continue
                        parts=p.get('parts',1); part=p.get('part',0)
                        if type(parts)!=int or type(part)!=int or not 1<=parts<=5 or not 0<=part<parts: continue
                        fragments={k:v for k,v in fragments.items() if k>=tick-8}
                        group=fragments.setdefault(tick,{})
                        group[part]=p.get('players',[])
                        if len(group)!=parts: continue
                        p['players']=[row for i in range(parts) for row in group[i]]
                        fragments.pop(tick,None)
                        if self.tick>=0: self.lost+=max(0,(tick-self.tick)//2-1)
                        self.tick=tick; self.rx+=1; self.last_recv=now
                        self.emit(p)
                if self.id is not None and now-last_input>=1/30:
                    with self.lock: controls=self.latest or {}
                    self.seq+=1
                    udp.sendto(encode('input',id=self.id,token=self.token,seq=self.seq,**controls),self.address)
                    self.tx+=1; last_input=now
                if now-heartbeat>1:
                    pending.extend(frame('ping',stamp=now)); heartbeat=now
                if now-self.last_recv>8: raise ConnectionError('Host timed out (8 seconds)')
        except (OSError,ValueError,ConnectionError) as e:
            if not self.stop_event.is_set(): self.emit({'t':'disconnected','reason':str(e)})
        finally:
            for s in (tcp,udp):
                if s:
                    try: s.close()
                    except OSError: pass

    def close(self):
        self.stop_event.set()
        if threading.current_thread()!=self.thread: self.thread.join(timeout=1)
