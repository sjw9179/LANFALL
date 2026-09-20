import pytest
from game.world.physics import CollisionWorld,Mover
from game.server.match import Match,Player
from panda3d.core import Vec3

def test_real_city_spawns_have_stable_ground():
    world=CollisionWorld();spawns=world.spawn_points()
    assert len(spawns)>=50
    assert len(set(tuple(p) for p in spawns))==len(spawns)
    for pos in spawns:
        assert not (16<pos[0]<103 and 10<pos[2]<101), 'Stadium interior spawn'
        assert not world.ray(Vec3(*pos)+Vec3(0,.2,0),Vec3(*pos)+Vec3(0,80,0)), 'Indoor spawn'
        mover=Mover(world,pos)
        for _ in range(45):mover.step({},1/30)
        assert mover.grounded
        assert abs(mover.pos.y-pos[1])<.15

def test_small_party_spawns_central_and_clear():
    world=CollisionWorld();m=Match(world,lambda *a,**k:None,seed=81)
    m.players[1]=Player(1,'Host');m.start(3)
    positions=[p.mover.pos for p in m.players.values()]
    for i,p in enumerate(positions):
        assert p.x*p.x+p.z*p.z<=65**2 and -.1<p.y<.7
        assert not world.ray(p+(0,.2,0),p+(0,Mover.HEIGHT+.2,0))
        assert all((p-q).length()>12 for q in positions[i+1:])

def test_actual_city_walls_block_capsules_from_both_sides():
    world=CollisionWorld();count=0
    for pos in world.spawn_points():
        for d in (Vec3(1,0,0),Vec3(-1,0,0),Vec3(0,0,1),Vec3(0,0,-1)):
            a=Vec3(*pos)+Vec3(0,1.3,0);hit=world.ray(a,a+d*25)
            if not hit or abs(hit[1].y)>.2:continue
            point,normal,_=hit;mover=Mover(world,pos)
            for sign in (-1,1):
                assert mover.sweep(point+normal*sign*1.2,point-normal*sign*1.2).hasHit()
            count+=1
    assert count>=50
