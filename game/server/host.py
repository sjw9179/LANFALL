"""Single authoritative simulation/socket thread. No renderer is touched here."""
import queue
import secrets
import select
import socket
import threading
import time
from dataclasses import dataclass,field
from game.config import GAME_PORT,DISCOVERY_PORT,MAX_PLAYERS
from game.network.protocol import Framer,frame,encode,decode,finite_vector
from game.server.match import Match,Player

@dataclass
class Peer:
    sock: object
    address: tuple
    parser: object=field(default_factory=Framer)
    pending: bytearray=field(default_factory=bytearray)
    id: object=None
    token: str=''
    udp: object=None
    seen: float=field(default_factory=time.monotonic)
    joined: float=field(default_factory=time.monotonic)
    rate_at: float=0
    rate_count: int=0

class Host:
    def __init__(self,physics,name='LANFALL ROOM',capacity=10,bots=0,code='',port=GAME_PORT,discovery_port=DISCOVERY_PORT,team_size=1):
        self.name=str(name)[:32]; self.capacity=max(1,min(MAX_PLAYERS,int(capacity)))
        self.bots=max(0,min(int(bots),self.capacity-1)); self.code=str(code)[:24]
        self.port=int(port); self.discovery_port=discovery_port; self.owner=secrets.token_hex(16)
        self.host_id=None; self.next_id=1; self.peers={}; self.sockets=[]
        self.stop_event=threading.Event(); self.errors=queue.Queue(); self.ready=threading.Event()
        self.match=Match(physics,self.broadcast)
        self.match.team_size=4 if team_size==4 else 1
        self.loaded=set();self.loading_at=0
        self.tick_ms=0.; self.thread=threading.Thread(target=self.run,daemon=True,name='LANFALL host')
        self.thread.start()
        if not self.ready.wait(4): raise RuntimeError('Server startup timeout')
        if not self.errors.empty(): raise RuntimeError(self.errors.get())

    def send(self,peer,kind,**data):
        peer.pending.extend(frame(kind,**data))
        if len(peer.pending)>1048576: self.drop(peer)

    def broadcast(self,kind,**data):
        for peer in list(self.peers.values()):
            if peer.id is not None: self.send(peer,kind,**data)

    def lobby(self):
        self.broadcast('lobby',name=self.name,capacity=self.capacity,bots=self.bots,host=self.host_id,
                       phase=self.match.phase,players=[p.public() for p in self.match.players.values()],map='drive_city',team_size=self.match.team_size)

    def drop(self,peer):
        self.peers.pop(peer.sock,None)
        try: peer.sock.close()
        except OSError: pass
        if peer.id in self.match.players:
            p=self.match.players[peer.id]
            if self.match.phase=='playing': self.match.damage(p,10000,source='disconnect')
            del self.match.players[peer.id]
            self.loaded.discard(peer.id)
            if self.match.phase=='loading':self.check_loaded()
            self.lobby()
        if peer.id is not None and peer.id==self.host_id: self.stop_event.set()

    def handle(self,peer,p):
        kind=p['t']
        if time.monotonic()-peer.rate_at>1: peer.rate_at=time.monotonic(); peer.rate_count=0
        peer.rate_count+=1
        if peer.rate_count>100: raise ValueError('Message rate exceeded')
        if kind=='ping':
            if type(p.get('stamp')) in (int,float): self.send(peer,'pong',stamp=p['stamp'])
            return
        if peer.id is None:
            if kind!='join': raise ValueError('Join first')
            reason=None
            owner=secrets.compare_digest(str(p.get('owner','')),self.owner)
            if self.host_id is None and not owner: reason='Host is preparing the room. Try again.'
            elif self.match.phase!='lobby': reason='Match already started'
            elif len(self.match.players)+self.bots>=self.capacity: reason='Room is full'
            elif self.code and not secrets.compare_digest(str(p.get('code','')),self.code): reason='Wrong invitation code'
            name=p.get('name')
            if not isinstance(name,str) or not name.strip() or len(name)>24: reason='Nickname must be 1–24 characters'
            if reason:
                self.send(peer,'error',reason=reason); return
            peer.id=self.next_id; self.next_id+=1; peer.token=secrets.token_hex(12)
            self.match.players[peer.id]=Player(peer.id,name.strip(),ready=owner)
            self.match.players[peer.id].team=next((i for i in range(1,51) if sum(o.team==i for o in self.match.players.values())<4),1) if self.match.team_size==4 else peer.id
            if owner: self.host_id=peer.id
            self.send(peer,'welcome',id=peer.id,token=peer.token,host=self.host_id)
            self.lobby(); return
        player=self.match.players.get(peer.id)
        if not player: return
        if kind=='ready' and self.match.phase=='lobby': player.ready=bool(p.get('ready')); self.lobby()
        elif kind=='team' and self.match.phase=='lobby' and self.match.team_size==4:
            team=p.get('team')
            if type(team) is int and 1<=team<=13 and sum(o.team==team for o in self.match.players.values() if o.id!=player.id)<4:
                player.team=team;player.ready=peer.id==self.host_id;self.lobby()
        elif kind=='loaded' and self.match.phase=='loading' and p.get('round')==self.match.round_id:
            self.loaded.add(peer.id);self.check_loaded()
        elif kind=='spectate' and not player.alive:
            target=self.match.players.get(p.get('id'))
            if target and target.alive:player.watching=target.id
        elif kind=='bots' and peer.id==self.host_id and self.match.phase=='lobby':
            count=p.get('count')
            if type(count) is int:
                self.bots=max(0,min(count,self.capacity-len(self.match.players)))
                self.lobby()
        elif kind=='start' and peer.id==self.host_id:
            if self.match.phase=='lobby' and all(o.ready for o in self.match.players.values()):
                self.loaded=set();self.loading_at=time.monotonic()
                self.match.start(self.bots);self.match.phase='loading';self.lobby();self.check_loaded()
            else: self.send(peer,'error',reason='All players must be ready')
        elif kind=='return' and peer.id==self.host_id and self.match.phase=='finished':
            self.match.return_lobby(); self.lobby()
        elif kind in ('reload','switch','pickup','heal','cancel'):
            self.match.action(player,kind,**{k:v for k,v in p.items() if k not in ('m','v','t')})

    def check_loaded(self):
        humans={p.id for p in self.match.players.values() if not p.bot}
        self.broadcast('loading',ready=len(humans & self.loaded),total=len(humans))
        if humans and humans<=self.loaded:
            self.match.phase='playing';self.match.now=0
            for p in self.match.players.values():p.controls={}
            self.broadcast('deployed',round=self.match.round_id)

    def input_packet(self,p,addr):
        if p['t']!='input' or type(p.get('id')) is not int or type(p.get('seq')) is not int: return
        peer=next((peer for peer in self.peers.values() if peer.id==p['id']),None)
        if not peer or addr[0]!=peer.address[0] or not secrets.compare_digest(str(p.get('token','')),peer.token): return
        player=self.match.players.get(peer.id)
        if not player or p['seq']<=player.last_seq: return
        if not finite_vector(p.get('move',[0,0]),2,1) or not finite_vector([p.get('yaw',0),p.get('pitch',0)],2,100000): return
        player.last_seq=p['seq']; peer.udp=addr; peer.seen=time.monotonic()
        player.last_input=self.match.now
        player.controls=dict(move=p.get('move',[0,0]),yaw=p.get('yaw',0)%360,pitch=max(-88,min(88,p.get('pitch',0))),
                             **{k:bool(p.get(k,False)) for k in ('fire','ads','sprint','crouch','jump')})

    def run(self):
        try:
            tcp=socket.socket(); tcp.bind(('0.0.0.0',self.port)); tcp.listen(64); tcp.setblocking(False)
            self.port=tcp.getsockname()[1]; self.sockets.append(tcp)
            udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); udp.bind(('0.0.0.0',self.port)); udp.setblocking(False); self.sockets.append(udp)
            discovery=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            discovery.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
            discovery.bind(('0.0.0.0',self.discovery_port)); discovery.setblocking(False); self.sockets.append(discovery)
            self.discovery_port=discovery.getsockname()[1]
            self.ready.set(); last=time.monotonic(); accumulator=0; state_at=0
            while not self.stop_event.is_set():
                now=time.monotonic(); accumulator+=min(.15,now-last); last=now
                sockets=self.sockets+list(self.peers)
                readable,writable,_=select.select(sockets,[s for s,p in self.peers.items() if p.pending],[],.002)
                for s in readable:
                    if s==tcp:
                        conn,addr=tcp.accept(); conn.setblocking(False); conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                        if len(self.peers)>=64: conn.close()
                        else: self.peers[conn]=Peer(conn,addr)
                    elif s==discovery:
                        try:
                            data,addr=s.recvfrom(4096); p=decode(data)
                            if p['t']=='DISCOVER_GAME' and type(p.get('stamp')) in (int,float):
                                s.sendto(encode('GAME_OFFER',name=self.name,port=self.port,count=len(self.match.players),capacity=self.capacity,bots=self.bots,
                                                playing=self.match.phase!='lobby',locked=bool(self.code),stamp=p['stamp'],host=socket.gethostname()),addr)
                        except (OSError,ValueError,TypeError): pass
                    elif s==udp:
                        for _ in range(256):
                            try: data,addr=s.recvfrom(2048)
                            except (BlockingIOError,ConnectionResetError): break
                            try: self.input_packet(decode(data),addr)
                            except (ValueError,TypeError,KeyError): pass
                    else:
                        peer=self.peers.get(s)
                        if not peer: continue
                        try:
                            data=s.recv(65536)
                            if not data: self.drop(peer); continue
                            peer.seen=now
                            for p in peer.parser.feed(data): self.handle(peer,p)
                        except (OSError,ValueError,TypeError,KeyError): self.drop(peer)
                for s in writable:
                    peer=self.peers.get(s)
                    if not peer: continue
                    try:
                        n=s.send(peer.pending); del peer.pending[:n]
                    except BlockingIOError: pass
                    except OSError: self.drop(peer)
                while accumulator>=1/30:
                    began=time.perf_counter(); self.match.update(1/30); self.tick_ms=(time.perf_counter()-began)*1000; accumulator-=1/30
                    if self.match.phase in ('playing','loading') and self.match.tick%2==0:
                        rows=self.match.snapshot(); chunks=[rows[i:i+10] for i in range(0,len(rows),10)]
                        for peer in list(self.peers.values()):
                            if peer.udp:
                                for index,rows_part in enumerate(chunks):
                                    packet=encode('snapshot',token=peer.token,round=self.match.round_id,tick=self.match.tick,part=index,parts=len(chunks),players=rows_part,zone=self.match.zone.state())
                                    try: udp.sendto(packet,peer.udp)
                                    except OSError: pass
                if now-state_at>.25:
                    state_at=now
                    for peer in list(self.peers.values()):
                        p=self.match.players.get(peer.id)
                        if p and self.match.phase!='lobby':
                            target=self.match.players.get(p.watching) if not p.alive else None
                            watch=dict(id=target.id,own=target.private(self.match.now)) if target and target.alive else {}
                            self.send(peer,'state',players=[q.public() for q in self.match.players.values()],own=p.private(self.match.now),watch=watch,zone=self.match.zone.state(),tick_ms=round(self.tick_ms,2))
                for peer in list(self.peers.values()):
                    if self.match.phase=='loading' and now-self.loading_at>90 and peer.id not in self.loaded:
                        self.send(peer,'error',reason='맵 로딩 제한 시간(90초)을 초과했습니다.');self.drop(peer);continue
                    if now-peer.seen>8 or (peer.id is None and now-peer.joined>5): self.drop(peer)
        except Exception as e:
            import traceback
            traceback.print_exc(); self.errors.put(str(e)); self.ready.set()
        finally:
            for peer in list(self.peers.values()):
                try: peer.sock.close()
                except OSError: pass
            for s in self.sockets: s.close()

    def close(self):
        self.stop_event.set(); self.thread.join(timeout=3)
