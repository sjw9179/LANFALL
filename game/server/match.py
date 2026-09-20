import math
import random
from dataclasses import dataclass, field
from panda3d.core import Vec3
from game.world.physics import Mover, direction, ray_sphere
from game.world.zone import Zone
from game.weapons import WEAPONS
from game.items import MEDICAL, starting_medical
from game.world.navigation import Navigation

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
    medical: dict = field(default_factory=starting_medical)
    heal_kind: str = ''
    boost: float = 0
    damage_dealt: float = 0
    headshots: int = 0
    shots: int = 0
    rank: int = 0
    survived: float = 0
    team: int = 0
    route: list = field(default_factory=list)
    route_at: float = 0
    watching: int = 0

    def public(self):
        return dict(id=self.id,name=self.name,ready=self.ready,bot=self.bot,hp=round(self.hp),armor=round(self.armor),kills=self.kills,alive=self.alive,rank=self.rank,team=self.team)

    def private(self, now):
        return dict(weapon=self.weapon,inventory=self.inventory,ammo=self.ammo,reserve=self.reserve,meds=self.meds,
                    reload=max(0,self.reload_until-now),heal=max(0,self.heal_until-now),heal_kind=self.heal_kind,
                    medical=self.medical,boost=round(self.boost,1),stats=self.stats(now))

    def stats(self,now):
        return dict(rank=self.rank,kills=self.kills,damage=round(self.damage_dealt),headshots=self.headshots,
                    shots=self.shots,survived=round(now if self.alive else self.survived))

class Match:
    def __init__(self, physics, emit, seed=None):
        self.physics=physics; self.emit=emit; self.rng=random.Random(seed)
        self.players={}; self.phase='lobby'; self.now=0.; self.items={}; self.zone=Zone(seed)
        self.spawns=physics.spawn_points(); self.tick=0; self.winner=None; self.training=False
        self.zone_damage_at=0
        self.round_id=0
        self.team_size=1;self.navigation=Navigation()

    def start(self,bots=0):
        if self.phase!='lobby': return
        for i in range(bots):
            pid=1000+i; self.players[pid]=Player(pid,f'BOT {i+1:02}',ready=True,bot=True)
            if self.team_size==4:
                human_teams=[p.team for p in self.players.values() if not p.bot]
                self.players[pid].team=max(human_teams,default=1)+1+i//4
        if self.team_size==1:
            for p in self.players.values():p.team=p.id
        points=self.spawns[:]; self.rng.shuffle(points)
        # Small parties share a central encounter area, with room to prepare.
        # Fifty-player rounds use the full district.
        if len(self.players)<=10:
            radius=65 if len(self.players)<=4 else 95
            central=[p for p in points if p[0]*p[0]+p[2]*p[2]<=radius**2]
            if len(central)>=len(self.players):points=central
        chosen=[points.pop()]
        while len(chosen)<len(self.players):
            pos=max(points,key=lambda pos:min((pos[0]-q[0])**2+(pos[2]-q[2])**2 for q in chosen))
            chosen.append(pos);points.remove(pos)
        if self.team_size==4:
            available=chosen+points;assigned={};team_bases={}
            for player in self.players.values():
                if player.team not in team_bases:
                    base=max(available,key=lambda q:min(((q[0]-v[0])**2+(q[2]-v[2])**2 for v in team_bases.values()),default=1))
                    team_bases[player.team]=base
                base=team_bases[player.team]
                pos=min(available,key=lambda q:(q[0]-base[0])**2+(q[2]-base[2])**2)
                assigned[player.id]=pos;available.remove(pos)
            chosen=[assigned[p.id] for p in self.players.values()];points=available
        for p,pos in zip(self.players.values(),chosen):
            p.mover=Mover(self.physics,pos); p.hp=100; p.armor=0; p.alive=True; p.kills=0
            p.inventory=['pistol']; p.weapon='pistol'; p.ammo={'pistol':12}; p.reserve=72; p.meds=1
            p.next_fire=p.reload_until=p.heal_until=0; p.controls={}
            p.medical=starting_medical();p.heal_kind='';p.boost=0
            p.damage_dealt=p.headshots=p.shots=p.rank=p.survived=0
            p.route=[];p.route_at=0
            if p.bot: p.inventory+=['rifle']; p.weapon='rifle'; p.ammo['rifle']=30; p.reserve=999
        kinds=['rifle','smg','shotgun','dmr','ammo','ammo','bandage','firstaid','medkit','energy','painkiller','armor1','armor2']
        self.items={i:dict(id=i,kind=kinds[i%len(kinds)],pos=pos) for i,pos in enumerate((chosen+points)[:180])}
        self.zone=Zone(self.rng.randrange(1000000)); self.now=0; self.zone_damage_at=0
        self.training=len({p.team for p in self.players.values()})==1; self.phase='playing'; self.tick=0; self.winner=None
        self.round_id+=1
        self.next_item=max(self.items,default=0)+1
        self.emit('started',map='drive_city',round=self.round_id,training=self.training,items=list(self.items.values()))

    def return_lobby(self):
        self.players={i:p for i,p in self.players.items() if not p.bot}
        for p in self.players.values(): p.ready=False; p.alive=True; p.hp=100; p.mover=None
        self.phase='lobby'; self.items={}; self.winner=None
        self.emit('returned')

    def damage(self, victim, damage, killer=None, head=False, source='zone'):
        if not victim.alive or (source=='shot' and killer and killer.team==victim.team): return
        blocked=min(victim.armor,damage*.5) if source=='shot' else 0
        actual=min(victim.hp,max(0,damage-blocked))
        victim.armor-=blocked; victim.hp=max(0,victim.hp-actual); victim.heal_until=0;victim.heal_kind=''
        if killer and killer!=victim:
            killer.damage_dealt+=actual
            if head:killer.headshots+=1
        self.emit('damage',victim=victim.id,attacker=killer.id if killer else None,head=head,amount=round(actual),source=source,
                  origin=list(killer.mover.pos) if killer and killer.mover else None)
        if victim.hp<=0:
            victim.alive=False; victim.controls={}
            remaining_teams={p.team for p in self.players.values() if p.alive}
            victim.rank=0 if victim.team in remaining_teams else 1+len(remaining_teams);victim.survived=self.now
            if victim.rank:
                for member in self.players.values():
                    if member.team==victim.team:member.rank=victim.rank
            if killer and killer!=victim: killer.kills+=1
            drops=[]
            contents=[(k,1) for k in victim.inventory]+[('ammo',victim.reserve)]
            contents += [(k,n) for k,n in victim.medical.items() if n>0]
            if victim.armor>0:contents.append(('armor2' if victim.armor>50 else 'armor1',1))
            for index,(kind,amount) in enumerate(contents):
                if amount<=0:continue
                angle=index*2.399;offset=Vec3(math.sin(angle)*(.35+.10*index),0,math.cos(angle)*(.35+.10*index))
                pos=victim.mover.pos+offset
                # Keep drops on the victim's floor; don't push them through walls.
                if self.physics.ray(victim.mover.pos+Vec3(0,.4,0),pos+Vec3(0,.4,0)):pos=victim.mover.pos
                item=dict(id=self.next_item,kind=kind,pos=list(pos),amount=amount)
                self.next_item+=1;self.items[item['id']]=item;drops.append(item)
            self.emit('death',victim=victim.id,name=victim.name,killer=killer.name if killer else '자기장',head=head,
                      pos=list(victim.mover.pos),yaw=victim.yaw,weapon=victim.weapon,drops=drops,
                      stats=victim.stats(self.now),total=len(self.players))

    def fire(self,p):
        w=WEAPONS[p.weapon]
        if not p.alive or self.phase!='playing' or self.now+1e-5<p.next_fire or p.reload_until>self.now or p.heal_until>self.now or p.ammo.get(p.weapon,0)<=0: return False
        p.ammo[p.weapon]-=1;p.shots+=1; p.next_fire=max(p.next_fire+1/w.rate,self.now+1/w.rate-.016)
        origin=p.mover.pos+Vec3(0,Mover.CROUCH_EYE if p.mover.crouch else Mover.EYE,0)
        forward=direction(p.yaw,p.pitch)
        # Camera -> muzzle check prevents a long barrel shooting through a nearby wall.
        muzzle=origin+forward*.65+Vec3(0,-.12,0)
        blocked=self.physics.ray(origin,muzzle)
        impacts=[]; hit_ids=[];hit_details=[];surfaces=[]
        for _ in range(w.pellets):
            spread=w.spread*(.28 if p.controls.get('ads') else 1)
            d=Vec3(forward.x+self.rng.gauss(0,spread),forward.y+self.rng.gauss(0,spread),forward.z+self.rng.gauss(0,spread)); d.normalize()
            surface=blocked or self.physics.ray(origin,origin+d*w.range)
            wall=(surface[0]-origin).length() if surface else w.range
            best=wall; victim=None; head=False;part='body'
            for other in self.players.values():
                if other.id==p.id or other.team==p.team or not other.alive: continue
                pos=other.mover.pos
                height=Mover.CROUCH_EYE if other.mover.crouch else Mover.EYE
                for center,radius,zone in ((pos+Vec3(0,height,0),.28,'head'),(pos+Vec3(0,height*.58,0),.50,'body'),(pos+Vec3(0,.42,0),.38,'leg')):
                    t=ray_sphere(origin,d,center,radius)
                    if t is not None and t<best: best=t; victim=other;head=zone=='head';part=zone
            if victim:
                self.damage(victim,w.damage*{'head':1.8,'body':1.,'leg':.65}[part],p,head,'shot');hit_ids.append(victim.id)
                hit_details.append(dict(id=victim.id,part=part,pos=list(origin+d*best)))
            elif surface:
                normal=Vec3(surface[1])
                if normal.dot(d)>0:normal=-normal
                surfaces.append(dict(pos=list(surface[0]),normal=list(normal)))
            if not impacts: impacts.append(list(surface[0] if surface and not victim else origin+d*best))
        self.emit('shot',id=p.id,weapon=p.weapon,origin=list(origin),impact=impacts[0],hits=hit_ids,hit_details=hit_details,surfaces=surfaces)
        return True

    def action(self,p,kind,**data):
        if self.phase!='playing' or not p.alive: return
        if kind=='reload' and not p.reload_until and p.reserve>0 and p.ammo.get(p.weapon,0)<WEAPONS[p.weapon].magazine:
            p.reload_until=self.now+WEAPONS[p.weapon].reload; p.heal_until=0
        elif kind=='switch' and data.get('weapon') in p.inventory:
            p.weapon=data['weapon']; p.reload_until=0; p.heal_until=0
        elif kind=='heal' and not p.heal_until:
            selected=data.get('item')
            if selected is None:
                selected=next((k for k in ('firstaid','bandage','medkit','energy','painkiller') if p.medical.get(k,0)>0 and ((MEDICAL[k]['heal'] and p.hp<MEDICAL[k]['cap']) or (MEDICAL[k]['boost'] and p.boost<100))),None)
            spec=MEDICAL.get(selected)
            if spec and p.medical.get(selected,0)>0 and ((spec['heal'] and p.hp<spec['cap']) or (spec['boost'] and p.boost<100)):
                p.heal_kind=selected;p.heal_until=self.now+spec['seconds'];p.reload_until=0
        elif kind=='cancel':p.heal_until=0;p.heal_kind=''
        elif kind=='pickup':
            item=self.items.get(data.get('item'))
            if not item or (p.mover.pos-Vec3(*item['pos'])).length()>2.8: return
            if self.physics.ray(p.mover.pos+Vec3(0,.6,0),Vec3(*item['pos'])+Vec3(0,.4,0)): return
            k=item['kind']
            if k in WEAPONS:
                if k not in p.inventory: p.inventory.append(k); p.ammo[k]=WEAPONS[k].magazine
                else: p.reserve+=WEAPONS[k].magazine
                p.weapon=k; p.reload_until=0
            elif k=='ammo': p.reserve+=item.get('amount',60)
            elif k in MEDICAL:
                p.medical[k]=p.medical.get(k,0)+item.get('amount',1);p.meds=sum(p.medical.values())
            else: p.armor=max(p.armor,50 if k=='armor1' else 100)
            del self.items[item['id']]
            self.emit('pickup',item=item['id'],player=p.id,item_kind=k)

    def bot_input(self,p):
        if self.now<p.brain_at: return
        p.brain_at=self.now+.18+self.rng.random()*.08
        enemies=[o for o in self.players.values() if o.team!=p.team and o.alive]
        target=min(enemies,key=lambda o:(o.mover.pos-p.mover.pos).lengthSquared()) if enemies else p
        delta=target.mover.pos-p.mover.pos; dist=delta.length()
        visible=bool(enemies) and .1<dist<95 and self.physics.distance(p.mover.pos+Vec3(0,Mover.EYE,0),delta.normalized(),dist)>dist-.5
        center=Vec3(self.zone.next_center[0],p.mover.pos.y,self.zone.next_center[1])
        to_safe=max(0,(center-p.mover.pos).length()-self.zone.next_radius+12)
        state=self.zone.state()
        evacuate=self.zone.outside(p.mover.pos) or (to_safe>0 and (state['shrinking'] or state['remaining']<to_safe/4+25))
        if visible and not evacuate:
            yaw=math.degrees(math.atan2(delta.x,delta.z))+self.rng.uniform(-3,3)
            pitch=-math.degrees(math.atan2(delta.y,max(.1,math.hypot(delta.x,delta.z))))+self.rng.uniform(-2,2)
            p.controls=dict(move=[self.rng.choice([-.5,.5]),.5 if dist>22 else 0],yaw=yaw,pitch=pitch,fire=self.now>8 and (self.now+p.id)%2.8>1.,ads=True)
        else:
            goal=center if evacuate or not enemies or self.zone.outside(target.mover.pos) else target.mover.pos
            if self.now>=p.route_at or not p.route:
                p.route=self.navigation.route(p.mover.pos,goal);p.route_at=self.now+3+self.rng.random()
            while len(p.route)>1 and (Vec3(*p.route[0])-p.mover.pos).length()<1.5:p.route.pop(0)
            waypoint=Vec3(*p.route[0]) if p.route else goal
            delta=waypoint-p.mover.pos;yaw=math.degrees(math.atan2(delta.x,delta.z))
            blocked=self.physics.distance(p.mover.pos+Vec3(0,.8,0),direction(yaw,0),1.4)<1.1
            if blocked:
                candidates=[yaw+s for s in (-90,-55,55,90,150)]
                yaw=max(candidates,key=lambda a:self.physics.distance(p.mover.pos+Vec3(0,.8,0),direction(a,0),3))
                p.route_at=min(p.route_at,self.now+.5)
            p.controls=dict(move=[0,1 if delta.length()>1 else 0],yaw=yaw,pitch=0,fire=False,sprint=True,jump=False)
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
            if p.heal_until and (p.controls.get('jump') or p.controls.get('sprint') or p.mover.velocity.length()>1):
                p.heal_until=0;p.heal_kind=''
            if p.mover.pos.y < -15: self.damage(p,1000,source='fall')
            if p.reload_until and self.now>=p.reload_until:
                amount=min(WEAPONS[p.weapon].magazine-p.ammo.get(p.weapon,0),p.reserve)
                p.ammo[p.weapon]=p.ammo.get(p.weapon,0)+amount; p.reserve-=amount; p.reload_until=0
            if p.heal_until and self.now>=p.heal_until:
                spec=MEDICAL[p.heal_kind]
                p.hp=max(p.hp,min(spec['cap'],p.hp+spec['heal'])) if spec['heal'] else p.hp
                p.boost=min(100,p.boost+spec['boost']);p.medical[p.heal_kind]-=1
                p.meds=sum(p.medical.values());p.heal_until=0;p.heal_kind=''
            if p.boost>0:
                p.hp=min(100,p.hp+dt*(.7 if p.boost>60 else .35));p.boost=max(0,p.boost-dt*.3)
            if p.controls.get('fire'): self.fire(p)
        if self.now>=self.zone_damage_at:
            self.zone_damage_at=self.now+1
            for p in self.players.values():
                if p.alive and self.zone.outside(p.mover.pos): self.damage(p,2+self.zone.stage*2)
        alive=[p for p in self.players.values() if p.alive]
        alive_teams={p.team for p in alive}
        if len(alive)==0 or (len(alive_teams)==1 and not self.training):
            self.phase='finished'; self.winner=alive[0].id if alive else None
            if alive:
                for p in self.players.values():
                    if p.team==alive[0].team:p.rank=1
                    if p.alive:p.survived=self.now
            self.emit('finished',winner=self.winner,name=alive[0].name if alive else 'NO SURVIVOR',total=len(self.players),
                      team=alive[0].team if alive else None,results={str(p.id):p.stats(self.now) for p in self.players.values()})

    def snapshot(self):
        return [[p.id,*[round(v,3) for v in p.mover.pos],round(p.yaw,1),round(p.pitch,1),round(p.hp),round(p.armor),p.alive,p.mover.crouch,p.weapon] for p in self.players.values() if p.mover]
