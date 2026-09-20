import math
from ursina import Entity,Mesh,Shader,color

ZONE_SHADER=Shader(language=Shader.GLSL,vertex='''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main(){uv=p3d_MultiTexCoord0;gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}
''',fragment='''
#version 140
uniform float elapsed;
in vec2 uv;
out vec4 fragColor;
void main(){
 float streak=pow(max(0.,sin(uv.x*470.+sin(uv.y*8.+elapsed)*2.)),26.);
 float pulse=.5+.5*sin(uv.y*50.-elapsed*2.5);
 float alpha=(.07+streak*.24+pulse*.025)*(1.-uv.y);
 fragColor=vec4(.16,.43,.94,alpha);
}
''')

def zone_wall():
    vertices=[];uvs=[];triangles=[]
    for i in range(129):
        a=i*math.tau/128
        vertices.extend([(math.cos(a),0,math.sin(a)),(math.cos(a),60,math.sin(a))]);uvs.extend([(i/128,0),(i/128,1)])
        if i<128:
            n=i*2;triangles.extend([(n,n+1,n+2),(n+1,n+3,n+2)])
    wall=Entity(model=Mesh(vertices=vertices,triangles=triangles,uvs=uvs),shader=ZONE_SHADER,color=color.rgba32(255,255,255,80),double_sided=True)
    wall.setDepthWrite(False);wall.hide(1);wall.set_shader_input('elapsed',0.)
    return wall
