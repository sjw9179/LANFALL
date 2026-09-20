import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game.world.physics import CollisionWorld
from game.config import ASSETS
from panda3d.core import Vec3
w=CollisionWorld();points=[];lookup={};began=time.monotonic()
for x in range(-204,205,3):
    for z in range(-204,205,3):
        h=w.ground(x,z,top=1.2)
        if not h or h[1].y<.85 or not -.1<h[0].y<.7:continue
        p=h[0]+Vec3(0,.05,0)
        if w.ray(p+Vec3(0,.2,0),p+Vec3(0,2.3,0)):continue
        if any(w.distance(p+Vec3(0,.8,0),v, .8)<.8 for v in ((1,0,0),(-1,0,0),(0,0,1),(0,0,-1))):continue
        lookup[x,z]=len(points);points.append(list(p))
edges=[[] for _ in points]
for (x,z),i in lookup.items():
    for dx,dz in ((3,0),(0,3),(3,3),(3,-3)):
        j=lookup.get((x+dx,z+dz))
        if j is None or abs(points[i][1]-points[j][1])>.55:continue
        a,b=Vec3(*points[i]),Vec3(*points[j]);d=b-a;d.normalize();side=Vec3(d.z,0,-d.x)*.4
        if any(w.ray(a+offset,b+offset) for offset in (Vec3(0,.7,0),Vec3(0,1.5,0)+side,Vec3(0,1.5,0)-side)):continue
        edges[i].append(j);edges[j].append(i)
visited=set();components=[]
for node in range(len(points)):
    if node in visited:continue
    todo=[node];visited.add(node);component=[]
    while todo:
        i=todo.pop();component.append(i)
        for j in edges[i]:
            if j not in visited:visited.add(j);todo.append(j)
    components.append(component)
largest=max(components,key=len);remap={old:new for new,old in enumerate(largest)}
points=[points[i] for i in largest];edges=[[remap[j] for j in edges[i] if j in remap] for i in largest]
(ASSETS/'cache/navigation.json').write_text(json.dumps(dict(points=points,edges=edges),separators=(',',':')))
print(len(points),'nodes',sum(map(len,edges)),'edges',round(time.monotonic()-began,2),'seconds')
