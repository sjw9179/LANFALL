import queue
import socket
import time
import pytest
from game.network.client import Connection
from game.network.discovery import Discovery
from game.network.protocol import encode
from game.server.host import Host
from test_game import world

def wait_event(client,kind,timeout=5):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            p=client.events.get(timeout=.1)
            if p['t']==kind:return p
        except queue.Empty: pass
    raise AssertionError(f'Timeout waiting for {kind}')

def test_two_clients_ready_start_sync_stale_and_disconnect(world):
    host=Host(world,capacity=2,port=0,discovery_port=0,code='1234')
    a=b=None
    try:
        a=Connection('127.0.0.1',host.port,'Host','1234',host.owner); wait_event(a,'welcome')
        b=Connection('127.0.0.1',host.port,'Guest','1234'); wait_event(b,'welcome')
        b.send('start'); time.sleep(.08); assert host.match.phase=='lobby'
        a.send('start'); wait_event(a,'error'); assert host.match.phase=='lobby'
        b.send('ready',ready=True); time.sleep(.08); a.send('start')
        wait_event(a,'started'); wait_event(b,'started')
        assert host.match.phase=='loading'
        a.send('loaded',round=1);time.sleep(.1)
        assert host.match.phase=='loading' and host.match.now==0
        b.send('loaded',round=0);time.sleep(.08);assert host.match.phase=='loading'
        b.send('loaded',round=1);wait_event(a,'deployed');wait_event(b,'deployed')
        assert host.match.phase=='playing'
        s1=wait_event(a,'snapshot'); s2=wait_event(b,'snapshot')
        assert len(s1['players'])==len(s2['players'])==2
        assert s1['zone']['next']==s2['zone']['next']
        peer=next(p for p in host.peers.values() if p.id==b.id)
        player=host.match.players[b.id]; player.last_seq=10000
        host.input_packet(dict(t='input',id=b.id,seq=4,token=peer.token,move=[1,0]),peer.udp)
        assert player.last_seq==10000
        # Restart through the lobby: old round UDP packets must not freeze the next match.
        host.match.phase='finished';a.send('return');wait_event(a,'returned');wait_event(b,'returned')
        a.send('ready',ready=True);b.send('ready',ready=True);time.sleep(.08);a.send('start')
        wait_event(a,'started');wait_event(b,'started')
        a.send('loaded',round=2);b.send('loaded',round=2);wait_event(a,'deployed')
        restarted=wait_event(a,'snapshot')
        assert restarted['round']==2 and a.round_id==2
        host.close(); wait_event(b,'disconnected',timeout=3)
    finally:
        if a:a.close()
        if b:b.close()
        host.close()

def test_discovery_expiry_and_invalid_code(world):
    host=Host(world,capacity=2,port=0,discovery_port=0,code='secret')
    discovery=Discovery(host.discovery_port)
    a=Connection('127.0.0.1',host.port,'Host','secret',host.owner)
    bad=None
    try:
        wait_event(a,'welcome')
        bad=Connection('127.0.0.1',host.port,'Guest','wrong'); assert 'code' in wait_event(bad,'error')['reason'].lower()
        deadline=time.monotonic()+4
        while not discovery.list() and time.monotonic()<deadline:time.sleep(.1)
        assert discovery.list()[0]['capacity']==2
        host.close()
        for room in discovery.rooms.values():room['seen']-=6
        assert not discovery.list()
    finally: a.close(); bad and bad.close(); discovery.close(); host.close()

def test_lobby_bots_owner_capacity_and_phase(world):
    host=Host(world,capacity=4,port=0,discovery_port=0)
    a=b=None
    try:
        a=Connection('127.0.0.1',host.port,'Host',owner=host.owner);wait_event(a,'welcome')
        b=Connection('127.0.0.1',host.port,'Guest');wait_event(b,'welcome')
        b.send('bots',count=2);time.sleep(.08);assert host.bots==0
        a.send('bots',count=99);time.sleep(.08);assert host.bots==2
        a.send('bots',count=-1);time.sleep(.08);assert host.bots==0
        a.send('bots',count=1);b.send('ready',ready=True);time.sleep(.08);a.send('start')
        wait_event(a,'started');assert len(host.match.players)==3
        a.send('bots',count=0);time.sleep(.08);assert host.bots==1
    finally:
        if a:a.close()
        if b:b.close()
        host.close()

def test_four_player_team_capacity_and_switch(world):
    host=Host(world,capacity=5,port=0,discovery_port=0,team_size=4);clients=[]
    try:
        for i in range(5):
            c=Connection('127.0.0.1',host.port,f'P{i}',owner=host.owner if i==0 else '')
            clients.append(c);wait_event(c,'welcome')
        assert [p.team for p in host.match.players.values()]==[1,1,1,1,2]
        clients[4].send('team',team=1);time.sleep(.08);assert host.match.players[5].team==2
        clients[1].send('team',team=2);time.sleep(.08)
        assert host.match.players[2].team==2 and not host.match.players[2].ready
    finally:
        for c in clients:c.close()
        host.close()
