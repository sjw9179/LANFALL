import pytest
from game.ui.map_navigation import MapNavigation

def test_cursor_anchored_zoom_and_roundtrip():
    m=MapNavigation();anchor=m.world_at(.17,-.12)
    m.zoom_at(.17,-.12,2.5)
    assert m.world_at(.17,-.12)==pytest.approx(anchor)
    m.marker=m.world_at(-.2,.3)
    assert [(m.marker[i]/420-m.center[i])*m.zoom for i in range(2)]==pytest.approx([-.2,.3])
    m.zoom_at(.17,-.12,.4)
    assert m.zoom==1 and m.center==pytest.approx([0,0])

def test_map_pan_and_zoom_never_expose_outside_map():
    m=MapNavigation();m.zoom_at(0,0,100);m.pan(40,-40)
    assert m.zoom==5
    assert all(abs(v)<=.5-.5/m.zoom for v in m.center)
    m.zoom_at(0,0,.0001)
    assert m.zoom==1 and m.center==[0,0]
