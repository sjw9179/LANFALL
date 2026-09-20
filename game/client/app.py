import collections
import json
import math
import queue
import socket
import time as clock
from pathlib import Path
from ursina import *
from panda3d.core import Filename,Fog,WindowProperties,NodePath
from game.config import ASSETS,ROOT,GAME_PORT
from game.network.client import Connection
from game.network.discovery import Discovery
from game.server.host import Host
from game.world.physics import CollisionWorld,Mover
from game.ui.screens import Screens,TEAL,PANEL,ORANGE
from game.ui.hud import HUD
from game.weapons import WEAPONS

class Game(Entity):
    def __init__(self,args):
        super().__init__()
        self.args=args; self.started_at=clock.monotonic(); self.connection=None; self.host=None; self.discovery=None
        self.nickname=args.name; self.room_name='LANFALL ROOM'; self.room_code=''; self.capacity=10; self.bot_count=3
        self.lobby_data={}; self.players={}; self.own={}; self.zone={}; self.avatars={}; self.snapshots=collections.deque(maxlen=8)
        self.items={}; self.item_entities={}; self.mover=None; self.yaw=0.; self.pitch=0.; self.hud=None
        self.playing=False; self.finished=False; self.paused=False; self.debug=False; self.show_rays=False
        self.fixed_time=0.; self.browser_at=0.; self.nearest=None; self.weapon_id=''; self.view_gun=None
        self.effects=[]; self.shot_visual_at=0; self.spectate_index=0; self.spectate_label=None
        self.smoke_start=False; self.smoke_shot=False; self.smoke_images=set(); self.frame_times=[]
        self.settings_path=Path.home()/'.lanfall/settings.json'
        self.settings={'quality':'MEDIUM','sensitivity':1.,'volume':.6,'effects':True}
        try: self.settings.update(json.loads(self.settings_path.read_text(encoding='utf8')))
        except (OSError,ValueError): pass
        font=Path('C:/Windows/Fonts/malgun.ttf')
        if font.exists():
            application.fonts_folder=font.parent
            Text.default_font=font.name
        self.physics=CollisionWorld()
        self.map=Entity(model=loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache/city.bam'))))
        self.map.setTwoSided(True)
        self.sky=Sky(color=color.hex('#b1c6d0'))
        self.sun=DirectionalLight(shadows=False); self.sun.look_at(Vec3(1,-2,1))
        self.ambient=AmbientLight(color=color.rgba(175,190,205,255))
        self.sounds={k:Audio(ASSETS/'audio'/f'{k}.ogg',autoplay=False,volume=.35) for k in [*WEAPONS,'hit','reload']}
        self.models={k:loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache'/f'{k}.bam'))) for k in [*WEAPONS,'operator']}
        self.screens=Screens(self); self.screens.main(); self.apply_settings()
        camera.position=(65,85,-105); camera.look_at(Vec3(0,0,25)); camera.fov=84
        self.bg_angle=0
        self.debug_mesh=None
        if args.auto_host or args.smoke:
            self.bot_count=args.bots; self.capacity=max(2,args.bots+1); self.capacity=min(50,self.capacity)
            invoke(self.host_room,delay=.3)
        elif args.join: invoke(Func(self.join_address,args.join,args.name),delay=.3)

    def save_settings(self):
        self.settings_path.parent.mkdir(parents=True,exist_ok=True)
        self.settings_path.write_text(json.dumps(self.settings,indent=2),encoding='utf8')

    def apply_settings(self):
        q=self.settings.get('quality','MEDIUM')
        if q not in ('LOW','MEDIUM','HIGH'): q='MEDIUM'; self.settings['quality']=q
        camera.clip_plane_far={'LOW':150,'MEDIUM':240,'HIGH':400}[q]
        fog=Fog('city haze'); fog.setColor(.62,.72,.77); fog.setLinearRange(camera.clip_plane_far*.45,camera.clip_plane_far)
        scene.setFog(fog)
        self.sun.shadows=q=='HIGH'
        if q=='HIGH':
            from ursina.shaders import lit_with_shadows_shader
            self.map.shader=lit_with_shadows_shader
        else:
            from ursina.shaders import basic_lighting_shader
            self.map.shader=basic_lighting_shader
        for sound in self.sounds.values(): sound.volume=self.settings['volume']*.5
        self.save_settings()

    def host_room(self):
        self.screens.message('도시와 대기실을 준비하는 중…')
        try:
            self.host=Host(CollisionWorld(),self.room_name,self.capacity,self.bot_count,self.room_code,port=self.args.port)
            self.connection=Connection('127.0.0.1',self.host.port,self.nickname,self.room_code,self.host.owner)
        except Exception as e:
            self.screens.message(f'방 생성 실패: {e}'); self.host=None

    def start_discovery(self):
        if not self.discovery: self.discovery=Discovery()

    def join_found(self,room):
        if room.get('locked'):
            self.screens.join_address.text=f"{room['ip']}:{room['port']}#"
            self.screens.message('직접 참가 칸의 # 뒤에 초대 코드를 입력하세요.')
            return
        self.join_address(f"{room['ip']}:{room['port']}",self.screens.join_name.text)

    def join_address(self,address,name):
        try:
            endpoint,_,code=address.strip().partition('#')
            host,sep,port=endpoint.partition(':')
            if not host: raise ValueError('IP 주소를 입력하세요.')
            if self.connection: self.connection.close()
            self.nickname=name.strip()[:24] or 'Player'
            self.connection=Connection(host,int(port) if sep else GAME_PORT,self.nickname,code)
            self.screens.message('접속 중…')
        except (OSError,ValueError) as e: self.screens.message(str(e))

    def copy_invite(self):
        import pyperclip
        ip='127.0.0.1'
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                s.connect(('192.0.2.1',1)); ip=s.getsockname()[0]
        except OSError:
            try: ip=socket.gethostbyname(socket.gethostname())
            except OSError: pass
        port=self.host.port if self.host else self.connection.address[1]
        if not self.host: ip=self.connection.address[0]
        code=self.room_code if self.host else ''
        invite=f'{ip}:{port}'+('#'+code if code else '')
        pyperclip.copy(invite); self.screens.message('복사됨: '+invite)

    def toggle_ready(self):
        mine=next((p for p in self.lobby_data.get('players',[]) if p['id']==self.connection.id),{})
        self.connection.send('ready',ready=not mine.get('ready',False))

    def clear_round(self):
        for e in [*self.avatars.values(),*self.item_entities.values()]: destroy(e)
        self.avatars={}; self.item_entities={}; self.items={}; self.snapshots.clear()
        if self.hud: self.hud.destroy(); self.hud=None
        if self.view_gun: destroy(self.view_gun); self.view_gun=None
        if self.spectate_label: destroy(self.spectate_label); self.spectate_label=None
        self.weapon_id=''; self.mover=None; self.playing=False; self.finished=False; self.paused=False

    def leave(self):
        if self.connection: self.connection.close(); self.connection=None
        if self.host: self.host.close(); self.host=None
        self.clear_round(); self.screens.main()
        camera.position=(65,85,-105); camera.look_at(Vec3(0,0,25)); camera.fov=84
        mouse.locked=False; mouse.visible=True

    def begin_round(self,p):
        self.clear_round(); self.screens.hide(); self.playing=True
        self.hud=HUD(self); self.items={x['id']:x for x in p['items']}
        for item in self.items.values():
            kind=item['kind']; position=Vec3(*item['pos'])+Vec3(0,.32,0)
            if kind in WEAPONS:
                e=Entity(model=self.models[kind].copyTo(NodePath('loot')),position=position,scale=.8,rotation=(0,45,80))
            else:
                tint=TEAL if kind in ('medkit','bandage') else (ORANGE if kind=='ammo' else color.azure)
                e=Entity(model='cube',position=position,scale=(.35,.22,.3),color=tint)
            self.item_entities[item['id']]=e
        self.zone_line=Entity(model=Mesh(vertices=[(math.cos(i*math.tau/128),.3,math.sin(i*math.tau/128)) for i in range(129)],mode='line',thickness=3),color=color.azure)
        self.effects.append((self.zone_line,float('inf')))
        mouse.locked=not bool(self.args.smoke); mouse.visible=bool(self.args.smoke)
        self.spectate_label=Text('',parent=camera.ui,origin=(0,0),y=-.24,scale=.9,color=ORANGE)

    def handle(self,p):
        kind=p['t']
        if kind=='lobby':
            self.lobby_data=p; self.players={x['id']:x for x in p['players']}
            if p['phase']=='lobby':
                if self.screens.page!='lobby': self.screens.lobby()
                else: self.screens.update_lobby()
        elif kind=='started': self.begin_round(p)
        elif kind=='returned':
            self.clear_round(); self.screens.lobby()
            camera.position=(65,85,-105); camera.look_at(Vec3(0,0,25)); camera.fov=84
        elif kind=='state':
            self.own=p['own']; self.players={x['id']:x for x in p['players']}; self.zone=p['zone']
        elif kind=='snapshot' and self.playing:
            self.zone=p['zone']; self.snapshots.append((clock.monotonic(),{r[0]:r for r in p['players']}))
            mine=next((r for r in p['players'] if r[0]==self.connection.id),None)
            if mine:
                pos=Vec3(*mine[1:4])
                if self.mover is None: self.mover=Mover(self.physics,pos)
                elif (pos-self.mover.pos).length()>1.5: self.mover.pos=pos
                elif (pos-self.mover.pos).length()>.65: self.mover.pos=lerp(self.mover.pos,pos,.25)
        elif kind=='pickup':
            self.items.pop(p['item'],None)
            if p['item'] in self.item_entities: destroy(self.item_entities.pop(p['item']))
        elif kind=='shot':
            self.shot_effect(p)
        elif kind=='finished':
            self.finished=True
            if self.hud: self.hud.finished(p)
        elif kind=='error':
            self.screens.message(p['reason'])
            if self.connection and self.connection.id is None: self.connection.close(); self.connection=None
        elif kind=='disconnected':
            reason=p['reason']; self.leave(); self.screens.message('연결 종료: '+reason)
        if self.hud: self.hud.event(p)

    def shot_effect(self,p):
        mine=p['id']==self.connection.id
        sound=self.sounds[p['weapon']]
        distance_to=(camera.world_position-Vec3(*p['origin'])).length()
        sound.volume=self.settings['volume']*(.5 if mine else max(0,.3-distance_to/400)); sound.play()
        if mine:
            self.pitch=max(-88,self.pitch-WEAPONS[p['weapon']].recoil)
            self.shot_visual_at=clock.monotonic()
        if not self.settings['effects']: return
        if mine and self.view_gun:
            flash=Entity(parent=camera,model='sphere',position=(.22,-.12,.85),scale=.065,color=color.yellow,unlit=True)
            self.effects.append((flash,clock.monotonic()+.045))
        impact=Vec3(*p['impact'])
        mark=Entity(model='sphere',position=impact,scale=.055,color=ORANGE,unlit=True)
        self.effects.append((mark,clock.monotonic()+.75))
        if self.show_rays or not mine:
            ray=Entity(model=Mesh(vertices=[p['origin'],p['impact']],mode='line',thickness=1),color=color.rgba(255,211,130,130))
            self.effects.append((ray,clock.monotonic()+.07))

    def update_avatars(self,now):
        if not self.snapshots: return
        target=now-.1
        while len(self.snapshots)>2 and self.snapshots[1][0]<target: self.snapshots.popleft()
        t0,s0=self.snapshots[0]; t1,s1=self.snapshots[-1]
        for t,s in self.snapshots:
            if t<=target: t0,s0=t,s
            if t>=target: t1,s1=t,s; break
        alpha=clamp((target-t0)/max(.001,t1-t0),0,1)
        for pid,row in s1.items():
            if pid==self.connection.id: continue
            if pid not in self.avatars:
                e=Entity(model=self.models['operator'].copyTo(NodePath('operator')),scale=.63)
                e.leg_left=e.model.find('**/leg-left'); e.leg_right=e.model.find('**/leg-right')
                self.avatars[pid]=e
            e=self.avatars[pid]; previous=s0.get(pid,row)
            pos=lerp(Vec3(*previous[1:4]),Vec3(*row[1:4]),alpha)
            moving=(pos-e.position).length()>.002
            e.position=pos; e.rotation_y=row[4]+180; e.enabled=row[8]
            e.scale_y=.45 if row[9] else .63
            if moving:
                swing=math.sin(now*12+pid)*22
                if not e.leg_left.isEmpty(): e.leg_left.setP(swing)
                if not e.leg_right.isEmpty(): e.leg_right.setP(-swing)
            if self.mover and (e.position-self.mover.pos).length()>camera.clip_plane_far: e.enabled=False
        for pid in list(self.avatars):
            if pid not in self.players: destroy(self.avatars.pop(pid))

    def controls(self):
        active=not self.paused and not self.finished and self.players.get(self.connection.id,{}).get('alive',True)
        if not active: return dict(move=[0,0],yaw=self.yaw,pitch=self.pitch)
        return dict(move=[int(bool(held_keys['d']))-int(bool(held_keys['a'])),int(bool(held_keys['w']))-int(bool(held_keys['s']))],
                    yaw=self.yaw,pitch=self.pitch,jump=bool(held_keys['space']),crouch=bool(held_keys['c'] or held_keys['control']),
                    sprint=bool(held_keys['shift']),fire=bool(held_keys['left mouse']),ads=bool(held_keys['right mouse']))

    def update(self):
        dt=min(time.dt,.1); now=clock.monotonic()
        if self.connection:
            for _ in range(300):
                if not self.connection: break
                try: p=self.connection.events.get_nowait()
                except queue.Empty: break
                self.handle(p)
        if self.host and not self.host.errors.empty():
            error=self.host.errors.get(); self.leave(); self.screens.message(error)
        if self.screens.page=='browser' and now-self.browser_at>1:
            self.screens.refresh_rooms(); self.browser_at=now
        for e,expires in self.effects[:]:
            if now>expires or (not self.playing and expires==float('inf')):
                destroy(e); self.effects.remove((e,expires))
        if not self.playing:
            self.bg_angle+=dt*.018
            camera.position=(math.sin(self.bg_angle)*100+45,85,-105+math.cos(self.bg_angle)*20)
            camera.look_at(Vec3(0,0,25))
        elif self.mover and self.hud:
            self.frame_times.append(dt)
            if len(self.frame_times)>600: self.frame_times.pop(0)
            alive=self.players.get(self.connection.id,{}).get('alive',True)
            if mouse.locked and not self.paused and not self.finished and alive:
                self.yaw=(self.yaw+mouse.velocity[0]*110*self.settings['sensitivity'])%360
                self.pitch=clamp(self.pitch-mouse.velocity[1]*110*self.settings['sensitivity'],-88,88)
            controls=self.controls()
            if self.args.smoke:
                age=now-self.started_at
                controls.update(move=[0,1 if 4<age<7 else 0],fire=8<age<10,jump=5<age<5.2)
            self.connection.controls(**controls)
            self.fixed_time+=dt
            while self.fixed_time>=1/30:
                if alive and not self.finished: self.mover.step(controls,1/30)
                self.fixed_time-=1/30
            self.update_avatars(now)
            if alive:
                eye=1.02 if self.mover.crouch else 1.52
                camera.position=lerp(camera.position,self.mover.pos+Vec3(0,eye,0),min(1,dt*30))
                camera.rotation=(self.pitch,self.yaw,0)
                self.spectate_label.text=''
            else:
                survivors=[(pid,e) for pid,e in self.avatars.items() if self.players.get(pid,{}).get('alive')]
                if survivors:
                    pid,e=survivors[self.spectate_index%len(survivors)]
                    camera.position=lerp(camera.position,e.position+Vec3(0,3,-5),min(1,dt*8)); camera.look_at(e.position+Vec3(0,1,0))
                    self.spectate_label.text=f"관전  {self.players[pid]['name']}  /  좌클릭: 다음 플레이어"
                else: self.spectate_label.text='탈락했습니다'
            weapon=self.own.get('weapon','pistol')
            if weapon!=self.weapon_id:
                if self.view_gun: destroy(self.view_gun)
                self.weapon_id=weapon
                self.view_gun=Entity(parent=camera,model=self.models[weapon].copyTo(NodePath('first-person')),position=(.25,-.2,.58),rotation_y=180,scale=.65,unlit=True)
            self.view_gun.enabled=alive and not self.finished
            ads=controls.get('ads',False)
            camera.fov=lerp(camera.fov,57 if ads else (89 if controls.get('sprint') else 84),min(1,dt*12))
            sway=math.sin(now*9)*.012 if self.mover.velocity.length()>1 else math.sin(now*2)*.003
            self.view_gun.position=lerp(self.view_gun.position,Vec3(.015 if ads else .25,-.145 if ads else -.21+sway,.66 if ads else .6),min(1,dt*12))
            self.view_gun.rotation_x=lerp(self.view_gun.rotation_x,-7 if now-self.shot_visual_at<.08 else 0,min(1,dt*25))
            if self.own.get('reload',0)>0: self.view_gun.rotation_x=30
            self.nearest=None; nearest_distance=2.8
            for ident,item in self.items.items():
                delta=Vec3(*item['pos'])-self.mover.pos; distance=delta.length()
                e=self.item_entities[ident]; e.enabled=distance<70
                if distance<nearest_distance: nearest_distance=distance; self.nearest=item
            self.hud.prompt.text=f"[E] {self.nearest['kind'].upper()} 줍기" if self.nearest and alive else ''
            self.hud.cross.enabled=alive and not self.finished
            self.hud.update(dt)
            if self.zone:
                self.zone_line.position=(self.zone['center'][0],0,self.zone['center'][1]); self.zone_line.scale=(self.zone['radius'],1,self.zone['radius'])
        self.smoke(now)

    def smoke(self,now):
        if not self.args.smoke: return
        age=now-self.started_at
        if self.connection and self.connection.id and not self.smoke_start and self.screens.page=='lobby' and age>2:
            self.capture('lobby'); self.connection.send('start'); self.smoke_start=True
        for threshold,name in [(1.5,'menu'),(5,'game'),(11,'combat')]:
            if age>threshold and name not in self.smoke_images:
                self.capture(name); self.smoke_images.add(name)
        if age>self.args.smoke:
            result={'seconds':age,'playing':self.playing,'id':self.connection.id if self.connection else None,
                    'players':len(self.players),'frames':len(self.frame_times),'mean_fps':round(len(self.frame_times)/max(.001,sum(self.frame_times)),1),
                    'position':list(self.mover.pos) if self.mover else None,'hp':self.players.get(self.connection.id,{}).get('hp') if self.connection else None,
                    'packets':self.connection.rx if self.connection else 0,'server_tick_ms':self.host.tick_ms if self.host else None}
            (ROOT.parent/'logs/smoke.json').write_text(json.dumps(result,indent=2),encoding='utf8'); print('SMOKE',result,flush=True)
            self.quit()

    def capture(self,name):
        path=ROOT.parent/'logs'/f'{name}.png'; path.parent.mkdir(exist_ok=True)
        base.win.saveScreenshot(Filename.fromOsSpecific(str(path)))

    def input(self,key):
        if key=='f12': self.capture('manual')
        if not self.playing or not self.connection: return
        if key=='f1': self.debug=not self.debug
        if key=='f3': self.show_rays=not self.show_rays
        if key=='f2':
            if self.debug_mesh: destroy(self.debug_mesh); self.debug_mesh=None
            else:
                self.debug_mesh=Entity(model=loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache/collision.bam'))),color=color.rgba(50,255,160,100),unlit=True)
                self.debug_mesh.setRenderModeWireframe()
        if key=='escape' and not self.finished:
            self.paused=not self.paused; mouse.locked=not self.paused; mouse.visible=self.paused
            if self.paused:
                self.hud.pause=Entity(parent=camera.ui)
                Entity(parent=self.hud.pause,model='quad',scale=(.62,.35),color=color.rgba(8,17,26,240))
                Text('일시 메뉴  /  전투는 계속됩니다',parent=self.hud.pause,origin=(0,0),y=.11,scale=1)
                Button(parent=self.hud.pause,text='계속하기',y=.015,scale=(.4,.055),color=PANEL,on_click=Func(self.input,'escape'))
                Button(parent=self.hud.pause,text='방 나가기',y=-.07,scale=(.4,.055),color=PANEL,on_click=self.leave)
            elif self.hud.pause: destroy(self.hud.pause); self.hud.pause=None
        if self.paused or self.finished: return
        if key=='r': self.connection.send('reload'); self.sounds['reload'].play()
        if key=='h': self.connection.send('heal')
        if key=='e' and self.nearest: self.connection.send('pickup',item=self.nearest['id'])
        if key in ('1','2','3','4','5'):
            weapon=list(WEAPONS)[int(key)-1]; self.connection.send('switch',weapon=weapon)
        if key=='left mouse down' and not self.players.get(self.connection.id,{}).get('alive',True): self.spectate_index+=1

    def quit(self):
        if self.connection: self.connection.close()
        if self.host: self.host.close()
        if self.discovery: self.discovery.close()
        application.quit()
