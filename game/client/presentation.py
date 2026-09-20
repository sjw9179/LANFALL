import math,random
from ursina import *
from panda3d.core import NodePath
from game.world.physics import Mover

SOFT=Shader(language=Shader.GLSL,vertex='''#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;in vec4 p3d_Vertex;in vec2 p3d_MultiTexCoord0;out vec2 uv;
void main(){uv=p3d_MultiTexCoord0;gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}
''',fragment='''#version 140
in vec2 uv;out vec4 fragColor;uniform vec4 tint;
void main(){float r=length(uv-.5)*2.;float n=.84+.16*sin(uv.x*23.+sin(uv.y*19.)*3.);fragColor=vec4(tint.rgb,pow(max(0.,1.-r),2.)*tint.a*n);}
''')

class DeathVisual(Entity):
    def __init__(self,app,packet):
        super().__init__(position=Vec3(*packet['pos']),rotation_y=packet.get('yaw',0)+180)
        self.age=0.;self.app=app
        self.body=Entity(parent=self,model=app.models['operator'].copyTo(NodePath('fallen')),scale=Mover.HEIGHT/1.78)
        self.body.clearShader()
        self.puffs=[]
        for i in range(10):
            e=Entity(parent=self,model='quad',shader=SOFT,billboard=True,double_sided=True)
            e.setDepthWrite(False);e.hide(1);self.puffs.append(e)

    def update(self):
        self.age+=min(time.dt,.1);t=min(1,self.age/1.1);s=t*t*(3-2*t)
        self.body.rotation_x=-88*s;self.body.y=.20*s
        visible=(self.world_position-camera.world_position).length()<100
        self.body.enabled=visible
        for i,e in enumerate(self.puffs):
            e.enabled=visible
            phase=(self.age*.20+i/10)%1
            e.position=(math.sin(i*2.4+self.age*.35)*phase*.7,.3+phase*4,math.cos(i*1.8)*phase*.55)
            e.scale=.8+phase*1.8;e.set_shader_input('tint',Vec4(.20,.64,.27,math.sin(phase*math.pi)*.65*min(1,self.age)))

class HitBurst(Entity):
    def __init__(self,pos,part):
        super().__init__(position=pos);self.age=0;self.particles=[]
        for _ in range(6 if part!='head' else 9):
            e=Entity(parent=self,model='quad',shader=SOFT,billboard=True,scale=random.uniform(.08,.17))
            e.set_shader_input('tint',Vec4(.45,.025,.02,.9));e.setDepthWrite(False);e.hide(1)
            self.particles.append((e,Vec3(random.uniform(-1,1),random.uniform(.1,1.6),random.uniform(-1,1))))
    def update(self):
        self.age+=time.dt
        for e,v in self.particles:
            e.position=v*self.age+Vec3(0,-2*self.age*self.age,0);e.scale=e.scale+Vec3(1,1,1)*time.dt*.22
            e.set_shader_input('tint',Vec4(.42,.015,.012,max(0,1-self.age/.45)))
        if self.age>.45:destroy(self)

class Tracer(Entity):
    def __init__(self,start,end):
        super().__init__();self.start=Vec3(*start);self.end=Vec3(*end);self.delta=self.end-self.start;self.age=0
        self.length=self.delta.length();self.direction=self.delta.normalized() if self.length else Vec3(0,0,1)
        self.line=Entity(parent=self,model=Mesh(vertices=[(0,0,0),(0,0,1)],mode='line',thickness=1.1),color=color.rgba32(255,219,166,160))
        self.hide(1)
    def update(self):
        self.age+=time.dt;head=min(self.length,self.age*700);tail=max(0,head-7)
        self.line.model.vertices=[self.start+self.direction*tail,self.start+self.direction*head];self.line.model.generate()
        if self.age>max(.045,self.length/700):destroy(self)

SCAR=Shader(language=Shader.GLSL,vertex=SOFT.vertex,fragment='''#version 140
in vec2 uv;out vec4 fragColor;uniform float opacity;
void main(){vec2 p=(uv-.5)*2.;float r=length(p);float edge=.75+.10*sin(atan(p.y,p.x)*9.);float chip=1.-smoothstep(edge-.18,edge,r);float core=1.-smoothstep(.15,.4,r);fragColor=vec4(mix(vec3(.23,.21,.18),vec3(.025),core),chip*opacity*.88);}
''')

def gun_optic(parent):
    """Open, physical sight housing: the scene stays visible around the optic."""
    root=Entity(parent=parent,position=(0,.042,.35))
    root.setFogOff()
    verts=[];tris=[]
    for z in (0,.07):
        for i in range(49):
            t=i*math.tau/48
            for r in (.045,.052):verts.append((math.cos(t)*r,math.sin(t)*r,z))
    for i in range(48):
        a=i*2;b=a+98
        tris.extend([a,a+1,a+2,a+1,a+3,a+2,b,b+2,b+1,b+1,b+2,b+3,a,a+2,b,a+2,b+2,b,a+1,b+1,a+3,a+3,b+1,b+3])
    Entity(parent=root,model=Mesh(vertices=verts,triangles=tris),color=color.hex('#333a3d'),double_sided=True,unlit=True)
    Entity(parent=root,model='cube',position=(0,-.06,.035),scale=(.035,.035,.08),color=color.hex('#41484c'),unlit=True)
    return root

class SurfaceImpact(Entity):
    def __init__(self,pos,normal,parent):
        super().__init__(parent=parent,position=Vec3(*pos)+Vec3(*normal)*.012)
        self.age=0.;self.puffs=[];self.normal=Vec3(*normal)
        self.mark=Entity(parent=self,model='quad',shader=SCAR,scale=random.uniform(.065,.105),double_sided=True)
        self.mark.look_at(self.world_position+self.normal)
        self.mark.set_shader_input('opacity',1.);self.mark.setDepthWrite(False)
        self.hide(1)
        for _ in range(4):
            e=Entity(parent=self,model='quad',shader=SOFT,billboard=True,double_sided=True,scale=random.uniform(.08,.14))
            e.setDepthWrite(False)
            velocity=self.normal*random.uniform(.35,.9)+Vec3(random.uniform(-.25,.25),random.uniform(.15,.45),random.uniform(-.25,.25))
            self.puffs.append((e,velocity))

    def update(self):
        self.age+=time.dt
        for e,v in self.puffs:
            e.enabled=self.age<.5
            if e.enabled:
                e.position=v*self.age; e.scale=.09+self.age*.4
                e.set_shader_input('tint',Vec4(.52,.48,.41,max(0,1-self.age/.5)*.6))
        self.mark.set_shader_input('opacity',min(1.,max(0.,(9-self.age)/2)))
        if self.age>=9:destroy(self)

class LobbyStage:
    def __init__(self,app):
        self.app=app;self.root=Entity(position=(0,-400,0));self.actors=[]
        self.active=None
        Entity(parent=self.root,model='plane',scale=(50,1,50),color=color.hex('#4c575b')).clearShader()
        Entity(parent=self.root,model='cube',position=(0,5,10),scale=(35,12,.3),color=color.hex('#293841')).clearShader()
        for x in range(-15,16,3):
            Entity(parent=self.root,model='cube',position=(x,4,9.6),scale=(.12,9,.14),color=color.hex('#50606a')).clearShader()
        for x in (-7,7):
            Entity(parent=self.root,model='cube',position=(x,.02,0),scale=(.08,.02,24),color=color.hex('#c39f48'),unlit=True)
            Entity(parent=self.root,model='cube',position=(x,4,9.3),scale=(.12,5,.08),color=color.hex('#d8e4df'),unlit=True)
        for x in range(-12,13,3):
            Entity(parent=self.root,model='cube',position=(x,.004,0),scale=(.013,.008,35),color=color.hex('#27363d'),unlit=True)
        Text('L A N F A L L   /   0 1',parent=self.root,position=(-4,3.8,9.3),scale=17,color=color.rgba32(185,191,180,110),rotation_y=0)
        self.set_count(1)

    def set_count(self,count):
        for e in self.actors:destroy(e)
        self.actors=[]
        for i in range(count):
            x=(i-(count-1)/2)*2.1+.5
            e=Entity(parent=self.root,model=self.app.models['operator'].copyTo(NodePath('lobby-operator')),position=(x,0,0),rotation_y=-20,scale=1.2 if count>1 else 1.4,color=color.rgb(.64,.69,.64))
            e.clearShader()
            self.actors.append(e)

    def update(self,active):
        self.root.enabled=active
        if self.active!=active:
            self.active=active
            self.app.sun.color=Vec4(1.4,1.55,1.65,1) if active else Vec4(2.7,2.45,2.05,1)
        if active:
            camera.position=(.3,-398.6,-10.5 if len(self.actors)>1 else -8.0)
            camera.rotation=(0,0,0);camera.fov=58
            self.app.sun.position=(-7,-390,-7);self.app.sun.lookAt(Vec3(0,-399,0))
            for i,e in enumerate(self.actors):e.rotation_y=-20+math.sin(time.time()*.3+i)*2
