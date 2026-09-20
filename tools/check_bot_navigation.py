"""Real map, accelerated simulation of bots evacuating a closing circle."""
import sys,json,math,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game.world.physics import CollisionWorld
from game.server.match import Match,Player
from panda3d.core import Vec3
w=CollisionWorld();m=Match(w,lambda *a,**k:None,seed=82)
m.players[1]=Player(1,'observer');m.start(20)
# Isolate navigation: no opponents or gunfire; zone damage remains authoritative.
for p in m.players.values():p.team=1
m.training=True;m.zone.elapsed=105
points=sorted(m.spawns,key=lambda p:math.hypot(p[0]-m.zone.next_center[0],p[2]-m.zone.next_center[1]),reverse=True)
bots=[p for p in m.players.values() if p.bot]
for p,pos in zip(bots,points):p.mover.pos=Vec3(*pos)
initial=sum(math.hypot(p.mover.pos.x-m.zone.next_center[0],p.mover.pos.z-m.zone.next_center[1])>m.zone.next_radius for p in bots)
began=time.perf_counter()
for _ in range(45*30):m.update(1/30)
result=dict(bots=20,initially_outside_next=initial,alive=sum(p.alive for p in bots),inside_current=sum(not m.zone.outside(p.mover.pos) for p in bots),elapsed_simulation=45,wall_seconds=round(time.perf_counter()-began,2))
for p in bots:
    if m.zone.outside(p.mover.pos):print('OUT',p.id,list(p.mover.pos),'HP',p.hp,'route',p.route[:3],p.controls)
print(json.dumps(result));Path('logs/bot-navigation.json').write_text(json.dumps(result,indent=2))
assert result['inside_current']>=16 and result['alive']>=18,result
