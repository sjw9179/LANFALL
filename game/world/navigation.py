"""Road-level A* routing; static graph is prepared once with the map."""
import heapq
import json
from game.config import ASSETS

class Navigation:
    def __init__(self):
        path=ASSETS/'cache/navigation.json'
        data=json.loads(path.read_text()) if path.exists() else {'points':[], 'edges':[]}
        self.points=data['points'];self.edges=data['edges']

    def nearest(self,pos):
        return min(range(len(self.points)),key=lambda i:(self.points[i][0]-pos[0])**2+(self.points[i][2]-pos[2])**2)

    def route(self,start,goal):
        if not self.points:return [list(goal)]
        a,b=self.nearest(start),self.nearest(goal)
        def distance(i,j):return ((self.points[i][0]-self.points[j][0])**2+(self.points[i][2]-self.points[j][2])**2)**.5
        opened=[(distance(a,b),a)];cost={a:0};parent={};closed=set()
        while opened:
            _,i=heapq.heappop(opened)
            if i in closed:continue
            if i==b:break
            closed.add(i)
            for j in self.edges[i]:
                g=cost[i]+distance(i,j)
                if g<cost.get(j,float('inf')):
                    cost[j]=g;parent[j]=i;heapq.heappush(opened,(g+distance(j,b),j))
        if b!=a and b not in parent:
            b=min(cost,key=lambda i:distance(i,b))
        route=[b]
        while route[-1]!=a:route.append(parent[route[-1]])
        return [self.points[i] for i in reversed(route)]
