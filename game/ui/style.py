"""Airy military HUD treatment shared by loading and menu screens."""
from ursina import *
GOLD=color.hex('#e4b640'); WHITE=color.hex('#f5f3e9'); MUTED=color.hex('#b9c2c8')
GRADIENT=Shader(language=Shader.GLSL,vertex='''#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;in vec4 p3d_Vertex;in vec2 p3d_MultiTexCoord0;out vec2 uv;
void main(){uv=p3d_MultiTexCoord0;gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}
''',fragment='''#version 140
in vec2 uv;out vec4 fragColor;uniform vec4 tint;uniform float strength;
void main(){float edge=pow(abs(uv.x-.5)*2.,2.);float vertical=pow(abs(uv.y-.5)*2.,5.);fragColor=vec4(tint.rgb,min(.9,(edge*.65+vertical*.6)*strength));}
''')

def vignette(parent,strength=1):
    e=Entity(parent=parent,model='quad',scale=(2,1.1),shader=GRADIENT,z=.1)
    e.set_shader_input('tint',Vec4(.025,.038,.046,1));e.set_shader_input('strength',float(strength));return e

class LoadingScreen:
    def __init__(self,title='LANFALL',subtitle='전장 준비 중'):
        self.root=Entity(parent=camera.ui,z=-1)
        Entity(parent=self.root,model='quad',scale=(2,1.1),color=color.hex('#18232a'),z=.2)
        # Angular topographic contours, generated as vector lines.
        import math
        for n in range(14):
            pts=[(math.cos(i*math.tau/100)*(.35+n*.065)+.35,math.sin(i*math.tau/100)*(.19+n*.04),0) for i in range(101)]
            Entity(parent=self.root,model=Mesh(vertices=pts,mode='line'),color=color.rgba32(126,158,170,24),z=.1)
        Text('L A N F A L L',parent=self.root,origin=(0,0),y=.10,scale=3.8,color=WHITE)
        Text('B A T T L E   F O R   T H E   L A S T   S I G N A L',parent=self.root,origin=(0,0),y=.015,scale=.64,color=GOLD)
        self.label=Text(subtitle,parent=self.root,origin=(0,0),y=-.29,scale=.82,color=WHITE)
        Entity(parent=self.root,model='quad',scale=(.72,.003),y=-.34,color=color.rgba32(200,210,215,50))
        self.bar=Entity(parent=self.root,model='quad',origin=(-.5,0),position=(-.36,-.34),scale=(.005,.003),color=GOLD)
        Text('LOCAL NETWORK  /  SOUTH DISTRICT',parent=self.root,origin=(0,0),y=-.42,scale=.58,color=MUTED)
        self.set(.02,subtitle)

    def set(self,value,text):
        self.label.text=text;self.bar.scale_x=.72*max(.01,min(1,value))
        # Pump rendering during synchronous model loads, before the game loop exists.
        base.graphicsEngine.renderFrame();base.graphicsEngine.renderFrame()

    def close(self):destroy(self.root)
