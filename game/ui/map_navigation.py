"""World/map coordinate transforms, independent of the renderer."""
class MapNavigation:
    def __init__(self):
        self.zoom=1.;self.center=[0.,0.];self.marker=None

    def world_at(self,x,y):
        return [(self.center[0]+x/self.zoom)*420,(self.center[1]+y/self.zoom)*420]

    def zoom_at(self,x,y,factor):
        anchor=self.world_at(x,y)
        self.zoom=max(1.,min(5.,self.zoom*factor))
        self.center=[anchor[0]/420-x/self.zoom,anchor[1]/420-y/self.zoom]
        self.clamp()

    def pan(self,x,y):
        self.center[0]-=x/self.zoom;self.center[1]-=y/self.zoom;self.clamp()

    def clamp(self):
        limit=.5-.5/self.zoom
        self.center=[max(-limit,min(limit,v)) for v in self.center]
