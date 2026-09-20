import math
import struct
import pytest
from panda3d.core import Vec3,BitMask32,Point3
from panda3d.bullet import BulletBoxShape,BulletRigidBodyNode,BulletTriangleMesh,BulletTriangleMeshShape
from game.world.physics import CollisionWorld,Mover,direction
from game.world.zone import Zone
from game.network.protocol import Framer,frame,decode,encode,finite_vector
from game.server.match import Match,Player

def box(world,pos,size):
    body=BulletRigidBodyNode('test'); shape=BulletBoxShape(Vec3(*size)/2); shape.setMargin(.001); body.addShape(shape); body.setIntoCollideMask(BitMask32.bit(0))
    node=world.root.attachNewNode(body); node.setPos(*pos); world.world.attachRigidBody(body)
    return node

@pytest.fixture
def world():
    w=CollisionWorld(False); box(w,(0,-.5,0),(500,1,500))
    w.spawn_points=lambda:[[i%10*3, .03, i//10*3] for i in range(60)]
    return w

def advance(m,steps,**controls):
    for _ in range(steps): m.step(controls,1/30)

def test_flat_wall_jump_and_no_double_jump(world):
    m=Mover(world,(0,.03,0)); advance(m,30,move=[0,1])
    assert m.grounded and 5<m.pos.z<6 and .01<m.pos.y<.08
    box(world,(0,2,8),(8,4,.3)); advance(m,90,move=[0,1]); assert m.pos.z<7.8
    m.pos=Vec3(20,.03,0); advance(m,2)
    heights=[]
    for i in range(100):
        m.step({'jump':True},1/30); heights.append(m.pos.y)
    assert 1<max(heights)<1.5
    assert m.grounded and m.pos.y<.08
    # Releasing midair and pressing again cannot add another impulse.
    advance(m,1,jump=False); advance(m,1,jump=True)
    vy=m.vy; advance(m,1,jump=False); advance(m,1,jump=True)
    assert m.vy<vy

def test_steps_and_high_ledge(world):
    for i in range(4): box(world,(0,(i+1)*.14,2+i),(4,(i+1)*.28,1.01))
    m=Mover(world,(0,.03,0)); advance(m,25,move=[0,1])
    assert m.pos.z>4 and m.pos.y>.6
    box(world,(0,2,8),(4,4,1)); advance(m,90,move=[0,1]); assert m.pos.z<7.5

def test_curb_without_jump_and_crouch_clearance(world):
    box(world,(0,.22,3),(4,.44,3))
    m=Mover(world,(0,.03,0));advance(m,18,move=[0,1])
    assert m.pos.z>2.5 and .44<m.pos.y<.51 and m.grounded
    m.pos=Vec3(10,.025,0);m.crouch=True
    box(world,(10,1.7,0),(3,.2,3));advance(m,3)
    assert m.crouch
    m.pos=Vec3(20,.025,0);advance(m,3)
    assert not m.crouch

def ramp(world,slope):
    mesh=BulletTriangleMesh(); end=10; height=end*slope
    a,b,c,d=Point3(-4,0,0),Point3(4,0,0),Point3(-4,height,end),Point3(4,height,end)
    mesh.addTriangle(a,c,b); mesh.addTriangle(b,c,d)
    body=BulletRigidBodyNode('ramp'); body.addShape(BulletTriangleMeshShape(mesh,dynamic=False)); body.setIntoCollideMask(BitMask32.bit(0))
    world.root.attachNewNode(body); world.world.attachRigidBody(body); world.meshes.append(mesh)

def test_gentle_slope_up_down(world):
    ramp(world,.35); m=Mover(world,(0,.03,-1)); advance(m,45,move=[0,1])
    assert m.pos.z>5 and m.pos.y>1.6 and m.grounded
    advance(m,45,move=[0,-1]); assert m.pos.y<.1 and m.grounded

def test_steep_slope_blocked(world):
    ramp(world,2); m=Mover(world,(0,.03,-1)); advance(m,90,move=[0,1])
    assert m.pos.z<1 and m.pos.y<.8

def new_match(world,count=2):
    events=[]; m=Match(world,lambda kind,**data:events.append((kind,data)),seed=42)
    for i in range(count): m.players[i+1]=Player(i+1,f'P{i+1}',ready=True)
    m.start(); return m,events

def test_raycast_center_headshot_and_wall(world):
    m,e=new_match(world); a,b=m.players.values()
    a.mover.pos=Vec3(0,.025,0); b.mover.pos=Vec3(0,.025,8)
    a.controls={'ads':True}; a.yaw=a.pitch=0
    m.fire(a); assert b.hp<70
    b.hp=100; m.now=2
    box(world,(0,1,4),(5,3,.2)); m.fire(a); assert b.hp==100
    a.mover.pos=Vec3(0,.025,3.7); m.now=4; m.fire(a); assert b.hp==100
    assert direction(0,0).almostEqual(Vec3(0,0,1))

def test_fire_reload_ammo_and_dead(world):
    m,e=new_match(world); a=m.players[1]
    assert m.fire(a); assert not m.fire(a)
    m.action(a,'reload'); m.now=.5; assert not m.fire(a)
    m.update(2); assert a.ammo['pistol']==12
    a.ammo['pistol']=0; m.now=5; assert not m.fire(a)
    a.ammo['pistol']=12; a.alive=False; assert not m.fire(a)

def test_pickup_exclusive_and_victory(world):
    m,e=new_match(world); a,b=m.players.values()
    item=next(iter(m.items.values())); a.mover.pos=b.mover.pos=Vec3(*item['pos'])
    m.action(a,'pickup',item=item['id']); m.action(b,'pickup',item=item['id'])
    assert len([k for k,d in e if k=='pickup'])==1
    m.damage(b,1000,a,source='shot'); m.update(1/30)
    assert m.phase=='finished' and m.winner==a.id
    m.return_lobby(); assert m.phase=='lobby' and not a.ready

def test_inventory_switch_and_pickup_through_wall(world):
    m,e=new_match(world);a=m.players[1];a.mover.pos=Vec3(0,.025,0)
    m.items={77:dict(id=77,kind='rifle',pos=[0,.025,2])}
    wall=box(world,(0,1,1),(4,2,.2))
    m.action(a,'pickup',item=77);assert 77 in m.items and 'rifle' not in a.inventory
    world.world.removeRigidBody(wall.node());wall.removeNode()
    m.action(a,'pickup',item=77);assert a.weapon=='rifle' and 77 not in m.items
    m.action(a,'switch',weapon='pistol');assert a.weapon=='pistol'
    m.action(a,'switch',weapon='dmr');assert a.weapon=='pistol'

def test_solo_practice_does_not_instantly_win(world):
    m,e=new_match(world,1); m.update(1/30)
    assert m.phase=='playing' and m.training
    m.players[1].mover.pos=Vec3(200,0,200); m.update(1)
    assert m.players[1].hp<100

def test_zone_containment_and_eventual_closure():
    z=Zone(42)
    for _ in range(550):
        assert math.dist(z.start_center,z.next_center)+z.next_radius<=z.start_radius+.001
        z.update(1)
    assert z.radius==0

def test_framing_partial_combined_and_bad_packets():
    stream=frame('ping',stamp=12)+frame('ready',ready=True); f=Framer(); packets=[]
    for byte in stream: packets.extend(f.feed(bytes([byte])))
    assert [p['t'] for p in packets]==['ping','ready']
    with pytest.raises(ValueError): Framer().feed(struct.pack('!I',99999999))
    with pytest.raises(ValueError): decode(b'garbage')
    with pytest.raises(ValueError): decode(encode('x').replace(b'LANFALL',b'BADGAME'))
    assert not finite_vector([float('nan'),0])
    assert not finite_vector([0,float('inf')],2)
