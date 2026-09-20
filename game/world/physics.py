"""Shared headless Bullet triangle queries and fixed-step capsule locomotion."""
import math
from panda3d.core import (NodePath, Loader, Filename, Vec3, Point3, TransformState,
                          BitMask32, loadPrcFileData)
from panda3d.bullet import (BulletWorld, BulletTriangleMesh, BulletTriangleMeshShape,
                            BulletRigidBodyNode, BulletCapsuleShape, YUp)
from game.config import ASSETS

loadPrcFileData('', 'coordinate-system y-up-left')
MASK=BitMask32.bit(0)

class CollisionWorld:
    def __init__(self, path=None):
        self.world=BulletWorld()
        self.root=NodePath('physics')
        self.meshes=[]
        if path is False: return
        path=path or ASSETS/'cache/collision.bam'
        model=NodePath(Loader.getGlobalPtr().loadSync(Filename.fromOsSpecific(str(path))))
        if model.isEmpty(): raise RuntimeError('Map cache missing; run tools/prepare_map.py')
        for n in model.findAllMatches('**/+GeomNode'):
            mesh=BulletTriangleMesh()
            for i in range(n.node().getNumGeoms()): mesh.addGeom(n.node().getGeom(i),False,n.getTransform(model))
            body=BulletRigidBodyNode('city')
            body.addShape(BulletTriangleMeshShape(mesh,dynamic=False))
            body.setIntoCollideMask(MASK)
            self.root.attachNewNode(body)
            self.world.attachRigidBody(body)
            self.meshes.append(mesh)

    def ray(self, origin, end):
        r=self.world.rayTestClosest(Point3(*origin),Point3(*end),MASK)
        return (Vec3(r.getHitPos()),Vec3(r.getHitNormal()),r.getHitFraction()) if r.hasHit() else None

    def distance(self, origin, direction, length):
        hit=self.ray(origin,Vec3(*origin)+Vec3(*direction)*length)
        return hit[2]*length if hit else length

    def ground(self,x,z,top=8,bottom=-15):
        return self.ray((x,top,z),(x,bottom,z))

    def spawn_points(self):
        import random
        points=[]
        for x in range(-145,146,12):
            for z in range(-145,146,12):
                if x*x+z*z>165**2: continue
                h=self.ground(x,z,top=7)
                if h and h[1].y>.75 and -.5<h[0].y<4:
                    # Reject interiors with too little head clearance and wall edges.
                    if self.ray(h[0]+Vec3(0,.2,0),h[0]+Vec3(0,2.2,0)): continue
                    if any(self.distance(h[0]+Vec3(0,.8,0),d,1.2)<1.1 for d in ((1,0,0),(-1,0,0),(0,0,1),(0,0,-1))): continue
                    points.append([x,float(h[0].y)+.04,z])
        random.Random(781).shuffle(points)
        if len(points)<50: raise RuntimeError(f'Only {len(points)} safe spawn points found')
        return points

class Mover:
    RADIUS=.32
    STEP=.36
    def __init__(self, world, pos):
        self.world=world
        self.pos=Vec3(*pos)
        self.vy=0.
        self.grounded=False
        self.normal=Vec3(0,1,0)
        self.velocity=Vec3(0)
        self.crouch=False
        self.shape=BulletCapsuleShape(.32,1.02,YUp)
        self.short_shape=BulletCapsuleShape(.32,.45,YUp)
        self.jump_held=False

    def sweep(self, a, b, shape=None):
        return self.world.world.sweepTestClosest(shape or self.shape,TransformState.makePos(a),TransformState.makePos(b),MASK,.001)

    def step(self, controls, dt):
        dt=min(dt,1/30)
        old=Vec3(self.pos)
        requested=bool(controls.get('crouch',False))
        if requested: self.crouch=True
        elif self.crouch:
            if not self.world.ray(self.pos+Vec3(0,1,0),self.pos+Vec3(0,1.8,0)): self.crouch=False
        yaw=math.radians(controls.get('yaw',0))
        x,z=controls.get('move',[0,0]); mag=max(1,math.hypot(x,z))
        speed=2.6 if self.crouch else (8 if controls.get('sprint') else 5.4)
        if controls.get('ads'): speed*=.65
        delta=Vec3((x*math.cos(yaw)+z*math.sin(yaw))/mag,0,(z*math.cos(yaw)-x*math.sin(yaw))/mag)*speed*dt
        shape=self.short_shape if self.crouch else self.shape
        half=.545 if self.crouch else .83
        # Raised horizontal capsule allows small stairs, never high walls.
        offset=Vec3(0,half+(self.STEP if self.grounded else .025),0)
        for _ in range(2):
            if delta.lengthSquared()<1e-9: break
            a=self.pos+offset; b=a+delta
            hit=self.sweep(a,b,shape)
            if not hit.hasHit(): self.pos+=delta; break
            fraction=max(0,hit.getHitFraction()-.025)
            self.pos+=delta*fraction
            n=Vec3(hit.getHitNormal()); n.y=0
            if n.lengthSquared()<.01: break
            n.normalize(); delta=(delta-n*delta.dot(n))*(1-fraction)
        jump=bool(controls.get('jump'))
        if jump and not self.jump_held and self.grounded:
            self.vy=7; self.grounded=False
        self.jump_held=jump
        self.vy-=20*dt
        target=self.pos.y+self.vy*dt
        if self.vy>0:
            hit=self.sweep(self.pos+Vec3(0,half,0),self.pos+Vec3(0,half+self.vy*dt,0),shape)
            if hit.hasHit(): target=self.pos.y; self.vy=0
        top=max(old.y,self.pos.y)+self.STEP+.07
        ground=self.world.ground(self.pos.x,self.pos.z,top=top,bottom=target-.18)
        if self.vy<=0 and ground and ground[1].y>=math.cos(math.radians(46)) and ground[0].y>=target-.12:
            self.pos.y=ground[0].y+.025; self.vy=0; self.grounded=True; self.normal=ground[1]
        else:
            if ground and ground[1].y<math.cos(math.radians(46)) and ground[0].y>target:
                self.pos.x=old.x; self.pos.z=old.z
            self.pos.y=target; self.grounded=False
        # Border keeps players on the authored playable district.
        self.pos.x=max(-205,min(205,self.pos.x)); self.pos.z=max(-205,min(205,self.pos.z))
        self.velocity=(self.pos-old)/max(dt,1e-6)
        return self.pos

def direction(yaw,pitch):
    y,p=math.radians(yaw),math.radians(pitch)
    return Vec3(math.sin(y)*math.cos(p),-math.sin(p),math.cos(y)*math.cos(p))

def ray_sphere(origin,direction,center,radius):
    offset=Vec3(*origin)-Vec3(*center)
    b=offset.dot(direction); c=offset.dot(offset)-radius*radius
    disc=b*b-c
    if disc<0: return None
    t=-b-math.sqrt(disc)
    return t if t>=0 else None
