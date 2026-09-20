from ursina import *
from pathlib import Path
from game.config import GAME_PORT

BG=color.hex('#0c1420'); PANEL=color.hex('#142131'); INK=color.hex('#edf4f6')
MUTED=color.hex('#92aab9'); TEAL=color.hex('#4fe0c0'); ORANGE=color.hex('#ffbb66')

class Screens:
    def __init__(self,app):
        self.app=app; self.root=None; self.page=''; self.notice=None

    def text(self,value,pos,scale=1,color_=INK,parent=None,**kwargs):
        return Text(value,parent=parent or self.root,position=pos,scale=scale,color=color_,**kwargs)

    def panel(self,pos,size,color_=PANEL,parent=None):
        return Entity(parent=parent or self.root,model='quad',position=pos,scale=size,color=color_)

    def button(self,label,pos,callback,width=.36,accent=False):
        b=Button(parent=self.root,text=label,position=pos,scale=(width,.052),color=TEAL if accent else PANEL,
                 text_color=BG if accent else INK,highlight_color=color.hex('#2b514f') if not accent else color.hex('#83f6d9'),
                 pressed_color=ORANGE,on_click=callback)
        b.text_entity.scale=.85
        return b

    def field(self,label,pos,value='',width=.38):
        self.text(label,(pos[0]-width/2,pos[1]+.045),.72,MUTED)
        f=InputField(parent=self.root,default_value=value,position=pos,scale=(width,.045),color=PANEL,limit_content_to='')
        f.text_field.scale=1
        return f

    def begin(self,page,title,subtitle):
        if self.root: destroy(self.root)
        self.root=Entity(parent=camera.ui); self.page=page
        mouse.locked=False; mouse.visible=True
        self.panel((-.48,0),(.87,1.1),color.rgba(9,17,27,243))
        self.panel((-.837,.35),(.006,.15),TEAL)
        self.text('LANFALL',(-.79,.44),2.6)
        self.text('LOCAL NETWORK  /  BATTLE ROYALE',(-.786,.366),.57,TEAL)
        self.text(title,(-.78,.245),1.55)
        self.text(subtitle,(-.78,.184),.75,MUTED)
        self.text('01   /   DRIVE CITY',(.38,-.36),1.1)
        self.text('SOUTH DISTRICT   •   최대 50명',(.38,-.405),.7,TEAL)
        self.text('LANFALL  /  LAN EDITION',(-.79,-.46),.6,MUTED)
        self.notice=self.text('',(-.78,-.39),.7,ORANGE)

    def message(self,text):
        if self.notice: self.notice.text=str(text)[:140]

    def main(self):
        self.begin('main','마지막까지 살아남아라','친구들과 같은 LAN에서. 서버 없이, 바로 전투.')
        self.button('방 만들기',(-.57,.07),self.create, .42,True)
        self.button('LAN 방 찾기',(-.57,-.005),self.browser,.42)
        self.button('설정',(-.57,-.08),self.settings,.42)
        self.button('종료',(-.57,-.155),self.app.quit,.42)
        self.text('혼자 연습 · 봇전 · 1대1 · 최대 50인',(-.78,-.26),.72,MUTED)

    def create(self):
        self.begin('create','방 만들기','게임 시작은 대기실에서 방장만 할 수 있습니다.')
        a=self.app
        name=self.field('닉네임',(-.57,.09),a.nickname,.42)
        room=self.field('방 이름',(-.57,-.005),a.room_name,.42)
        code=self.field('초대 코드 (빈칸: 공개방)',(-.57,-.1),a.room_code,.42)
        def capacity():
            options=[1,2,4,10,20,50]; a.capacity=options[(options.index(a.capacity)+1)%len(options)]
            a.bot_count=min(a.bot_count,a.capacity-1); cap.text=f'정원  {a.capacity}명'; bots.text=f'봇  {a.bot_count}명'
        def bot_count():
            options=sorted(set([0,1,min(3,a.capacity-1),min(7,a.capacity-1),a.capacity-1]))
            a.bot_count=options[(options.index(a.bot_count) if a.bot_count in options else -1)+1 if (options.index(a.bot_count) if a.bot_count in options else -1)+1<len(options) else 0]
            bots.text=f'봇  {a.bot_count}명'
        cap=self.button(f'정원  {a.capacity}명',(-.68,-.185),capacity,.2)
        bots=self.button(f'봇  {a.bot_count}명',(-.45,-.185),bot_count,.2)
        self.button('맵: DRIVE CITY',(-.57,-.255),self.maps,.42)
        def submit():
            a.nickname=name.text.strip()[:24] or 'Player'; a.room_name=room.text.strip() or 'LANFALL ROOM'; a.room_code=code.text.strip()[:24]
            a.host_room()
        self.button('대기실 입장',(-.57,-.33),submit,.42,True)
        self.button('뒤로',(-.2,.43),self.main,.12)

    def maps(self):
        self.begin('maps','맵 선택','현재 플레이 가능한 맵은 한 개입니다.')
        self.panel((-.56,.01),(.44,.24))
        self.text('01  /  DRIVE CITY',(-.755,.098),1.15,TEAL)
        self.text('도심 교전 · 도로 · 건물 · 엄폐물\n자기장으로 좁혀지는 남부 지구',(-.755,.035),.78)
        self.text('선택됨',(-.755,-.061),.74,ORANGE)
        self.panel((-.56,-.2),(.44,.105),color.hex('#101a28'))
        self.text('02  /  다음 전장',(-.755,-.165),.85,MUTED)
        self.text('COMING LATER',(-.755,-.205),.65,MUTED)
        self.button('확인',(-.56,-.32),self.create,.44,True)

    def browser(self):
        self.begin('browser','LAN 방 찾기','같은 공유기 / 스위치의 방을 자동으로 찾습니다.')
        self.app.start_discovery(); self.room_rows=Entity(parent=self.root)
        self.join_name=self.field('닉네임',(-.58,-.15),self.app.nickname,.42)
        self.join_address=self.field('직접 참가: IP:포트#초대코드',(-.58,-.24),'',.42)
        self.button('직접 참가',(-.58,-.325),lambda:self.app.join_address(self.join_address.text,self.join_name.text),.42,True)
        self.button('뒤로',(-.2,.43),self.main,.12)
        self.refresh_rooms()

    def refresh_rooms(self):
        if self.page!='browser': return
        for child in list(self.room_rows.children): destroy(child)
        rooms=self.app.discovery.list()
        if not rooms: self.text('검색 중…  방이 없으면 방을 만들어 보세요.',(-.78,.1),.73,MUTED,parent=self.room_rows)
        for i,r in enumerate(rooms[:4]):
            y=.12-i*.061
            self.text(f"{r['name'][:18]}  {r['count']}+{r.get('bots',0)}/{r['capacity']}  {r['ping']:.0f}ms",(-.78,y),.7,parent=self.room_rows)
            self.text(f"{r['ip']}  {'진행 중' if r['playing'] else ('초대 코드 필요' if r.get('locked') else '대기 중')}",(-.78,y-.025),.52,MUTED,parent=self.room_rows)
            b=Button(parent=self.room_rows,text='참가',position=(-.28,y-.011),scale=(.085,.043),color=PANEL)
            b.text_entity.scale=.65
            b.on_click=Func(self.app.join_found,r)
            b.disabled=bool(r['playing'])

    def lobby(self):
        self.begin('lobby','대기실','준비를 마치면 방장이 전투를 시작합니다.')
        self.panel((.35,.07),(1.02,.49),color.rgba(10,21,32,228))
        self.roster=self.text('',(-.105,.277),.72)
        self.room_info=self.text('',(-.78,.105),.81)
        self.ready_button=self.button('준비',(-.57,-.06),self.app.toggle_ready,.42)
        self.start_button=self.button('게임 시작',(-.57,-.14),lambda:self.app.connection.send('start'),.42,True)
        self.button('초대 주소 복사',(-.57,-.22),self.app.copy_invite,.42)
        self.button('방 나가기',(-.57,-.3),self.app.leave,.42)
        self.update_lobby()

    def update_lobby(self):
        if self.page!='lobby': return
        a=self.app; data=a.lobby_data; players=data.get('players',[])
        cols=[]
        # Up to 50 seats in three columns, including the configured bots.
        labels=[f"{'◆' if p['id']==data.get('host') else '•'} {p['name'][:13]}  {'READY' if p['ready'] else '대기'}" for p in players]
        labels += [f'◇ BOT {i+1:02}  READY' for i in range(data.get('bots',0))]
        for i in range(0,len(labels),17): cols.append('\n'.join(labels[i:i+17]))
        self.roster.text=''
        for child in list(self.roster.children): destroy(child)
        for i,col in enumerate(cols): self.text(col,(i*.32,0),.78,parent=self.roster,line_height=1.6)
        self.room_info.text=f"{data.get('name','')}\n\n{len(players)}명 + 봇 {data.get('bots',0)}명 / {data.get('capacity',0)}명\nDRIVE CITY"
        is_host=a.connection and a.connection.id==data.get('host')
        self.start_button.enabled=is_host
        mine=next((p for p in players if p['id']==a.connection.id),{})
        self.ready_button.text='준비 완료 ✓' if mine.get('ready') else '준비하기'

    def settings(self,back=None):
        self.begin('settings','설정','학교 PC에서는 낮음 또는 보통을 권장합니다.')
        a=self.app
        def quality():
            options=['LOW','MEDIUM','HIGH']; a.settings['quality']=options[(options.index(a.settings['quality'])+1)%3]
            q.text='그래픽  '+a.settings['quality']; a.apply_settings()
        q=self.button('그래픽  '+a.settings['quality'],(-.57,.06),quality,.42)
        def sens():
            a.settings['sensitivity']=round(a.settings['sensitivity']+.2,1)
            if a.settings['sensitivity']>2: a.settings['sensitivity']=.4
            s.text=f"마우스 감도  {a.settings['sensitivity']:.1f}"; a.save_settings()
        s=self.button(f"마우스 감도  {a.settings['sensitivity']:.1f}",(-.57,-.015),sens,.42)
        def volume():
            a.settings['volume']=round((a.settings['volume']+.2)%1.2,1)
            v.text=f"효과음  {int(a.settings['volume']*100)}%"; a.apply_settings()
        v=self.button(f"효과음  {int(a.settings['volume']*100)}%",(-.57,-.09),volume,.42)
        def effects():
            a.settings['effects']=not a.settings['effects']; e.text='효과  '+('ON' if a.settings['effects'] else 'OFF'); a.save_settings()
        e=self.button('효과  '+('ON' if a.settings['effects'] else 'OFF'),(-.57,-.165),effects,.42)
        self.button('완료',(-.57,-.27),back or self.main,.42,True)

    def hide(self):
        if self.root: destroy(self.root); self.root=None
        self.page='game'; self.notice=None
