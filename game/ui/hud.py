import math
from ursina import *
from game.ui.screens import INK,TEAL,MUTED,ORANGE,PANEL
from game.weapons import WEAPONS
from game.ui.inventory import Inventory
from game.items import MEDICAL
from game.ui.style import vignette,GOLD
from game.ui.map_navigation import MapNavigation
from game.ui.combat_widgets import zone_overlay,DamageCompass,show_result

class HUD:
    def __init__(self,app):
        self.app=app; self.root=Entity(parent=camera.ui); self.feed=[]
        self.combat=Entity(parent=self.root)
        vignette(self.combat,.45)
        self.hp_trail=100.;self.damage=DamageCompass(self.combat,app)
        self.health_bg=Entity(parent=self.combat,model='quad',position=(0,-.435),scale=(.52,.020),color=color.rgba32(30,35,39,155))
        self.hpghost=Entity(parent=self.combat,model='quad',origin=(-.5,0),position=(-.257,-.435),scale=(.514,.014),color=color.rgba32(185,42,32,200))
        self.hpbar=Entity(parent=self.combat,model='quad',origin=(-.5,0),position=(-.257,-.435),scale=(.514,.014),color=color.hex('#f4f1e8'))
        for i in range(1,4):Entity(parent=self.combat,model='quad',position=(-.26+i*.13,-.435),scale=(.001,.018),color=color.rgba32(20,25,28,110))
        self.boostbar=Entity(parent=self.combat,model='quad',origin=(-.5,0),position=(-.257,-.419),scale=(.001,.003),color=GOLD)
        self.hp=Text(parent=self.combat,position=(.28,-.424),scale=.85)
        self.armor=Text(parent=self.combat,position=(-.255,-.464),scale=.59,color=INK)
        self.ammo=Text(parent=self.combat,position=(.11,-.364),scale=1.85,origin=(.5,0))
        self.weapon=Text(parent=self.combat,position=(-.255,-.365),scale=.8,color=INK)
        self.slots=Text(parent=self.combat,position=(-.255,-.397),scale=.57,color=MUTED)
        self.compass=Text(parent=self.combat,position=(0,.46),origin=(0,0),scale=.85,color=INK)
        self.team_text=Text(parent=self.combat,position=(-.83,-.25),scale=.72,line_height=1.6,color=INK)
        self.use_label=Text(parent=self.combat,position=(0,-.23),origin=(0,0),scale=.82,color=GOLD)
        self.use_bar=Entity(parent=self.combat,model='quad',origin=(-.5,0),position=(-.11,-.26),scale=(.001,.003),color=GOLD,enabled=False)
        self.status=Text(parent=self.combat,position=(.58,.46),scale=.74)
        self.zone_text=Text(parent=self.combat,position=(-.83,.46),scale=.75,color=INK)
        self.prompt=Text(parent=self.combat,position=(0,-.17),origin=(0,0),scale=.85,color=ORANGE)
        self.cross=Text('+',parent=self.combat,origin=(0,0),scale=1,color=INK,z=-.025)
        self.hit=Text('×',parent=self.combat,origin=(0,0),scale=2,color=ORANGE,enabled=False)
        self.flash=Entity(parent=self.combat,model='quad',scale=(2,1),color=color.rgba32(210,40,25,0),z=-.01)
        self.feed_text=Text(parent=self.combat,position=(.38,.21),scale=.64,color=INK)
        self.help=Text('F 줍기   R 장전   H 회복   TAB 소지품',parent=self.combat,position=(-.83,-.472),scale=.51,color=MUTED)
        self.debug=Text(parent=self.combat,position=(-.79,.25),scale=.6,color=TEAL,enabled=False)
        self.score=Text(parent=self.combat,position=(-.16,.32),scale=.8,enabled=False)
        self.score_right=Text(parent=self.combat,position=(.15,.32),scale=.8,enabled=False)
        self.map_root=Entity(parent=self.combat,position=(.70,-.30),scale=.23)
        Entity(parent=self.map_root,model='quad',scale=(1.08,1.22),color=color.rgba32(16,17,19,235),z=.02)
        Entity(parent=self.map_root,model='quad',texture='minimap.png',scale=1,color=color.white,z=.01)
        Text('N',parent=self.map_root,position=(0,.57),origin=(0,0),scale=2.2,color=TEAL)
        Text('DRIVE CITY  /  [M]',parent=self.map_root,position=(-.49,-.535),scale=1.9,color=INK)
        self.map_shade=zone_overlay(self.map_root)
        self.outer=self.circle(color.azure); self.next=self.circle(INK)
        self.dot=Entity(parent=self.map_root,model=Mesh(vertices=[(0,.7,0),(-.4,-.4,0),(0,-.2,0),(.4,-.4,0)],triangles=[0,1,2,0,2,3]),scale=.065,color=ORANGE,z=-.03,double_sided=True)
        self.dot.setDepthTest(False);self.dot.setBin('fixed',60)
        Entity(parent=self.dot,model=Mesh(vertices=list(self.dot.model.vertices),triangles=list(self.dot.model.triangles)),scale=1.35,z=.003,color=color.black,double_sided=True).setBin('fixed',59)
        self.map_nav=MapNavigation();self.map_drag=None
        self.mini_marker=Text('◆',parent=self.map_root,origin=(0,0),scale=3,color=color.cyan,z=-.035,enabled=False)
        self.waypoint_label=Text(parent=self.combat,position=(.60,-.16),scale=.6,color=color.cyan)
        self.tactical=Entity(parent=self.combat,enabled=False,z=-.1)
        Entity(parent=self.tactical,model='quad',scale=(2,1.1),color=color.rgba32(10,11,13,247),z=.02)
        Text('LANFALL',parent=self.tactical,position=(-.79,.44),scale=1.4,color=TEAL)
        Text('TACTICAL MAP',parent=self.tactical,position=(-.79,.385),scale=.68,color=MUTED)
        Text('01 / DRIVE CITY\n\nSOUTH DISTRICT\n420 × 420 m',parent=self.tactical,position=(.49,.35),scale=.7,color=INK)
        Text('파란 영역  자기장 피해\n흰 원       다음 안전구역\n금색 표식  내 위치\n\n휠         확대 / 축소\n좌클릭    목적지 지정\n우클릭    표식 지우기\n휠 누르고 끌기  이동\nM / ESC   지도 닫기',parent=self.tactical,position=(.49,-.17),scale=.65,color=MUTED)
        self.map_viewport=Entity(parent=self.tactical,scale=.79,position=(-.035,-.012))
        self.map_viewport.setScissor(Vec3(-.5,-.5,0),Vec3(.5,.5,0))
        self.large_root=Entity(parent=self.map_viewport)
        self.large_marker=Text('◆',parent=self.large_root,origin=(0,0),scale=1,color=color.cyan,z=-.035,enabled=False)
        Entity(parent=self.large_root,model='quad',texture='minimap.png',z=.01)
        self.large_shade=zone_overlay(self.large_root)
        self.large_outer=self.circle(color.azure,self.large_root);self.large_next=self.circle(INK,self.large_root)
        self.large_dot=Entity(parent=self.large_root,model=Mesh(vertices=list(self.dot.model.vertices),triangles=list(self.dot.model.triangles)),scale=.025,color=ORANGE,z=-.03,double_sided=True)
        self.large_dot.setDepthTest(False);self.large_dot.setBin('fixed',61)
        Entity(parent=self.large_dot,model=Mesh(vertices=list(self.dot.model.vertices),triangles=list(self.dot.model.triangles)),scale=1.3,z=.003,color=color.black,double_sided=True).setBin('fixed',60)
        for i in range(7):
            f=i/6-.5
            for vertices in [[(f,-.5,0),(f,.5,0)],[(-.5,f,0),(.5,f,0)]]:
                Entity(parent=self.large_root,model=Mesh(vertices=vertices,mode='line'),color=color.rgba32(240,238,220,35))
            if i<6:
                Text(chr(65+i),parent=self.large_root,position=(f+1/12,.517),origin=(0,0),scale=.75,color=MUTED)
                Text(str(i+1),parent=self.large_root,position=(-.523,.5-i/6-1/12),origin=(0,0),scale=.75,color=MUTED)
        self.map_timer=Text(parent=self.tactical,position=(-.79,.30),scale=.69,color=INK)
        self.damage_direction=Text('',parent=self.combat,position=(0,.16),origin=(0,0),scale=.8,color=ORANGE)
        self.result=None; self.pause=None; self.last_hit=0; self.damage_timer=0
        self.inventory=Inventory(app,self.combat)
        self.optic=Entity(parent=self.combat,enabled=False,z=-.03)
        for verts in [[(-.022,0,0),(-.005,0,0)],[(.005,0,0),(.022,0,0)],[(0,-.022,0),(0,-.005,0)]]:
            Entity(parent=self.optic,model=Mesh(vertices=verts,mode='line',thickness=1.4),color=color.rgba32(25,30,28,220))
        Entity(parent=self.optic,model='quad',scale=.0022,color=color.red)
        self.zoom_label=Text(parent=self.combat,position=(0,-.34),origin=(0,0),scale=.7,color=INK)

    def circle(self,tint,parent=None):
        vertices=[(math.cos(i*math.tau/64)*.5,math.sin(i*math.tau/64)*.5,0) for i in range(65)]
        return Entity(parent=parent or self.map_root,model=Mesh(vertices=vertices,mode='line',thickness=2),color=tint)

    def toggle_map(self):
        self.tactical.enabled=not self.tactical.enabled
        self.map_drag=None
        return self.tactical.enabled

    def map_input(self,key):
        x=(mouse.x+.035)/.79;y=(mouse.y+.012)/.79
        if key=='middle mouse up':self.map_drag=None
        if abs(x)>.5 or abs(y)>.5:return
        if key in ('scroll up','scroll down'):
            self.map_nav.zoom_at(x,y,1.25 if key=='scroll up' else .8)
        elif key=='left mouse down':self.map_nav.marker=self.map_nav.world_at(x,y)
        elif key=='right mouse down':self.map_nav.marker=None
        elif key=='middle mouse down':self.map_drag=(mouse.x,mouse.y)

    def update_map(self):
        nav=self.map_nav
        self.map_root.enabled=not self.tactical.enabled
        self.waypoint_label.enabled=not self.tactical.enabled
        if self.tactical.enabled and self.map_drag is not None:
            x,y=self.map_drag;nav.pan((mouse.x-x)/.79,(mouse.y-y)/.79)
            self.map_drag=(mouse.x,mouse.y)
        self.large_root.scale=nav.zoom
        self.large_root.position=(-nav.center[0]*nav.zoom,-nav.center[1]*nav.zoom,0)
        self.large_dot.scale=.025/nav.zoom
        self.large_marker.scale=1/nav.zoom
        for marker in (self.mini_marker,self.large_marker):
            marker.enabled=nav.marker is not None
            if nav.marker:marker.position=(nav.marker[0]/420,nav.marker[1]/420,-.035)
        self.waypoint_label.text=''
        if self.app.mover:
            p=self.app.mover.pos
            if self.app.spectate_target in self.app.avatars and not self.app.players.get(self.app.connection.id,{}).get('alive',True):
                p=self.app.avatars[self.app.spectate_target].position
            self.dot.position=(p.x/420,p.z/420,-.03);self.large_dot.position=self.dot.position
            self.dot.rotation_z=-camera.rotation_y;self.large_dot.rotation_z=-camera.rotation_y
            if nav.marker:self.waypoint_label.text=f'◆ 목적지  {math.hypot(p.x-nav.marker[0],p.z-nav.marker[1]):.0f} m'

    def event(self,p):
        if p['t']=='death':
            self.feed.append(f"{p['killer']}  ›  {p['name']}{'  HEAD' if p['head'] else ''}")
            self.feed=self.feed[-5:]; self.feed_text.text='\n'.join(self.feed)
        if p['t']=='damage' and p['victim']==self.app.connection.id:
            self.damage_timer=1.2
            self.damage.register(p.get('origin'),True)
        if p['t']=='shot' and p['id']!=self.app.connection.id:
            origin=Vec3(*p['origin'])
            if (origin-camera.world_position).length()<120:self.damage.register(p['origin'],False)
        if p['t']=='shot' and p['id']==self.app.connection.id and p['hits']:
            self.last_hit=.16; self.hit.enabled=True

    def update(self,dt):
        self.update_map()
        a=self.app; own=a.own; p=a.players.get(a.connection.id,{})
        if not p.get('alive',True) and a.spectate_target in a.players:
            p=a.players[a.spectate_target]
            if a.watch_state.get('id')==a.spectate_target:own=a.watch_state['own']
        aiming=a.ads and not a.paused and not a.finished and p.get('alive',True) and not self.tactical.enabled and not self.inventory.enabled and not own.get('reload',0)
        self.optic.enabled=aiming
        self.zoom_label.enabled=aiming;self.zoom_label.text=f'{a.zoom:.1f}x   |   우클릭 해제 · 휠 배율'
        if self.inventory.enabled:self.inventory.refresh()
        hp=p.get('hp',100); armor=p.get('armor',0)
        self.hp.text=f'{hp:03}'; self.hpbar.scale_x=.514*hp/100
        self.hpbar.color=color.hex('#e65a48') if hp<30 else color.hex('#f4f1e8')
        self.hp_trail=lerp(self.hp_trail,hp,min(1,dt*3));self.hpghost.scale_x=.514*self.hp_trail/100
        self.boostbar.scale_x=.514*own.get('boost',0)/100
        directions=['N','NE','E','SE','S','SW','W','NW'];bearing=camera.rotation_y%360
        self.compass.text=f'{directions[int((bearing+22.5)//45)%8]}     {bearing:03.0f}°'
        team=p.get('team');self.team_text.text='\n'.join(f'{i+1}  {q["name"][:14]}   {q["hp"] if q["alive"] else "OUT"}' for i,q in enumerate(a.players.values()) if q.get('team')==team) if a.lobby_data.get('team_size')==4 else ''
        self.damage.update(dt)
        self.armor.text=f'방탄복 {armor:03}   |   회복템 {sum(own.get("medical",{}).values()):02}   |   부스트 {own.get("boost",0):.0f}%'
        self.slots.text='   /   '.join(f'{list(WEAPONS).index(k)+1} {WEAPONS[k].name.split(" /")[0]}' for k in own.get('inventory',[]))
        weapon=own.get('weapon','pistol'); ammo=own.get('ammo',{}).get(weapon,0)
        self.weapon.text=WEAPONS[weapon].name; self.ammo.text=f'{ammo:02} / {own.get("reserve",0)}'
        if own.get('reload',0)>0: self.weapon.text=f'RELOADING  {own["reload"]:.1f}s'
        heal=own.get('heal',0);spec=MEDICAL.get(own.get('heal_kind'),{})
        self.use_label.text=f'{spec.get("name","회복")} 사용 중  {heal:.1f}s   [X 취소]' if heal else ''
        self.use_bar.enabled=heal>0
        if heal:self.use_bar.scale_x=.22*(1-heal/spec.get('seconds',8))
        self.status.text=f'ALIVE  {sum(p.get("alive",False) for p in a.players.values()):02}     KILLS  {p.get("kills",0):02}'
        z=a.zone
        if z:
            for overlay in (self.map_shade,self.large_shade):
                overlay.set_shader_input('safe_center',Vec2(z['center'][0]/420+.5,z['center'][1]/420+.5));overlay.set_shader_input('safe_radius',float(z['radius']/420))
            self.zone_text.text=f'ZONE {z["stage"]+1:02}  /  {"축소 중" if z["shrinking"] else "축소까지"} {z["remaining"]:.0f}s\n안전구역 반경 {z["radius"]:.0f}m'
            self.map_timer.text=f'ZONE {z["stage"]+1:02}\n\n{z["remaining"]:.0f} SEC\n\n안전구역\n{z["radius"]:.0f} m'
            for circle,center,radius in ((self.outer,z['center'],z['radius']),(self.next,z['next'],z['next_radius']),(self.large_outer,z['center'],z['radius']),(self.large_next,z['next'],z['next_radius'])):
                circle.position=(center[0]/420,center[1]/420,0); circle.scale=radius*2/420
            if a.mover:
                if math.hypot(a.mover.pos.x-z['center'][0],a.mover.pos.z-z['center'][1])>z['radius']:
                    self.zone_text.color=ORANGE
                else: self.zone_text.color=INK
        self.last_hit-=dt; self.hit.enabled=self.last_hit>0
        self.damage_timer=max(0,self.damage_timer-dt); self.flash.color=color.rgba32(200,25,10,int(self.damage_timer*110))
        self.damage_direction.enabled=False
        self.debug.enabled=a.debug
        if a.debug and a.mover:
            m=a.mover; c=a.connection
            slope=math.degrees(math.acos(max(-1,min(1,m.normal.y))))
            self.debug.text=f'FPS {1/max(.001,dt):.0f}  CLIENT {c.id}  HOST {bool(a.host)}\nPOS {m.pos.x:.1f} {m.pos.y:.2f} {m.pos.z:.1f}\nVEL {m.velocity.length():.1f}  GROUNDED {m.grounded}\nNORMAL {m.normal.x:.2f} {m.normal.y:.2f} {m.normal.z:.2f} / {slope:.1f}°\nPING {c.ping:.1f}ms  TICK {c.tick}\nPACKETS TX {c.tx} RX {c.rx} LOSS~ {c.lost}\nF2 COLLIDERS  F3 SHOT RAYS'
        self.score.enabled=bool(held_keys['f4'])
        self.score_right.enabled=self.score.enabled
        if self.score.enabled:
            rows=[f"{p['name'][:14]}  {'ALIVE' if p['alive'] else 'OUT'}  {p['kills']} K" for p in a.players.values()]
            self.score.text='\n'.join(rows[:25]);self.score_right.text='\n'.join(rows[25:])

    def finished(self,p):
        show_result(self,p)

    def eliminated(self,p):
        show_result(self,p,eliminated=True)

    def destroy(self):
        if self.pause:
            destroy(self.pause);self.pause=None
        destroy(self.root)
