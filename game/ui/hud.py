import math
from ursina import *
from game.ui.screens import INK,TEAL,MUTED,ORANGE,PANEL
from game.weapons import WEAPONS

class HUD:
    def __init__(self,app):
        self.app=app; self.root=Entity(parent=camera.ui); self.feed=[]
        self.health_bg=Entity(parent=self.root,model='quad',position=(-.65,-.407),scale=(.29,.065),color=color.rgba(10,20,30,225))
        self.hpbar=Entity(parent=self.root,model='quad',origin=(-.5,0),position=(-.782,-.435),scale=(.26,.007),color=TEAL)
        self.hp=Text(parent=self.root,position=(-.78,-.388),scale=1.2)
        self.armor=Text(parent=self.root,position=(-.78,-.46),scale=.63,color=MUTED)
        self.ammo=Text(parent=self.root,position=(.49,-.385),scale=1.7)
        self.weapon=Text(parent=self.root,position=(.49,-.351),scale=.67,color=TEAL)
        self.status=Text(parent=self.root,position=(-.13,.45),scale=.86)
        self.zone_text=Text(parent=self.root,position=(-.79,.45),scale=.75,color=INK)
        self.prompt=Text(parent=self.root,position=(0,-.17),origin=(0,0),scale=.85,color=ORANGE)
        self.cross=Text('+',parent=self.root,origin=(0,0),scale=1.3,color=INK)
        self.hit=Text('×',parent=self.root,origin=(0,0),scale=2,color=ORANGE,enabled=False)
        self.flash=Entity(parent=self.root,model='quad',scale=(2,1),color=color.rgba(210,40,25,0),z=-.01)
        self.feed_text=Text(parent=self.root,position=(.38,.21),scale=.64,color=INK)
        self.help=Text('WASD 이동   SHIFT 달리기   SPACE 점프   C 앉기\nE 줍기   R 장전   H 회복   1–5 무기   TAB 생존자   ESC 메뉴',parent=self.root,position=(-.79,-.49),scale=.52,color=MUTED)
        self.debug=Text(parent=self.root,position=(-.79,.25),scale=.6,color=TEAL,enabled=False)
        self.score=Text(parent=self.root,position=(-.16,.32),scale=.8,enabled=False)
        self.map_root=Entity(parent=self.root,position=(.687,.334),scale=.23)
        Entity(parent=self.map_root,model='quad',scale=(1.14,1.14),color=color.rgba(9,19,29,230))
        self.outer=self.circle(TEAL); self.next=self.circle(color.rgba(230,240,250,150))
        self.dot=Entity(parent=self.map_root,model='circle',scale=.04,color=ORANGE,z=-.01)
        self.damage_direction=Text('',parent=self.root,position=(0,.16),origin=(0,0),scale=.8,color=ORANGE)
        self.result=None; self.pause=None; self.last_hit=0; self.damage_timer=0

    def circle(self,tint):
        vertices=[(math.cos(i*math.tau/64)*.5,math.sin(i*math.tau/64)*.5,0) for i in range(65)]
        return Entity(parent=self.map_root,model=Mesh(vertices=vertices,mode='line',thickness=2),color=tint)

    def event(self,p):
        if p['t']=='death':
            self.feed.append(f"{p['killer']}  ›  {p['name']}{'  HEAD' if p['head'] else ''}")
            self.feed=self.feed[-5:]; self.feed_text.text='\n'.join(self.feed)
        if p['t']=='damage' and p['victim']==self.app.connection.id:
            self.damage_timer=.5
            attacker=self.app.avatars.get(p.get('attacker'))
            if attacker and self.app.mover:
                d=attacker.position-self.app.mover.pos
                angle=(math.degrees(math.atan2(d.x,d.z))-self.app.yaw+180)%360-180
                self.damage_direction.text='◀ 왼쪽 피격' if angle<-35 else ('오른쪽 피격 ▶' if angle>35 else '▲ 정면 피격')
            else: self.damage_direction.text='자기장 피해' if p.get('source')=='zone' else '피격'
        if p['t']=='shot' and p['id']==self.app.connection.id and p['hits']:
            self.last_hit=.16; self.hit.enabled=True

    def update(self,dt):
        a=self.app; own=a.own; p=a.players.get(a.connection.id,{})
        hp=p.get('hp',100); armor=p.get('armor',0)
        self.hp.text=f'{hp:03}  HP'; self.hpbar.scale_x=.26*hp/100
        self.armor.text=f'ARMOR {armor:03}     회복 {own.get("meds",0)} [H]'
        weapon=own.get('weapon','pistol'); ammo=own.get('ammo',{}).get(weapon,0)
        self.weapon.text=WEAPONS[weapon].name; self.ammo.text=f'{ammo:02} / {own.get("reserve",0)}'
        if own.get('reload',0)>0: self.weapon.text=f'RELOADING  {own["reload"]:.1f}s'
        if own.get('heal',0)>0: self.weapon.text=f'HEALING  {own["heal"]:.1f}s'
        self.status.text=f'ALIVE  {sum(p.get("alive",False) for p in a.players.values()):02}     KILLS  {p.get("kills",0):02}'
        z=a.zone
        if z:
            self.zone_text.text=f'ZONE {z["stage"]+1:02}  /  {"축소 중" if z["shrinking"] else "축소까지"} {z["remaining"]:.0f}s\n안전구역 반경 {z["radius"]:.0f}m'
            for circle,center,radius in ((self.outer,z['center'],z['radius']),(self.next,z['next'],z['next_radius'])):
                circle.position=(center[0]/420,center[1]/420,0); circle.scale=radius*2/420
            if a.mover:
                self.dot.position=(a.mover.pos.x/420,a.mover.pos.z/420,-.01)
                if math.hypot(a.mover.pos.x-z['center'][0],a.mover.pos.z-z['center'][1])>z['radius']:
                    self.zone_text.color=ORANGE
                else: self.zone_text.color=INK
        self.last_hit-=dt; self.hit.enabled=self.last_hit>0
        self.damage_timer=max(0,self.damage_timer-dt); self.flash.color=color.rgba(200,25,10,int(self.damage_timer*110))
        self.damage_direction.enabled=self.damage_timer>0
        self.debug.enabled=a.debug
        if a.debug and a.mover:
            m=a.mover; c=a.connection
            slope=math.degrees(math.acos(max(-1,min(1,m.normal.y))))
            self.debug.text=f'FPS {1/max(.001,dt):.0f}  CLIENT {c.id}  HOST {bool(a.host)}\nPOS {m.pos.x:.1f} {m.pos.y:.2f} {m.pos.z:.1f}\nVEL {m.velocity.length():.1f}  GROUNDED {m.grounded}\nNORMAL {m.normal.x:.2f} {m.normal.y:.2f} {m.normal.z:.2f} / {slope:.1f}°\nPING {c.ping:.1f}ms  TICK {c.tick}\nPACKETS TX {c.tx} RX {c.rx} LOSS~ {c.lost}\nF2 COLLIDERS  F3 SHOT RAYS'
        self.score.enabled=bool(held_keys['tab'])
        if self.score.enabled: self.score.text='\n'.join(f"{p['name']}  {'ALIVE' if p['alive'] else 'OUT'}  {p['kills']} K" for p in list(a.players.values())[:25])

    def finished(self,p):
        self.result=Entity(parent=self.root)
        Entity(parent=self.result,model='quad',scale=(1.15,.4),color=color.rgba(8,17,26,245))
        Text('WINNER' if p['winner']==self.app.connection.id else 'ROUND COMPLETE',parent=self.result,origin=(0,0),y=.12,scale=2,color=TEAL)
        Text(p['name'],parent=self.result,origin=(0,0),y=.035,scale=1.5)
        label='대기실로 돌아가기' if self.app.host else '방장이 대기실로 돌아가기를 기다리는 중'
        b=Button(parent=self.result,text=label,y=-.09,scale=(.65,.06),color=PANEL)
        b.on_click=lambda:self.app.connection.send('return') if self.app.host else None
        mouse.locked=False; mouse.visible=True

    def destroy(self): destroy(self.root)
