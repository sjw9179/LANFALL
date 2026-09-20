import math
from ursina import *
from game.ui.style import GOLD,WHITE,MUTED,vignette

MAP_ZONE=Shader(language=Shader.GLSL,vertex='''#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;in vec4 p3d_Vertex;in vec2 p3d_MultiTexCoord0;out vec2 uv;
void main(){uv=p3d_MultiTexCoord0;gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}
''',fragment='''#version 140
in vec2 uv;out vec4 fragColor;uniform vec2 safe_center;uniform float safe_radius;
void main(){float d=length(uv-safe_center);float outside=smoothstep(safe_radius-.002,safe_radius+.002,d);fragColor=vec4(.06,.29,.91,outside*.55);}
''')

def zone_overlay(parent):
    e=Entity(parent=parent,model='quad',shader=MAP_ZONE,z=.004)
    e.set_shader_input('safe_center',Vec2(.5,.5));e.set_shader_input('safe_radius',1.)
    return e

class DamageCompass:
    def __init__(self,parent,app):
        self.app=app;self.signals=[];self.parent=parent
        # Thin red arcs leave the centre of the sight unobstructed.
        verts=[];tris=[]
        for i in range(13):
            t=math.radians(-23+i*46/12)
            verts.extend([(math.sin(t)*.19,math.cos(t)*.19,0),(math.sin(t)*.205,math.cos(t)*.205,0)])
            if i<12:tris.extend([i*2,i*2+1,i*2+2,i*2+1,i*2+3,i*2+2])
        self.mesh=Mesh(vertices=verts,triangles=tris,static=True)
        self.blood=[]
        from game.client.presentation import SOFT
        for x,y,s in [(-.73,.22,.35),(.76,-.14,.38),(-.54,-.4,.3),(.48,.42,.33),(-.81,-.23,.31),(.69,.33,.26)]:
            e=Entity(parent=parent,model='quad',shader=SOFT,position=(x,y,-.018),scale=s)
            e.set_shader_input('tint',Vec4(.52,.01,.007,0));self.blood.append(e)
        self.blood_time=0

    def register(self,origin,hit):
        if hit:self.blood_time=1.4
        if origin is None:return
        if len(self.signals)>=8:
            destroy(self.signals.pop(0)[0])
        e=Entity(parent=self.parent,model=Mesh(vertices=list(self.mesh.vertices),triangles=list(self.mesh.triangles)),color=color.red,z=-.08,scale=1 if hit else 1.35)
        self.signals.append([e,Vec3(*origin),2.2 if hit else 1.1,hit])

    def update(self,dt):
        self.blood_time=max(0,self.blood_time-dt)
        for e in self.blood:e.set_shader_input('tint',Vec4(.50,.009,.004,self.blood_time*.68))
        for signal in self.signals[:]:
            e,pos,ttl,hit=signal;signal[2]-=dt
            delta=pos-camera.world_position
            angle=(math.degrees(math.atan2(delta.x,delta.z))-camera.rotation_y+180)%360-180
            e.rotation_z=-angle;e.color=color.rgba32(235,42,35,int(min(1,max(0,ttl))*(230 if hit else 135)))
            if signal[2]<=0:destroy(e);self.signals.remove(signal)

def show_result(hud,packet,eliminated=False):
    app=hud.app
    if hud.result:destroy(hud.result)
    if hud.pause:destroy(hud.pause);hud.pause=None
    hud.inventory.enabled=False;hud.tactical.enabled=False;app.ads=False;app.paused=False
    hud.last_result=(packet,eliminated)
    own=app.players.get(app.connection.id,{})
    stats=packet.get('stats',{}) if eliminated else packet.get('results',{}).get(str(app.connection.id),app.own.get('stats',{}))
    won=not eliminated and (packet.get('winner')==app.connection.id or (packet.get('team') is not None and packet.get('team')==own.get('team')))
    hud.result=Entity(parent=hud.root,z=-.25)
    hud.combat.enabled=False
    vignette(hud.result,2.2)
    Entity(parent=hud.result,model='quad',scale=(2,1.1),color=color.rgba32(10,18,24,105),z=.08)
    Text('오늘은 치킨이닭!' if won else ('전투 종료' if not eliminated else '다음 전투에서 다시 만나자'),parent=hud.result,position=(-.76,.35),scale=2.8 if won else 1.7,color=GOLD if won else WHITE)
    Text('WINNER  /  LANFALL' if won else 'AFTER ACTION REPORT',parent=hud.result,position=(-.755,.255),scale=.72,color=GOLD)
    rank=stats.get('rank',0)
    Text(f'#{rank:02}' if rank else 'TEAM\nALIVE',parent=hud.result,position=(.51,.35),scale=3.1,color=GOLD)
    Text(f'{packet.get("total",len(app.players))} OPERATORS',parent=hud.result,position=(.51,.20),scale=.65,color=WHITE)
    seconds=stats.get('survived',0)
    for x,label,value in [(-.75,'처치',stats.get('kills',0)),(-.36,'가한 피해',stats.get('damage',0)),(.03,'헤드 명중',stats.get('headshots',0)),(.42,'생존 시간',f'{seconds//60:02}:{seconds%60:02}')]:
        Entity(parent=hud.result,model='quad',position=(x+.13,-.13),scale=(.27,.001),color=GOLD)
        Text(str(value),parent=hud.result,position=(x,-.035),scale=2,color=WHITE)
        Text(label,parent=hud.result,position=(x,-.15),scale=.75,color=MUTED)
    def spectate():
        destroy(hud.result);hud.result=None;hud.combat.enabled=True;mouse.locked=False;mouse.visible=True
    Button(parent=hud.result,text='관전 계속  [J 전적]',position=(-.48,-.32),scale=(.43,.064),color=color.rgba32(230,232,224,35),on_click=spectate)
    if app.host and app.finished:
        action=lambda:app.connection.send('return');label='대기실로 돌아가기'
    else:action=app.leave;label='방 종료 · 메인으로' if app.host else '메인으로 돌아가기'
    Button(parent=hud.result,text=label,position=(.48,-.32),scale=(.43,.064),color=GOLD,text_color=color.black,on_click=action)
    Text('전투 결과는 서버에서 집계됩니다',parent=hud.result,position=(-.75,-.43),scale=.61,color=MUTED)
    mouse.locked=False;mouse.visible=True
    if won:app.set_music('victory')
