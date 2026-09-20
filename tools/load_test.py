"""Real TCP + UDP localhost clients; no rendered clients or claims about 50 PCs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import time,json,queue,statistics
from game.world.physics import CollisionWorld
from game.server.host import Host
from game.network.client import Connection

def wait(client,kind,seconds=10):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            p=client.events.get(timeout=.1)
            if p['t']==kind:return p
        except queue.Empty:pass
    raise RuntimeError(f'Timeout {kind}')

def main():
    host=Host(CollisionWorld(),capacity=50,port=0,discovery_port=0)
    clients=[]; result={}
    try:
        first=Connection('127.0.0.1',host.port,'HOST',owner=host.owner); clients.append(first); wait(first,'welcome')
        for i in range(49): clients.append(Connection('127.0.0.1',host.port,f'TEST {i+1:02}'))
        for c in clients[1:]: wait(c,'welcome'); c.send('ready',ready=True)
        time.sleep(.5); first.send('start')
        for c in clients: wait(c,'started')
        deadline=time.monotonic()+8; timings=[]; snapshots=[0]*50; max_players=0
        while time.monotonic()<deadline:
            for i,c in enumerate(clients):
                c.controls(move=[0,0],yaw=i*7,pitch=0)
                while not c.events.empty():
                    p=c.events.get_nowait()
                    if p['t']=='snapshot':snapshots[i]+=1; max_players=max(max_players,len(p['players']))
                    if p['t']=='disconnected':raise RuntimeError(p['reason'])
            timings.append(host.tick_ms); time.sleep(.01)
        result=dict(clients=len(clients),seconds=8,players_in_snapshot=max_players,
                    snapshots_min=min(snapshots),snapshots_max=max(snapshots),
                    server_tick_mean_ms=round(statistics.mean(timings),3),server_tick_max_ms=round(max(timings),3),
                    ping_mean_ms=round(statistics.mean(c.ping for c in clients),2),errors=list(host.errors.queue))
        assert min(snapshots)>30 and max_players==50 and not result['errors']
        print(json.dumps(result,indent=2))
        Path('logs/load-test.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    finally:
        for c in clients:c.close()
        host.close()

if __name__=='__main__':main()
