import math
import random
from dataclasses import dataclass, field
from panda3d.core import Vec3
from game.world.physics import Mover, direction, ray_sphere
from game.world.zone import Zone
from game.weapons import WEAPONS

@dataclass
class Player:
    id: int
    name: str
    ready: bool = False
    bot: bool = False
    hp: float = 100
    armor: float = 0
    kills: int = 0
    alive: bool = True
    weapon: str = 'pistol'
    inventory: list = field(default_factory=lambda:['pistol'])
    ammo: dict = field(default_factory=lambda:{'pistol':12})
    reserve: int = 72
    meds: int = 1
    reload_until: float = 0
    heal_until: float = 0
    next_fire: float = 0
    mover: object = None
    controls: dict = field(default_factory=dict)
    yaw: float = 0
    pitch: float = 0
    last_input: float = 0
    last_seq: int = -1
    brain_at: float = 0
    target: object = None
    stuck: float = 0

    def public(self):
        return dict(id=self.id,name=self.name,ready=self.ready,bot=self.bot,hp=round(self.hp),armor=round(self.armor),kills=self.kills,alive=self.alive)

    def private(self, now):
        return dict(weapon=self.weapon,inventory=self.inventory,ammo=self.ammo,reserve=self.reserve,meds=self.meds,
                    reload=max(0,self.reload_until-now),heal=max(0,self.heal_until-now))

class Match:
    def __init__(self, physics, emit, seed=None):
        self.physics=physics; self.emit=emit; self.rng=random.Random(seed)
        self.players={}; self.phase='lobby'; self.now=0.; self.items={}; self.zone=Zone(seed)
        self.spawns=physics.spawn_points(); self.tick=0; self.winner=None; self.training=False
        self.zone_damage_at=0

    def start(self,bots=0):
        if self.phase!='lobby': return
        for i in range(bots):
            pid=1000+i; self.players[pid]=Player(pid,f'BOT {i+1:02}',ready=True,bot=True)
        points=self.spawns[:]; self.rng.shuffle(points)
        for p,pos in zip(self.players.values(),points):
            p.mover=Mover(self.physics,pos); p.hp=100; p.armor=0; p.alive=True; p.kills=0
            p.inventory=['pistol']; p.weapon='pistol'; p.ammo={'pistol':12}; p.reserve=72; p.meds=1
            p.next_fire=p.reload_until=p.heal_until=0; p.controls={}
            if p.bot: p.inventory+=['rifle']; p.weapon='rifle'; p.ammo['rifle']=30; p.reserve=999
        kinds=['rifle','smg','shotgun','dmr','ammo','ammo','bandage','medkit','armor1','armor2']
        self.items={i:dict(id=i,kind=kinds[i%len(kinds)],pos=pos) for i,pos in enumerate(points[:180])}
        self.zone=Zone(self.rng.randrange(1000000)); self.now=0; self.zone_damage_at=0
        self.training=len(self.players)==1; self.phase='playing'; self.tick=0; self.winner=None
        self.emit('started',map='drive_city',training=self.training,items=list(self.items.values()))

    def return_lobby(self):
        self.players={i:p for i,p in self.players.items() if not p.bot}
        for p in self.players.values(): p.ready=False; p.alive=True; p.hp=100; p.mover=None
        self.phase='lobby'; self.items={}; self.winner=None
        self.emit('returned')

    def damage(self, victim, damage, killer=None, head=False, source='zone'):
        if not victim.alive: return
        blocked=min(victim.armor,damage*.5) if source=='shot' else 0
        victim.armor-=blocked; victim.hp=max(0,victim.hp-damage+blocked); victim.heal_until=0
        self.emit('damage',victim=victim.id,attacker=killer.id if killer else None,head=head,amount=round(damage-blocked),source=source)
        if victim.hp<=0:
            victim.alive=False; victim.controls={}
            if killer and killer!=victim: killer.kills+=1
            self.emit('death',victim=victim.id,name=victim.name,killer=killer.name if killer else '자기장',head=head)

    def fire(self,p):
        w=WEAPONS[p.weapon]
        if not p.alive or self.phase!='playing' or self.now+1e-5<p.next_fire or p.reload_until>self.now or p.heal_until>self.now or p.ammo.get(p.weapon,0)<=0: return False
        p.ammo[p.weapon]-=1; p.next_fire=max(p.next_fire+1/w.rate,self.now+1/w.rate-.016)
        origin=p.mover.pos+Vec3(0,1.02 if p.mover.crouch else 1.52,0)
        forward=direction(p.yaw,p.pitch)
        # Camera -> muzzle check prevents a long barrel shooting through a nearby wall.
        muzzle=origin+forward*.65+Vec3(0,-.12,0)
        blocked=self.physics.ray(origin,muzzle)
        impacts=[]; hit_ids=[]
        for _ in range(w.pellets):
            spread=w.spread*(.28 if p.controls.get('ads') else 1)
            d=Vec3(forward.x+self.rng.gauss(0,spread),forward.y+self.rng.gauss(0,spread),forward.z+self.rng.gauss(0,spread)); d.normalize()
            wall=0 if blocked else self.physics.distance(origin,d,w.range)
            best=wall; victim=None; head=False
            for other in self.players.values():
                if other.id==p.id or not other.alive: continue
                pos=other.mover.pos
                height=1.02 if other.mover.crouch else 1.52
                for center,radius,is_head in ((pos+Vec3(0,height,0),.25,True),(pos+Vec3(0,height*.57,0),.43,False)):
                    t=ray_sphere(origin,d,center,radius)
                    if t is not None and t<best: best=t; victim=other; head=is_head
            if victim:
                self.damage(victim,w.damage*(1.8 if head else 1),p,head,'shot'); hit_ids.append(victim.id)
            if not impacts: impacts.append(list(origin+d*best))
        self.emit('shot',id=p.id,weapon=p.weapon,origin=list(origin),impact=impacts[0],hits=hit_ids)
        return True

    def action(self,p,kind,**data):
        if self.phase!='playing' or not p.alive: return
        if kind=='reload' and not p.reload_until and p.reserve>0 and p.ammo.get(p.weapon,0)<WEAPONS[p.weapon].magazine:
            p.reload_until=self.now+WEAPONS[p.weapon].reload; p.heal_until=0
        elif kind=='switch' and data.get('weapon') in p.inventory:
            p.weapon=data['weapon']; p.reload_until=0; p.heal_until=0
        elif kind=='heal' and p.meds>0 and p.hp<100 and not p.heal_until:
            p.heal_until=self.now+3.; p.reload_until=0
        elif kind=='pickup':
            item=self.items.get(data.get('item'))
            if not item or (p.mover.pos-Vec3(*item['pos'])).length()>2.8: return
            if self.physics.distance(p.mover.pos+Vec3(0,.6,0), (Vec3(*item['pos'])+Vec3(0,.4,0)-p.mover.pos-Vec3(0,.6,0)).normalized(),2)<.15: return
            k=item['kind']
            if k in WEAPONS:
                if k not in p.inventory: p.inventory.append(k); p.ammo[k]=WEAPONS[k].magazine
                else: p.reserve+=WEAPONS[k].magazine
                p.weapon=k; p.reload_until=0
            elif k=='ammo': p.reserve+=60
            elif k in ('bandage','medkit'): p.meds+=1 if k=='bandage' else 2
            else: p.armor=max(p.armor,50 if k=='armor1' else 100)
            del self.items[item['id']]
            self.emit('pickup',item=item['id'],player=p.id,kind=k)

    def bot_input(self,p):
        if self.now<p.brain_at: return
        p.brain_at=self.now+.18+self.rng.random()*.08
        enemies=[o for o in self.players.values() if o.id!=p.id and o.alive]
        if not enemies: return
        target=min(enemies,key=lambda o:(o.mover.pos-p.mover.pos).lengthSquared())
        delta=target.mover.pos-p.mover.pos; dist=delta.length()
        visible=dist<95 and self.physics.distance(p.mover.pos+Vec3(0,1.45,0),delta.normalized(),dist)>dist-.5
        if visible:
            yaw=math.degrees(math.atan2(delta.x,delta.z))+self.rng.uniform(-3,3)
            pitch=-math.degrees(math.atan2(delta.y,max(.1,math.hypot(delta.x,delta.z))))+self.rng.uniform(-2,2)
            p.controls=dict(move=[self.rng.choice([-.5,.5]),.5 if dist>22 else 0],yaw=yaw,pitch=pitch,fire=True,ads=True)
        else:
            center=Vec3(self.zone.next_center[0],p.mover.pos.y,self.zone.next_center[1])
            goal=center if self.zone.outside(p.mover.pos) or self.zone.radius<75 else target.mover.pos
            delta=goal-p.mover.pos; yaw=math.degrees(math.atan2(delta.x,delta.z))
            if self.physics.distance(p.mover.pos+Vec3(0,.8,0),direction(yaw,0),2)<1.6:
                yaw+=95+35*math.sin(self.now*.4+p.id)
            p.controls=dict(move=[0,1],yaw=yaw,pitch=0,fire=False,sprint=True,jump=False)
        if p.ammo.get(p.weapon,0)==0: self.action(p,'reload')
        if p.hp<55: self.action(p,'heal')
        for item in list(self.items.values()):
            if (p.mover.pos-Vec3(*item['pos'])).lengthSquared()<6:
                self.action(p,'pickup',item=item['id']); break

    def update(self,dt):
        if self.phase!='playing': return
        self.now+=dt; self.tick+=1; self.zone.update(dt)
        for p in list(self.players.values()):
            if not p.alive: continue
            if p.bot: self.bot_input(p)
            elif self.now-p.last_input>.5: p.controls={}
            p.yaw=float(p.controls.get('yaw',p.yaw)); p.pitch=float(p.controls.get('pitch',p.pitch))
            p.mover.step(p.controls,dt)
            if p.mover.pos.y < -15: self.damage(p,1000,source='fall')
            if p.reload_until and self.now>=p.reload_until:
                amount=min(WEAPONS[p.weapon].magazine-p.ammo.get(p.weapon,0),p.reserve)
                p.ammo[p.weapon]=p.ammo.get(p.weapon,0)+amount; p.reserve-=amount; p.reload_until=0
            if p.heal_until and self.now>=p.heal_until:
                p.hp=min(100,p.hp+50); p.meds-=1; p.heal_until=0
            if p.controls.get('fire'): self.fire(p)
        if self.now>=self.zone_damage_at:
            self.zone_damage_at=self.now+1
            for p in self.players.values():
                if p.alive and self.zone.outside(p.mover.pos): self.damage(p,2+self.zone.stage*2)
        alive=[p for p in self.players.values() if p.alive]
        if len(alive)==0 or (len(alive)==1 and not self.training):
            self.phase='finished'; self.winner=alive[0].id if alive else None
            self.emit('finished',winner=self.winner,name=alive[0].name if alive else 'NO SURVIVOR')

    def snapshot(self):
        return [[p.id,*[round(v,3) for v in p.mover.pos],round(p.yaw,1),round(p.pitch,1),round(p.hp),round(p.armor),p.alive,p.mover.crouch,p.weapon] for p in self.players.values() if p.mover]
