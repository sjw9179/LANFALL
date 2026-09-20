import math
import random

class Zone:
    """Six contained circles; 90s grace then 5 x (25s wait + 45s shrink)."""
    def __init__(self, seed=None, duration_scale=1.):
        self.rng=random.Random(seed)
        self.scale=duration_scale
        self.elapsed=0.; self.stage=0
        self.center=[0.,0.]; self.radius=185.
        self.start_center=self.center[:]; self.start_radius=self.radius
        self.next_center=self.center[:]; self.next_radius=130.
        self.choose_target()

    def choose_target(self):
        self.start_center=self.center[:]; self.start_radius=self.radius
        self.next_radius=max(0,self.radius*.61 if self.stage<5 else 0)
        a=self.rng.random()*math.tau
        d=self.rng.random()*(self.radius-self.next_radius)*.72
        self.next_center=[self.center[0]+math.cos(a)*d,self.center[1]+math.sin(a)*d]

    def update(self,dt):
        self.elapsed+=dt/self.scale
        wait=90 if self.stage==0 else 25
        progress=max(0,min(1,(self.elapsed-wait)/45))
        self.center=[a+(b-a)*progress for a,b in zip(self.start_center,self.next_center)]
        self.radius=self.start_radius+(self.next_radius-self.start_radius)*progress
        if self.elapsed>=wait+45 and self.radius>0:
            self.elapsed-=wait+45; self.stage+=1; self.choose_target()

    def outside(self,pos): return math.hypot(pos[0]-self.center[0],pos[2]-self.center[1])>self.radius
    def state(self):
        wait=90 if self.stage==0 else 25
        return dict(center=self.center,radius=round(self.radius,2),next=self.next_center,next_radius=round(self.next_radius,2),
                    stage=self.stage,shrinking=self.elapsed>=wait,remaining=round(max(0,(wait+(45 if self.elapsed>=wait else 0)-self.elapsed)*self.scale),1))
