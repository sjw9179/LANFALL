import collections
import json
import math
import queue
import socket
import time as clock
from pathlib import Path
from ursina import *
from panda3d.core import Filename,Fog,WindowProperties,NodePath,Texture,PNMImage,Vec4
from direct.actor.Actor import Actor
from game.config import ASSETS,ROOT,GAME_PORT
from game.network.client import Connection
from game.network.discovery import Discovery
from game.server.host import Host
from game.world.physics import CollisionWorld,Mover,direction
from game.ui.screens import Screens,TEAL,PANEL,ORANGE
from game.ui.hud import HUD
from game.weapons import WEAPONS
from game.ui.inventory import ITEM_NAMES
from game.ui.style import LoadingScreen
from game.client.presentation import DeathVisual,HitBurst,Tracer,LobbyStage,SurfaceImpact,gun_optic

class Game(Entity):
    def __init__(self,args,splash=None):
        super().__init__()
        self.args=args; self.started_at=clock.monotonic(); self.connection=None; self.host=None; self.discovery=None
        self.nickname=args.name; self.room_name='LANFALL ROOM'; self.room_code=''; self.capacity=10; self.bot_count=3
        self.lobby_data={}; self.players={}; self.own={}; self.zone={}; self.avatars={}; self.snapshots=collections.deque(maxlen=8)
        self.items={}; self.item_entities={}; self.mover=None; self.yaw=0.; self.pitch=0.; self.hud=None
        self.playing=False; self.finished=False; self.paused=False; self.debug=False; self.show_rays=False
        self.ads=False;self.zoom=2
        self.team_size=4 if args.squad else 1;self.loading=False;self.loading_screen=None;self.loading_frames=0;self.round_id=0
        self.death_at=0;self.pending_result=None;self.deaths={};self.spectate_target=None;self.spectate_first=False
        self.watch_state={}
        self.world_fx=Entity();self.reload_started=0;self.recoil_phase=0
        self.fixed_time=0.; self.browser_at=0.; self.nearest=None; self.weapon_id=''; self.view_gun=None
        self.effects=[]; self.shot_visual_at=0; self.spectate_index=0; self.spectate_label=None
        self.smoke_start=False; self.smoke_shot=False; self.smoke_images=set(); self.frame_times=[]
        self.settings_path=Path.home()/'.lanfall/settings.json'
        self.settings={'quality':'MEDIUM','sensitivity':1.,'volume':.6,'music':.35,'effects':True}
        try: self.settings.update(json.loads(self.settings_path.read_text(encoding='utf8')))
        except (OSError,ValueError): pass
        if self.settings.get('visual_revision')!=2:
            self.settings.update(quality='HIGH',visual_revision=2)
        font=Path('C:/Windows/Fonts/malgun.ttf')
        if font.exists():
            application.fonts_folder=font.parent
            Text.default_font=font.name
        if splash:splash.set(.16,'도시 충돌 지형 · 이동 경로 불러오기')
        self.physics=CollisionWorld()
        if splash:splash.set(.35,'DRIVE CITY · 건물과 도로 불러오기')
        self.map=Entity(model=loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache/city.bam'))))
        self.map.setTwoSided(True)
        self.ground_visual=Entity(model='plane',scale=420,y=-.05,color=color.hex('#4d504b'))
        self.sky=Sky(texture=load_texture('sky.png'),color=color.white)
        self.sun=DirectionalLight(shadows=True); self.sun.position=(-50,90,-40); self.sun.look_at(Vec3(0,0,0))
        self.sun.color=Vec4(2.7,2.45,2.05,1)
        self.sun._light.getLens().setFilmSize(120,120);self.sun._light.getLens().setNearFar(1,240)
        self.ambient=AmbientLight(color=Vec4(.32,.39,.48,1))
        import simplepbr
        cubemap=Texture('outdoor ambient');cubemap.setupCubeMap(8,Texture.T_unsigned_byte,Texture.F_rgb)
        for face in range(6):
            img=PNMImage(8,8,3);img.fill(.34,.41,.5);cubemap.load(img,face,0)
        env=simplepbr.EnvMap(cubemap,skip_prepare=True)
        env.filtered_env_map=cubemap
        env.sh_coefficients[0]=Vec3(.9,1.05,1.25)
        env.is_prepared.set_result(env)
        self.pipeline=simplepbr.init(render_node=scene,msaa_samples=4,max_lights=2,enable_shadows=True,
                                      enable_fog=True,use_normal_maps=True,exposure=.15,env_map=env)
        self.map.clearShader();self.ground_visual.clearShader()
        if splash:splash.set(.63,'조명 · 실제 총성 · 로비 음악 준비')
        self.music_tracks={'lobby':Audio(ASSETS/'audio/music_lobby.ogg',autoplay=False,loop=True),
                           'victory':Audio(ASSETS/'audio/music_victory.wav',autoplay=False,loop=False)}
        self.music_state=None
        self.sounds={k:Audio(ASSETS/'audio'/f'{k}.ogg',autoplay=False,volume=.35) for k in [*WEAPONS,'hit','reload']}
        self.shot_pools={k:[Audio(ASSETS/'audio'/f'{k}.ogg',autoplay=False) for _ in range(5)] for k in WEAPONS}
        self.shot_index=0;self.step_index=0;self.step_at=0
        self.steps=[Audio(ASSETS/'audio'/f'step{i}.ogg',autoplay=False) for i in range(4)]
        self.models={k:loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache'/f'{k}.bam'))) for k in [*WEAPONS,'operator','arms']}
        if splash:splash.set(.86,'오퍼레이터 · 무기 · 회복 아이템 준비')
        self.item_models={p.stem[5:]:loader.loadModel(Filename.fromOsSpecific(str(p))) for p in (ASSETS/'cache').glob('item_*.bam')}
        self.lobby_stage=LobbyStage(self)
        self.screens=Screens(self); self.screens.main(); self.apply_settings()
        self.lobby_stage.update(True)
        self.bg_angle=0
        self.debug_mesh=None
        self.set_music('lobby')
        if splash:splash.set(1.,'준비 완료 · LANFALL에 오신 것을 환영합니다')
        if args.auto_host or args.smoke:
            self.bot_count=args.bots; self.capacity=max(2,args.bots+1); self.capacity=min(50,self.capacity)
            invoke(self.host_room,delay=.3)
        elif args.join: invoke(Func(self.join_address,args.join,args.name),delay=.3)
        self.started_at=clock.monotonic()

    def save_settings(self):
        self.settings_path.parent.mkdir(parents=True,exist_ok=True)
        self.settings_path.write_text(json.dumps(self.settings,indent=2),encoding='utf8')

    def set_music(self,state):
        if state==self.music_state:return
        for track in self.music_tracks.values():track.stop()
        self.music_state=state
        if state in self.music_tracks:
            self.music_tracks[state].volume=self.settings['music']*.65;self.music_tracks[state].play()

    def apply_settings(self):
        q=self.settings.get('quality','MEDIUM')
        if q not in ('LOW','MEDIUM','HIGH'): q='MEDIUM'; self.settings['quality']=q
        camera.clip_plane_far={'LOW':150,'MEDIUM':240,'HIGH':400}[q]
        fog=Fog('city haze'); fog.setColor(.43,.51,.57); fog.setExpDensity(.0025)
        scene.setFog(fog)
        self.sun.shadow_map_resolution=Vec2(1024 if q=='HIGH' else 512)
        self.sun.shadows=q!='LOW'
        self.sun._light.getLens().setFilmSize(90,90);self.sun._light.getLens().setFilmOffset(0,0);self.sun._light.getLens().setNearFar(1,240)
        self.pipeline.enable_shadows=q!='LOW';self.pipeline.use_normal_maps=q!='LOW'
        self.pipeline.msaa_samples=0 if q=='LOW' else 4
        for sound in self.sounds.values(): sound.volume=self.settings['volume']*.5
        for track in self.music_tracks.values():track.volume=self.settings['music']*.65
        self.save_settings()

    def host_room(self):
        self.screens.message('도시와 대기실을 준비하는 중…')
        try:
            self.host=Host(CollisionWorld(),self.room_name,self.capacity,self.bot_count,self.room_code,port=self.args.port,discovery_port=0 if self.args.smoke else 29740,team_size=self.team_size)
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
        if self.loading_screen:self.loading_screen.close();self.loading_screen=None
        self.loading=False;self.pending_result=None;self.death_at=0;self.spectate_target=None
        self.watch_state={}
        destroy(self.world_fx);self.world_fx=Entity();self.deaths={}
        for e in self.avatars.values():
            if hasattr(e,'actor'):e.actor.cleanup()
        for e in [*self.avatars.values(),*self.item_entities.values()]: destroy(e)
        self.avatars={}; self.item_entities={}; self.items={}; self.snapshots.clear()
        if self.hud: self.hud.destroy(); self.hud=None
        if self.view_gun: destroy(self.view_gun); self.view_gun=None
        if self.spectate_label: destroy(self.spectate_label); self.spectate_label=None
        self.weapon_id=''; self.mover=None; self.playing=False; self.finished=False; self.paused=False
        self.own={};self.fixed_time=0
        self.ads=False
        for e,_ in self.effects:destroy(e)
        self.effects=[]
        if self.debug_mesh:destroy(self.debug_mesh);self.debug_mesh=None

    def leave(self):
        if self.connection: self.connection.close(); self.connection=None
        if self.host: self.host.close(); self.host=None
        self.clear_round(); self.screens.main()
        self.lobby_stage.update(True)
        mouse.locked=False; mouse.visible=True
        self.set_music('lobby')

    def begin_round(self,p):
        self.clear_round(); self.screens.hide(); self.playing=True
        self.loading=True;self.round_id=p['round'];self.loading_frames=0;self.set_music(None)
        self.loading_screen=LoadingScreen(subtitle='전투 준비 · 맵과 장비 배치 중')
        if self.args.presentation_test and self.host:
            for member in self.host.match.players.values():
                if member.bot:member.controls={};member.brain_at=1e9
        self.lobby_stage.root.enabled=False
        self.hud=HUD(self); self.items={x['id']:x for x in p['items']}
        for item in self.items.values():
            self.spawn_item(item)
        self.zone_line=Entity(model=Mesh(vertices=[(math.cos(i*math.tau/128),.3,math.sin(i*math.tau/128)) for i in range(129)],mode='line',thickness=3),color=color.azure)
        self.effects.append((self.zone_line,float('inf')))
        from game.world.effects import zone_wall
        self.zone_wall=zone_wall();self.effects.append((self.zone_wall,float('inf')))
        mouse.locked=not bool(self.args.smoke); mouse.visible=bool(self.args.smoke)
        self.spectate_label=Text('',parent=camera.ui,origin=(0,0),y=-.24,scale=.9,color=ORANGE)

    def spawn_item(self,item):
        kind=item['kind'];position=Vec3(*item['pos'])+Vec3(0,.07,0)
        model=self.models[kind] if kind in WEAPONS else self.item_models[kind]
        e=Entity(model=model.copyTo(NodePath('loot')),position=position)
        if kind in WEAPONS:e.rotation=(0,45,80);e.y+=.09
        if kind=='armor2':e.color=color.hex('#c4cba7')
        e.clearShader();self.items[item['id']]=item;self.item_entities[item['id']]=e

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
            self.set_music('lobby')
            self.lobby_stage.update(True)
        elif kind=='state':
            before=self.own.get('reload',0)
            self.own=p['own']; self.players={x['id']:x for x in p['players']}; self.zone=p['zone']
            self.watch_state=p.get('watch',{})
            if self.own.get('reload',0)>0:
                self.ads=False
                if not before:self.reload_started=clock.monotonic();self.sounds['reload'].play()
        elif kind=='loading' and self.loading_screen:
            self.loading_screen.set(.92,f'전체 플레이어 준비 확인  {p["ready"]} / {p["total"]} · 완료 후 동시에 시작합니다')
            if self.args.smoke:self.capture('deployment-loading')
        elif kind=='deployed':
            self.loading=False
            if self.loading_screen:self.loading_screen.close();self.loading_screen=None
            mouse.locked=not bool(self.args.smoke);mouse.visible=bool(self.args.smoke)
        elif kind=='snapshot' and self.playing:
            self.zone=p['zone']; self.snapshots.append((clock.monotonic(),{r[0]:r for r in p['players']}))
            mine=next((r for r in p['players'] if r[0]==self.connection.id),None)
            if mine:
                pos=Vec3(*mine[1:4])
                if self.mover is None:
                    self.mover=Mover(self.physics,pos)
                    self.yaw=math.degrees(math.atan2(-pos.x,-pos.z))%360
                elif (pos-self.mover.pos).length()>1.5: self.mover.pos=pos
                elif (pos-self.mover.pos).length()>.65: self.mover.pos=lerp(self.mover.pos,pos,.25)
        elif kind=='pickup':
            self.items.pop(p['item'],None)
            if p['item'] in self.item_entities: destroy(self.item_entities.pop(p['item']))
        elif kind=='shot':
            self.shot_effect(p)
        elif kind=='death':
            visual=DeathVisual(self,p);visual.parent=self.world_fx;self.deaths[p['victim']]=visual
            for item in p.get('drops',[]):self.spawn_item(item)
            if p['victim'] in self.players:self.players[p['victim']].update(alive=False,hp=0)
            if p['victim']==self.connection.id:
                self.death_at=clock.monotonic();self.pending_result=p;self.ads=False
                mouse.locked=False;mouse.visible=True
        elif kind=='finished':
            self.finished=True;self.pending_result=None
            if self.hud: self.hud.finished(p)
        elif kind=='error':
            self.screens.message(p['reason'])
            if self.connection and self.connection.id is None: self.connection.close(); self.connection=None
        elif kind=='disconnected':
            reason=p['reason']; self.leave(); self.screens.message('연결 종료: '+reason)
        if self.hud: self.hud.event(p)

    def shot_effect(self,p):
        mine=p['id']==self.connection.id
        self.shot_index+=1
        sound=self.shot_pools[p['weapon']][self.shot_index%5]
        distance_to=(camera.world_position-Vec3(*p['origin'])).length()
        sound.volume=self.settings['volume']*(.65 if mine else .6/(1+(distance_to/32)**1.4))
        sound.balance=0
        if not mine and self.physics.ray(camera.world_position,Vec3(*p['origin'])): sound.volume*=.55
        sound.play()
        if not mine:
            delta=Vec3(*p['origin'])-camera.world_position
            sound.balance=clamp(delta.dot(camera.right)/max(1,delta.length()),-1,1)
        if mine:
            self.recoil_phase+=1
            self.pitch=max(-88,self.pitch-WEAPONS[p['weapon']].recoil*.65)
            lateral={'pistol':.035,'rifle':.07,'smg':.045,'shotgun':.09,'dmr':.06}[p['weapon']]
            self.yaw+=math.sin(self.recoil_phase*2.4)*lateral
            self.shot_visual_at=clock.monotonic()
        if not self.settings['effects']: return
        origin=Vec3(*p['origin'])
        if mine:origin+=camera.right*.16-camera.up*.13+camera.forward*.7
        tracer=Tracer(origin,p['impact']);tracer.parent=self.world_fx
        for surface in p.get('surfaces',[])[:4]:
            if (Vec3(*surface['pos'])-camera.world_position).length()<65:
                marks=[e for e in self.world_fx.children if isinstance(e,SurfaceImpact)]
                if len(marks)>=80:destroy(marks[0])
                SurfaceImpact(surface['pos'],surface['normal'],self.world_fx)
        for hit in p.get('hit_details',[])[:3]:
            if (Vec3(*hit['pos'])-camera.world_position).length()<100:
                burst=HitBurst(hit['pos'],hit['part']);burst.parent=self.world_fx
        # Gun movement and recorded gunfire convey the shot; no camera-space balls.
        if self.show_rays:
            ray=Entity(model=Mesh(vertices=[p['origin'],p['impact']],mode='line',thickness=1),color=color.rgba32(255,211,130,130))
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
                actor=Actor(self.models['operator'])
                e=Entity(model=actor,scale=Mover.HEIGHT/1.78);e.actor=actor;e.clearShader()
                e.leg_left=actor.controlJoint(None,'modelRoot','leg_left');e.leg_right=actor.controlJoint(None,'modelRoot','leg_right')
                e.gun=Entity(parent=e,model=self.models['rifle'].copyTo(NodePath('remote-gun')),position=(.17,1.14,.15),scale=.75)
                e.gun.clearShader()
                e.tag=Text(parent=e,text='',position=(0,2.03,0),origin=(0,0),scale=5,billboard=True,color=ORANGE)
                e.tag.hide(1);e.visibility_at=0
                self.avatars[pid]=e
            e=self.avatars[pid]; previous=s0.get(pid,row)
            pos=lerp(Vec3(*previous[1:4]),Vec3(*row[1:4]),alpha)
            moving=(pos-e.position).length()>.002
            e.position=pos; e.rotation_y=row[4]+180;e.yaw=row[4];e.pitch=row[5]; e.enabled=row[8] and pid not in self.deaths
            e.scale_y=(1.4 if row[9] else Mover.HEIGHT)/1.78
            if now>e.visibility_at:
                e.visibility_at=now+.2
                eye=e.position+Vec3(0,Mover.CROUCH_EYE if row[9] else Mover.EYE,0)
                distance_to=(eye-camera.world_position).length()
                visible=row[8] and distance_to<85 and not self.physics.ray(camera.world_position,eye)
                e.tag.enabled=visible;e.tag.text=f'{self.players.get(pid,{}).get("name","OPERATOR")}  {distance_to:.0f}m' if visible else ''
            swing=math.sin(now*12+pid)*22 if moving else 0
            if not e.leg_left.isEmpty(): e.leg_left.setP(swing)
            if not e.leg_right.isEmpty(): e.leg_right.setP(-swing)
            if self.mover and (e.position-self.mover.pos).length()>camera.clip_plane_far: e.enabled=False
        for pid in list(self.avatars):
            if pid not in self.players: destroy(self.avatars.pop(pid))

    def controls(self):
        active=not self.loading and not self.paused and not self.finished and not (self.hud and (self.hud.result or self.hud.tactical.enabled or self.hud.inventory.enabled)) and self.players.get(self.connection.id,{}).get('alive',True)
        if not active: return dict(move=[0,0],yaw=self.yaw,pitch=self.pitch)
        return dict(move=[int(bool(held_keys['d']))-int(bool(held_keys['a'])),int(bool(held_keys['w']))-int(bool(held_keys['s']))],
                    yaw=self.yaw,pitch=self.pitch,jump=bool(held_keys['space']),crouch=bool(held_keys['c'] or held_keys['control']),
                    sprint=bool(held_keys['shift']),fire=bool(held_keys['left mouse']),ads=self.ads)

    def update(self):
        dt=min(time.dt,.1); now=clock.monotonic()
        self.lobby_stage.update(not self.playing)
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
        if self.playing and self.mover and self.hud:
            if self.loading:
                self.loading_frames+=1
                if self.loading_frames==3:self.connection.send('loaded',round=self.round_id)
            if self.pending_result and now-self.death_at>2:
                self.hud.eliminated(self.pending_result);self.pending_result=None
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
                if alive and not self.finished and not self.loading:self.mover.step(controls,1/30)
                self.fixed_time-=1/30
            self.update_avatars(now)
            self.sun.position=(self.mover.pos.x-50,90,self.mover.pos.z-40)
            self.sun.lookAt(self.mover.pos)
            if alive and self.mover.grounded and self.mover.velocity.length()>1 and now>self.step_at:
                self.step_index=(self.step_index+1)%4;step=self.steps[self.step_index]
                step.volume=self.settings['volume']*(.12 if self.mover.crouch else .3);step.pitch=1.08 if controls.get('sprint') else 1
                step.play();self.step_at=now+(.29 if controls.get('sprint') else .43)
            if alive:
                eye=Mover.CROUCH_EYE if self.mover.crouch else Mover.EYE
                camera.position=lerp(camera.position,self.mover.pos+Vec3(0,eye,0),min(1,dt*30))
                camera.rotation=(self.pitch,self.yaw,0)
                self.spectate_label.text=''
            elif now-self.death_at<2 and self.connection.id in self.deaths:
                body=self.deaths[self.connection.id];camera.position=body.position+Vec3(0,2.1,-3.2)
                camera.look_at(body.position+Vec3(0,.65,0));camera.rotation_z=0
            else:
                survivors=[(pid,e) for pid,e in self.avatars.items() if self.players.get(pid,{}).get('alive')]
                teammates=[(pid,e) for pid,e in survivors if self.players[pid].get('team')==self.players.get(self.connection.id,{}).get('team')]
                if teammates:survivors=teammates
                if survivors:
                    pid,e=survivors[self.spectate_index%len(survivors)]
                    if self.spectate_target!=pid:self.connection.send('spectate',id=pid)
                    eye=e.position+Vec3(0,Mover.EYE,0);forward=direction(e.yaw,e.pitch)
                    desired=eye if self.spectate_first else eye-direction(e.yaw,0)*3.4+Vec3(0,.7,0)
                    obstruction=self.physics.ray(eye,desired)
                    if obstruction:desired=obstruction[0]+(eye-desired).normalized()*.25
                    camera.position=desired if self.spectate_target!=pid else lerp(camera.position,desired,min(1,dt*12))
                    camera.look_at(eye+forward*15);camera.rotation_z=0;self.spectate_target=pid
                    e.enabled=not self.spectate_first
                    e.tag.enabled=False
                    self.spectate_label.text=f"관전  {self.players[pid]['name']}  |  Q / E 대상 변경  ·  V 시점  ·  J 전적"
                else: self.spectate_label.text='탈락했습니다'
            weapon=self.own.get('weapon','pistol')
            if weapon!=self.weapon_id:
                if self.view_gun: destroy(self.view_gun)
                self.weapon_id=weapon
                self.view_gun=Entity(parent=camera,model=self.models[weapon].copyTo(NodePath('first-person')),position=(.18,-.14,.3),scale=1)
                self.view_gun.clearShader()
                self.gun_sight=gun_optic(self.view_gun)
                grips={'pistol':((0,-.105,.055),(-.025,-.15,.07)),
                       'rifle':((0,-.13,.30),(-.025,-.12,.62)),
                       'smg':((0,-.11,.12),(-.025,-.10,.36)),
                       'shotgun':((0,-.13,.32),(-.025,-.105,.71)),
                       'dmr':((0,-.13,.30),(-.025,-.11,.67))}
                self.grip_entities=[]
                for name,pos in zip(('arm_right','arm_left'),grips[weapon]):
                    part=self.models['arms'].find('**/'+name)
                    if not part.isEmpty():
                        arm=Entity(parent=self.view_gun,model=part.copyTo(NodePath('grip')),position=pos)
                        arm.clearShader();arm.hide(1)
                        arm.rest_pos=Vec3(*pos);self.grip_entities.append(arm)
                self.reload_mag=Entity(parent=self.view_gun,model=self.item_models['ammo'].copyTo(NodePath('reload-magazine')),scale=.45 if weapon=='pistol' else .65,enabled=False)
                self.reload_mag.clearShader();self.reload_mag.hide(1)
                self.view_gun.hide(1)
            ads=controls.get('ads',False) and self.own.get('reload',0)<=0
            self.view_gun.enabled=alive and not self.finished and not self.hud.inventory.enabled and not self.hud.tactical.enabled
            zoom_fov=math.degrees(2*math.atan(math.tan(math.radians(84)/2)/self.zoom))
            camera.fov=lerp(camera.fov,zoom_fov if ads else (89 if controls.get('sprint') else 84),min(1,dt*18))
            sway=math.sin(now*9)*.012 if self.mover.velocity.length()>1 else math.sin(now*2)*.003
            # Compensate view-model width/height as the world FOV narrows.
            # The bore sits just below the centre; hands remain below the lens.
            ratio=math.tan(math.radians(camera.fov)/2)/math.tan(math.radians(84)/2)
            self.view_gun.scale=(ratio,ratio,1)
            target=Vec3(0,-.042*ratio,.32) if ads else Vec3(.18*ratio,((-.095 if weapon=='pistol' else -.14)+sway)*ratio,.40 if weapon=='pistol' else .28)
            self.view_gun.position=lerp(self.view_gun.position,target,min(1,dt*16))
            self.view_gun.rotation_x=lerp(self.view_gun.rotation_x,-7 if now-self.shot_visual_at<.08 else 0,min(1,dt*25))
            reloading=self.own.get('reload',0)
            if reloading>0:
                progress=clamp(1-reloading/WEAPONS[weapon].reload,0,1);motion=math.sin(progress*math.pi)
                self.view_gun.rotation=(-25*motion,-9*motion,-15*motion)
                self.view_gun.y+=.025*motion
                if len(self.grip_entities)>1:self.grip_entities[1].position=self.grip_entities[1].rest_pos+Vec3(0,-.13*motion,-.03*motion)
                self.reload_mag.enabled=.18<progress<.84
                self.reload_mag.position=Vec3(-.02,-.16-.14*motion,.055 if weapon=='pistol' else .30)
            else:
                self.view_gun.rotation_z=lerp(self.view_gun.rotation_z,0,min(1,dt*15));self.view_gun.rotation_y=lerp(self.view_gun.rotation_y,0,min(1,dt*15))
                self.reload_mag.enabled=False
                for arm in self.grip_entities:arm.position=lerp(arm.position,arm.rest_pos+Vec3(0,-.08 if ads else 0,0),min(1,dt*15))
            self.nearest=None; nearest_distance=2.8
            for ident,item in self.items.items():
                delta=Vec3(*item['pos'])-self.mover.pos; distance=delta.length()
                e=self.item_entities[ident]; e.enabled=distance<70
                if distance<nearest_distance: nearest_distance=distance; self.nearest=item
            self.hud.prompt.text=f"[F] {ITEM_NAMES.get(self.nearest['kind'],self.nearest['kind'])} 줍기" if self.nearest and alive and not ads else ''
            self.hud.cross.enabled=alive and not self.finished and not ads and not self.hud.inventory.enabled and not self.hud.tactical.enabled
            self.hud.update(dt)
            self.spectate_label.enabled=not bool(self.hud.result)
            if self.zone:
                self.zone_line.position=(self.zone['center'][0],0,self.zone['center'][1]); self.zone_line.scale=(self.zone['radius'],1,self.zone['radius'])
                self.zone_wall.position=self.zone_line.position;self.zone_wall.scale=(self.zone['radius'],1,self.zone['radius'])
                self.zone_wall.set_shader_input('elapsed',float(now-self.started_at))
        self.smoke(now)

    def smoke(self,now):
        if not self.args.smoke: return
        age=now-self.started_at
        if self.connection and self.connection.id and not self.smoke_start and self.screens.page=='lobby' and age>2:
            self.capture('lobby'); self.connection.send('start'); self.smoke_start=True
        for threshold,name in [(1.5,'menu'),(5,'game'),(11,'combat')]:
            if age>threshold and name not in self.smoke_images:
                self.capture(name); self.smoke_images.add(name)
        if age>14 and self.hud and 'tactical' not in self.smoke_images:
            self.hud.toggle_map();self.capture('tactical')
            self.hud.map_nav.zoom_at(.15,.12,2.5);self.hud.map_nav.marker=self.hud.map_nav.world_at(.12,-.08)
            self.hud.update_map();self.capture('tactical-zoom-marker')
            self.hud.toggle_map();self.smoke_images.add('tactical')
        if age>12 and self.hud and 'inventory' not in self.smoke_images:
            self.hud.inventory.enabled=True;self.hud.inventory.refresh();self.capture('inventory');self.hud.inventory.enabled=False;self.smoke_images.add('inventory')
        if age>15 and self.hud and 'optic' not in self.smoke_images:
            self.ads=True
        if age>16 and self.hud and 'optic' not in self.smoke_images:
            self.capture('optic');self.ads=False;self.smoke_images.add('optic')
        if age>18 and self.mover and self.host and 'opponent-setup' not in self.smoke_images:
            points=self.physics.spawn_points()
            pair=next(((p,q) for p in points for q in points if 13<(Vec3(*p)-Vec3(*q)).length()<20 and not self.physics.ray(Vec3(*p)+Vec3(0,Mover.EYE,0),Vec3(*q)+Vec3(0,Mover.EYE,0))),None)
            if pair:
                p,q=map(lambda x:Vec3(*x),pair)
                self.host.match.players[self.connection.id].mover.pos=p;self.mover.pos=p
                bot=next((p for p in self.host.match.players.values() if p.bot),None)
                if bot:bot.mover.pos=q;bot.controls={};bot.brain_at=1e9
                if self.args.presentation_test:
                    for member in self.host.match.players.values():
                        if member.bot:member.controls={};member.brain_at=1e9
                delta=q-p;self.yaw=math.degrees(math.atan2(delta.x,delta.z));self.pitch=0
            self.smoke_images.add('opponent-setup')
        if age>20 and self.hud and 'opponent' not in self.smoke_images:
            self.capture('opponent');self.smoke_images.add('opponent')
        if self.args.presentation_test and self.host and self.hud:
            match=self.host.match;own=match.players[self.connection.id]
            def once(name,threshold,action):
                if age>threshold and name not in self.smoke_images:
                    if action() is not False:self.smoke_images.add(name)
            def floor_shot():
                self.pitch=32;own.pitch=32;own.yaw=self.yaw;own.next_fire=0
                own.ammo[own.weapon]=max(1,own.ammo[own.weapon]);match.fire(own)
            once('surface-shot',20.4,floor_shot)
            once('surface-impact',20.65,lambda:self.capture('surface-impact'))
            once('surface-reset',21.5,lambda:setattr(self,'pitch',0))
            def kill_bot():
                bot=next(p for p in match.players.values() if p.bot and p.alive)
                match.damage(bot,200,own,source='shot')
            once('death-setup',22,kill_bot)
            once('death-loot',23.3,lambda:self.capture('death-loot'))
            def hurt():
                bot=next(p for p in match.players.values() if p.bot and p.alive)
                match.damage(own,35,bot,source='shot')
            once('hurt-setup',24,hurt)
            once('hurt',24.1,lambda:self.capture('hurt'))
            once('reload-setup',25,lambda:match.action(own,'reload'))
            once('reload-motion',25.65,lambda:self.capture('reload-motion'))
            once('heal-setup',27,lambda:match.action(own,'heal',item='firstaid'))
            once('heal-progress',28,lambda:self.capture('heal-progress'))
            def verify_healing():
                if own.heal_until:
                    assert age<35,'First aid timer stalled'
                    return False
                assert own.hp>=75,'First aid did not complete during stationary use'
                assert own.ammo[own.weapon]==WEAPONS[own.weapon].magazine,'Reload did not refill the magazine'
                assert not self.ads,'Reload left ADS active'
            once('medical-verified',33.3,verify_healing)
            if 'medical-verified' in self.smoke_images:
                once('own-death',34,lambda:match.damage(own,200,next(p for p in match.players.values() if p.alive and p.bot),source='shot'))
            once('death-report',36.5,lambda:self.capture('death-report'))
            def spectate():
                if self.hud.result:destroy(self.hud.result);self.hud.result=None;self.hud.combat.enabled=True
            once('spectate-setup',37,spectate)
            once('spectate',38,lambda:self.capture('spectate'))
            def victory_preview():
                self.hud.finished(dict(winner=self.connection.id,team=own.team,total=4,results={str(own.id):dict(rank=1,kills=3,damage=285,headshots=2,survived=245)}))
                self.capture('victory-preview');destroy(self.hud.result);self.hud.result=None;self.hud.combat.enabled=True
            once('victory-preview',39,victory_preview)
        if age>self.args.smoke:
            result={'seconds':age,'playing':self.playing,'id':self.connection.id if self.connection else None,
                    'players':len(self.players),'frames':len(self.frame_times),'mean_fps':round(len(self.frame_times)/max(.001,sum(self.frame_times)),1),
                    'position':list(self.mover.pos) if self.mover else None,'hp':self.players.get(self.connection.id,{}).get('hp') if self.connection else None,
                    'packets':self.connection.rx if self.connection else 0,'server_tick_ms':self.host.tick_ms if self.host else None}
            result['deployment_ready']=not self.loading
            if self.args.presentation_test:result['presentation_checks']=sorted(self.smoke_images)
            if self.hud:
                if self.hud.result:destroy(self.hud.result);self.hud.result=None;self.hud.combat.enabled=True
                self.finished=False
                self.input('escape');panel=self.hud.pause
                self.leave()
                result['pause_menu_cleaned']=panel.isEmpty()
                assert result['pause_menu_cleaned'],'Pause menu survived leaving the round'
                self.capture('exit-menu')
            (ROOT.parent/'logs/smoke.json').write_text(json.dumps(result,indent=2),encoding='utf8'); print('SMOKE',result,flush=True)
            self.quit()

    def capture(self,name):
        path=ROOT.parent/'logs'/f'{name}.png'; path.parent.mkdir(exist_ok=True)
        base.graphicsEngine.renderFrame()
        base.win.saveScreenshot(Filename.fromOsSpecific(str(path)))

    def input(self,key):
        if key=='f12': self.capture('manual')
        if not self.playing or not self.connection: return
        if self.hud.tactical.enabled and key not in ('m','escape'):
            self.hud.map_input(key);return
        dead=not self.players.get(self.connection.id,{}).get('alive',True)
        if key=='j' and hasattr(self.hud,'last_result'):
            from game.ui.combat_widgets import show_result
            show_result(self.hud,*self.hud.last_result);return
        if self.hud.result:return
        if dead:
            if key in ('q','e','left mouse down'):self.spectate_index+=-1 if key=='q' else 1
            if key=='v':self.spectate_first=not self.spectate_first
            if key not in ('escape','m','f1','f2','f3','f12'):return
        if key=='tab' and not self.paused and not self.finished and not self.hud.tactical.enabled:
            opened=not self.hud.inventory.enabled
            self.hud.inventory.enabled=opened;self.ads=False
            mouse.locked=not opened;mouse.visible=opened
            if opened:self.hud.inventory.refresh()
            return
        if key=='escape' and self.hud.inventory.enabled:
            self.hud.inventory.enabled=False;mouse.locked=True;mouse.visible=False
            return
        if self.hud.inventory.enabled:return
        if key=='m' and not self.paused and not self.finished:
            opened=self.hud.toggle_map();mouse.locked=not opened;mouse.visible=opened
            return
        if key=='escape' and self.hud.tactical.enabled:
            self.hud.toggle_map();mouse.locked=True;mouse.visible=False
            return
        if key=='f1': self.debug=not self.debug
        if key=='f3': self.show_rays=not self.show_rays
        if key=='f2':
            if self.debug_mesh: destroy(self.debug_mesh); self.debug_mesh=None
            else:
                self.debug_mesh=Entity(model=loader.loadModel(Filename.fromOsSpecific(str(ASSETS/'cache/collision.bam'))),color=color.rgba32(50,255,160,100),unlit=True)
                self.debug_mesh.setRenderModeWireframe()
        if key=='escape' and not self.finished:
            self.paused=not self.paused; mouse.locked=not self.paused; mouse.visible=self.paused
            if self.paused:
                self.hud.pause=Entity(parent=self.hud.root)
                Entity(parent=self.hud.pause,model='quad',scale=(.62,.35),color=color.rgba32(16,17,19,245))
                Text('일시 메뉴  /  전투는 계속됩니다',parent=self.hud.pause,origin=(0,0),y=.11,scale=1)
                Button(parent=self.hud.pause,text='계속하기',y=.015,scale=(.4,.055),color=PANEL,on_click=Func(self.input,'escape'))
                Button(parent=self.hud.pause,text='방 나가기',y=-.07,scale=(.4,.055),color=PANEL,on_click=self.leave)
            elif self.hud.pause: destroy(self.hud.pause); self.hud.pause=None
        if self.hud.tactical.enabled:
            self.hud.map_input(key);return
        if self.paused or self.finished: return
        if key=='right mouse down' and self.own.get('reload',0)<=0:self.ads=not self.ads
        if self.ads and key in ('scroll up','scroll down'):
            levels=[1,2,4];self.zoom=levels[(levels.index(self.zoom)+(1 if key=='scroll up' else -1))%3]
        if key=='r':self.ads=False;self.connection.send('reload')
        if key=='h': self.connection.send('heal')
        if key=='x':self.connection.send('cancel')
        if key=='f' and self.nearest: self.connection.send('pickup',item=self.nearest['id'])
        if key in ('1','2','3','4','5'):
            weapon=list(WEAPONS)[int(key)-1]; self.connection.send('switch',weapon=weapon)
        if key=='left mouse down' and not self.players.get(self.connection.id,{}).get('alive',True): self.spectate_index+=1

    def quit(self):
        if self.connection: self.connection.close()
        if self.host: self.host.close()
        if self.discovery: self.discovery.close()
        application.quit()
