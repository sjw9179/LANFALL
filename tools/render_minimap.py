"""Bake an overhead district image using the actual downloaded map textures."""
from pathlib import Path
from panda3d.core import *
from direct.showbase.ShowBase import ShowBase
ROOT=Path(__file__).resolve().parents[1]
loadPrcFileData('', 'coordinate-system y-up-left\nwindow-type offscreen\nwin-size 1024 1024\naudio-library-name null\nnotify-level warning')
base=ShowBase(windowType='offscreen')
model=base.loader.loadModel(Filename.fromOsSpecific(str(ROOT/'game/assets/cache/city.bam')));model.reparentTo(base.render)
ambient=AmbientLight('ambient');ambient.setColor((.7,.7,.7,1));base.render.setLight(base.render.attachNewNode(ambient))
sun=DirectionalLight('sun');sun.setColor((1,1,1,1));light=base.render.attachNewNode(sun);light.setHpr(-35,-60,0);base.render.setLight(light)
# Fixed-function color map, with all auxiliary glTF stages removed for this bake.
for n in model.findAllMatches('**/+GeomNode'):
    for i in range(n.node().getNumGeoms()):
        state=n.node().getGeomState(i);attrs=state.getAttrib(TextureAttrib)
        if attrs:
            simple=TextureAttrib.make()
            for stage in attrs.getOnStages():
                if stage.getName()=='Base Color':
                    base_stage=TextureStage('map_color');base_stage.setTexcoordName(stage.getTexcoordName())
                    simple=simple.addOnStage(base_stage,attrs.getOnTexture(stage))
            n.node().setGeomState(i,state.setAttrib(simple))
model.setShader(Shader.make(Shader.SL_GLSL, '''#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main(){gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;uv=p3d_MultiTexCoord0;}
''','''#version 130
uniform sampler2D p3d_Texture0;
in vec2 uv;
out vec4 color;
void main(){vec4 c=texture(p3d_Texture0,uv);if(c.a<.5)discard;color=vec4(pow(c.rgb,vec3(.62)),1);}
'''),100)
base.setBackgroundColor(.08,.12,.13)
lens=OrthographicLens();lens.setFilmSize(420,420);lens.setNearFar(1,1000);base.cam.node().setLens(lens)
base.camera.setPos(0,500,0);base.camera.lookAt(Point3(0,0,0),Vec3(0,0,1))
for _ in range(4):base.graphicsEngine.renderFrame()
base.win.saveScreenshot(Filename.fromOsSpecific(str(ROOT/'game/assets/cache/minimap.png')))
base.destroy()
