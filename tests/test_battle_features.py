import math
from panda3d.core import Vec3
from test_game import world,new_match,box
from game.server.match import Match,Player
from game.items import MEDICAL

def step(m,seconds):
    for _ in range(round(seconds*30)):m.update(1/30)

def test_medical_caps_time_consumption_and_cancel(world):
    m,_=new_match(world,1);p=m.players[1];p.hp=40;p.medical={k:2 for k in MEDICAL}
    m.action(p,'heal',item='bandage');step(m,3);assert p.hp==40 and p.medical['bandage']==2
    step(m,1.1);assert p.hp==55 and p.medical['bandage']==1
    m.action(p,'heal',item='firstaid');step(m,6.1);assert p.hp==75
    m.action(p,'heal',item='bandage');assert not p.heal_until
    m.action(p,'heal',item='medkit');step(m,8.1);assert p.hp==100
    m.action(p,'heal',item='energy');step(m,4.1);assert 39<p.boost<=40
    p.hp=60;step(m,5);assert p.hp>60
    m.action(p,'heal',item='medkit');m.damage(p,1);assert not p.heal_until and p.medical['medkit']==1
    m.action(p,'heal',item='medkit');p.controls={'move':[0,1]};p.last_input=m.now;step(m,.2)
    assert not p.heal_until and p.medical['medkit']==1

def test_squad_friendly_fire_team_victory_and_stats(world):
    events=[];m=Match(world,lambda k,**d:events.append((k,d)),seed=2);m.team_size=4
    m.players={1:Player(1,'A',team=1),2:Player(2,'B',team=1),3:Player(3,'C',team=2)};m.start()
    a,b,c=m.players.values();m.damage(b,40,a,source='shot');assert b.hp==100
    m.damage(a,100,c,source='shot');m.update(1/30);assert m.phase=='playing' and a.rank==0
    m.damage(c,500,b,head=True,source='shot');m.update(1/30)
    assert m.phase=='finished' and a.rank==b.rank==1 and c.rank==2
    assert b.damage_dealt==100 and b.headshots==1 and b.kills==1
    result=next(d for k,d in events if k=='finished');assert result['team']==1 and result['results']['2']['damage']==100
    death=next(d for k,d in events if k=='death');assert death['drops'] and all(x['kind']!='crate' for x in death['drops'])

def test_head_body_leg_damage(world):
    values=[]
    for height,part in [(1.9,'head'),(1.1,'body'),(.42,'leg')]:
        m,events=new_match(world);a,b=m.players.values();a.mover.pos=Vec3(0,.025,0);b.mover.pos=Vec3(0,.025,8)
        a.controls={'ads':True};a.yaw=0;a.pitch=math.degrees(math.atan2(1.9-height,8))
        m.fire(a);shot=next(d for k,d in events if k=='shot');assert shot['hit_details'][0]['part']==part
        values.append(100-b.hp)
    assert values[0]>values[1]>values[2]

def test_bot_prioritizes_zone_over_visible_enemy(world):
    m,_=new_match(world);bot,enemy=m.players.values();bot.bot=True;bot.mover.pos=Vec3(150,.025,0);enemy.mover.pos=Vec3(160,.025,0)
    m.zone.center=[0,0];m.zone.radius=100;m.zone.next_center=[0,0];m.zone.next_radius=60
    m.now=30;m.bot_input(bot)
    assert bot.controls['sprint'] and not bot.controls['fire'] and bot.route

def test_surface_impacts_only_for_geometry_with_normal(world):
    m,events=new_match(world,1);p=m.players[1];p.mover.pos=Vec3(0,.025,0);p.yaw=0;p.pitch=0;p.controls={'ads':True}
    box(world,(0,2,5),(8,4,.3));assert m.fire(p)
    shot=next(d for k,d in events if k=='shot');surface=shot['surfaces'][0]
    assert abs(surface['pos'][2]-4.85)<.03 and surface['normal'][2]<-.9
    assert not shot['hits']
    events.clear();p.next_fire=0;p.pitch=-70;assert m.fire(p)
    assert not next(d for k,d in events if k=='shot')['surfaces']

def test_close_muzzle_impact_stays_on_wall(world):
    m,events=new_match(world,1);p=m.players[1];p.mover.pos=Vec3(0,.025,0);p.yaw=0;p.pitch=0
    box(world,(0,2,.4),(5,4,.1));assert m.fire(p)
    shot=next(d for k,d in events if k=='shot')
    assert .3<shot['impact'][2]<.4
    assert shot['surfaces'][0]['pos']==shot['impact']
