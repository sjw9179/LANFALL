from ursina import *
from game.ui.screens import INK,TEAL,MUTED,PANEL,BG
from game.weapons import WEAPONS
from game.items import MEDICAL

ITEM_NAMES={'ammo':'탄약 / 탄창','armor1':'방탄복 Lv.1','armor2':'방탄복 Lv.2',**{k:w.name for k,w in WEAPONS.items()},**{k:v['name'] for k,v in MEDICAL.items()}}

class Inventory(Entity):
    def __init__(self,app,parent):
        super().__init__(parent=parent,enabled=False,z=-.12)
        self.app=app;self.nearby=[]
        Entity(parent=self,model='quad',scale=(2,1.1),color=color.rgba32(22,34,43,215),z=.02)
        Text('LOADOUT',parent=self,position=(-.78,.44),scale=1.7,color=TEAL)
        Text('TAB / ESC   닫기     |     F   근처 아이템 줍기',parent=self,position=(-.78,.379),scale=.68,color=MUTED)
        for x,title in [(-.77,'VICINITY / 주변'),(-.23,'WEAPONS / 보유 무기'),(.34,'EQUIPMENT / 장비')]:
            Text(title,parent=self,position=(x,.29),scale=.78,color=TEAL)
            Entity(parent=self,model='quad',position=(x+.22,.253),scale=(.44,.0015),color=TEAL)
        self.near_buttons=[]
        for i in range(5):
            b=Button(parent=self,text='',position=(-.55,.185-i*.089),scale=(.44,.071),color=PANEL,highlight_color=color.hex('#45433b'))
            b.text_size=.66;b.on_click=Func(self.pickup,i);self.near_buttons.append(b)
        self.empty=Text('근처에 아이템이 없습니다',parent=self,position=(-.77,.20),scale=.68,color=MUTED)
        self.weapon_buttons={}
        for i,(key,w) in enumerate(WEAPONS.items()):
            b=Button(parent=self,text='',position=(-.01,.185-i*.089),scale=(.44,.071),color=PANEL,highlight_color=color.hex('#45433b'))
            b.text_size=.68;b.on_click=Func(self.equip,key);self.weapon_buttons[key]=b
        self.equipment=Text(parent=self,position=(.34,.21),scale=.85,line_height=1.6)
        self.med_buttons={}
        for i,(key,spec) in enumerate(MEDICAL.items()):
            b=Button(parent=self,text=spec['name'],position=(.56,.05-i*.058),scale=(.44,.050),color=PANEL,on_click=Func(app.connection.send,'heal',item=key))
            b.text_size=.64;self.med_buttons[key]=b
        Text('OPTIC / 고정 배율',parent=self,position=(.34,-.245),scale=.73,color=TEAL)
        self.zoom_buttons=[]
        for i,zoom in enumerate((1,2,4)):
            b=Button(parent=self,text=f'{zoom}x',position=(.401+i*.151,-.30),scale=(.135,.056),color=PANEL,on_click=Func(self.set_zoom,zoom))
            b.text_size=.8;self.zoom_buttons.append((zoom,b))
        Text('이동 / 피격 시 회복 취소 · X 수동 취소',parent=self,position=(.34,-.35),scale=.59,color=MUTED)
        Text('무기를 클릭하면 장착됩니다. 주변 아이템을 클릭하면 줍습니다.',parent=self,position=(-.78,-.405),scale=.7,color=MUTED)

    def equip(self,key):
        if key in self.app.own.get('inventory',[]):self.app.connection.send('switch',weapon=key)

    def pickup(self,index):
        if index<len(self.nearby):self.app.connection.send('pickup',item=self.nearby[index]['id'])

    def set_zoom(self,zoom):self.app.zoom=zoom

    def refresh(self):
        a=self.app;own=a.own;player=a.players.get(a.connection.id,{})
        inv=own.get('inventory',[])
        for i,(key,b) in enumerate(self.weapon_buttons.items()):
            owned=key in inv;selected=own.get('weapon')==key
            b.disabled=not owned;b.color=TEAL if selected else PANEL
            b.text_color=BG if selected else (INK if owned else MUTED)
            b.text=f'{i+1}  {WEAPONS[key].name}\n'+(f'{own.get("ammo",{}).get(key,0):02} / {WEAPONS[key].magazine}'+('   EQUIPPED' if selected else '   장착') if owned else '미보유')
        self.equipment.text=f'HP {player.get("hp",100):03}   ARMOR {player.get("armor",0):03}\nAMMO {own.get("reserve",0):03}   BOOST {own.get("boost",0):.0f}%'
        for key,b in self.med_buttons.items():
            n=own.get('medical',{}).get(key,0);spec=MEDICAL[key]
            b.text=f'{spec["name"]}  ×{n}   |   {spec["seconds"]:.0f}초'
            b.disabled=n<=0 or own.get('heal',0)>0 or (spec['heal']>0 and player.get('hp',100)>=spec['cap']) or (spec['boost']>0 and own.get('boost',0)>=100)
        self.nearby=sorted([item for item in a.items.values() if (Vec3(*item['pos'])-a.mover.pos).length()<2.8],key=lambda item:(Vec3(*item['pos'])-a.mover.pos).length())[:5] if a.mover else []
        self.empty.enabled=not self.nearby
        for i,b in enumerate(self.near_buttons):
            b.enabled=i<len(self.nearby)
            if b.enabled:b.text=ITEM_NAMES.get(self.nearby[i]['kind'],self.nearby[i]['kind'])+'\n클릭하여 줍기'
        for zoom,b in self.zoom_buttons:
            b.color=TEAL if a.zoom==zoom else PANEL;b.text_color=BG if a.zoom==zoom else INK
