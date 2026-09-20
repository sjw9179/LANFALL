from ursina import *
from pathlib import Path
from game.config import GAME_PORT
from game.ui.style import vignette,GOLD

BG=color.hex('#18252d'); PANEL=color.rgba32(220,230,230,28); INK=color.hex('#f5f3eb')
MUTED=color.hex('#a4a6a6'); TEAL=GOLD; ORANGE=color.hex('#e4bd75')

class Screens:
    def __init__(self,app):
        self.app=app; self.root=None; self.page=''; self.notice=None;self.card_page=0;self.roster_signature=None

    def text(self,value,pos,scale=1,color_=INK,parent=None,**kwargs):
        return Text(value,parent=parent or self.root,position=pos,scale=scale,color=color_,**kwargs)

    def panel(self,pos,size,color_=PANEL,parent=None):
        return Entity(parent=parent or self.root,model='quad',position=pos,scale=size,color=color_)

    def button(self,label,pos,callback,width=.36,accent=False):
        b=Button(parent=self.root,text=label,position=pos,scale=(width,.052),color=TEAL if accent else PANEL,
                 text_color=BG if accent else INK,highlight_color=color.hex('#41413e') if not accent else color.hex('#e0c99a'),
                 pressed_color=ORANGE,on_click=callback)
        b.text_size=.82
        return b

    def field(self,label,pos,value='',width=.38):
        self.text(label,(pos[0]-width/2,pos[1]+.045),.72,MUTED)
        f=InputField(parent=self.root,default_value=value,position=pos,scale=(width,.045),color=PANEL,limit_content_to='',character_limit=64)
        return f

    def begin(self,page,title,subtitle):
        if self.root:destroy(self.root)
        self.root=Entity(parent=camera.ui);self.page=page;self.notice=None
        mouse.locked=False;mouse.visible=True
        vignette(self.root,1.1)
        self.app.lobby_stage.set_count(1)
        self.app.lobby_stage.update(True)
        self.text('LANFALL',(-.82,.47),1.9,INK)
        for x,label,action in [(-.33,'플레이',self.main),(-.12,'전장',self.maps),(.06,'설정',self.settings)]:
            if self.app.connection:
                action=self.lobby if label!='설정' else lambda:self.settings(back=self.lobby)
            btn=self.button(label,(x,.44),action,.16)
            btn.color=color.clear;btn.text_color=GOLD if (page=='main' and label=='플레이') else INK
        self.text('LOCAL NETWORK',(.52,.45),.64,GOLD)
        self.panel((0,.389),(1.64,.001),color.rgba32(230,235,230,65))
        self.text(title,(-.80,.31),1.65)
        self.text(subtitle,(-.80,.252),.66,MUTED)
        self.text('LANFALL  /  SOUTH DISTRICT',(-.80,-.47),.54,MUTED)
        self.notice=self.text('',(-.80,-.415),.66,GOLD)

    def message(self,text):
        if self.notice: self.notice.text=str(text)[:140]

    def main(self):
        self.begin('main','마지막 신호가 될 때까지','도시가 닫힌다. 당신의 스쿼드는 준비됐는가.')
        self.text('BATTLE ROYALE',(-.80,.12),.76,GOLD)
        self.text('DRIVE CITY',(-.80,.075),1.6,INK)
        self.text('솔로 · 1대1 · 4인 스쿼드\n친구와 함께하는 최대 50인 LAN 전투',(-.80,.018),.72,MUTED)
        self.button('방 만들기',(-.595,-.18),self.create,.41,True)
        self.button('LAN 방 찾기',(-.595,-.247),self.browser,.41)
        self.button('종료',(.70,-.445),self.app.quit,.18)
        self.text(self.app.nickname,(.18,-.205),1.05,INK)
        self.text('OPERATOR 01   /   STANDBY',(.18,-.25),.58,GOLD)
        Entity(parent=self.root,model='quad',texture='minimap.png',position=(.67,.21),scale=.21)
        self.text('01 / DRIVE CITY',(.56,.083),.64,INK)
        self.text('420 × 420 m   URBAN COMBAT',(.56,.05),.49,MUTED)

    def create(self):
        self.begin('create','방 만들기','게임 시작은 대기실에서 방장만 할 수 있습니다.')
        a=self.app
        def mode():
            a.team_size=4 if a.team_size==1 else 1;mode_button.text='4인 스쿼드' if a.team_size==4 else '솔로 / 개인전'
        mode_button=self.button('4인 스쿼드' if a.team_size==4 else '솔로 / 개인전',(.57,.32),mode,.38,True)
        name=self.field('닉네임',(-.57,.09),a.nickname,.42)
        room=self.field('방 이름',(-.57,-.005),a.room_name,.42)
        code=self.field('초대 코드 (빈칸: 공개방)',(-.57,-.1),a.room_code,.42)
        def capacity():
            options=[1,2,4,10,20,50]; a.capacity=options[(options.index(a.capacity)+1)%len(options)]
            a.bot_count=min(a.bot_count,a.capacity-1); cap.text=f'정원  {a.capacity}명'; bots.text=f'봇  {a.bot_count}명'
        def bot_count():
            options=sorted({n for n in (0,1,3,7,a.capacity-1) if 0<=n<a.capacity})
            a.bot_count=options[(options.index(a.bot_count) if a.bot_count in options else -1)+1 if (options.index(a.bot_count) if a.bot_count in options else -1)+1<len(options) else 0]
            bots.text=f'봇  {a.bot_count}명'
        cap=self.button(f'정원  {a.capacity}명',(-.68,-.185),capacity,.2)
        bots=self.button(f'봇  {a.bot_count}명',(-.45,-.185),bot_count,.2)
        def select_map():
            a.nickname=name.text.strip()[:24] or 'Player';a.room_name=room.text.strip() or 'LANFALL ROOM';a.room_code=code.text.strip()[:24]
            self.maps()
        self.button('맵: DRIVE CITY',(-.57,-.255),select_map,.42)
        def submit():
            a.nickname=name.text.strip()[:24] or 'Player'; a.room_name=room.text.strip() or 'LANFALL ROOM'; a.room_code=code.text.strip()[:24]
            a.host_room()
        self.button('대기실 입장',(-.57,-.33),submit,.42,True)
        self.button('뒤로',(-.2,.43),self.main,.12)

    def maps(self):
        self.begin('maps','맵 선택','현재 플레이 가능한 맵은 한 개입니다.')
        self.panel((.37,.025),(.73,.73),color.rgba32(16,17,19,240))
        Entity(parent=self.root,model='quad',texture='minimap.png',position=(.37,.025),scale=.69,z=-.005)
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
            b.text_size=.65
            b.on_click=Func(self.app.join_found,r)
            b.disabled=bool(r['playing'])

    def lobby(self):
        self.begin('lobby','전투 대기실','플레이어 카드에서 팀과 준비 상태를 확인하세요.')
        self.card_root=Entity(parent=self.root);self.roster_signature=None
        self.room_info=self.text('',(-.80,.15),.77)
        self.ready_button=self.button('준비',(-.61,-.29),self.app.toggle_ready,.38)
        self.start_button=self.button('게임 시작',(-.61,-.36),lambda:self.app.connection.send('start'),.38,True)
        self.button('초대 주소 복사',(.60,-.36),self.app.copy_invite,.34)
        self.button('방 나가기',(.60,-.435),self.app.leave,.34)
        self.bots_label=self.text('',(.41,.31),.71,GOLD)
        self.bot_remove=self.button('- 봇',(.50,.245),lambda:self.app.connection.send('bots',count=self.app.lobby_data.get('bots',0)-1),.15)
        self.bot_add=self.button('+ 봇',(.69,.245),lambda:self.app.connection.send('bots',count=self.app.lobby_data.get('bots',0)+1),.15)
        self.page_label=self.text('',(-.03,-.285),.64,INK)
        self.button('이전',(-.14,-.35),lambda:self.change_page(-1),.14)
        self.button('다음',(.06,-.35),lambda:self.change_page(1),.14)
        self.team_button=self.button('이 팀에 참가',(.01,-.42),self.join_team,.43)
        self.update_lobby()

    def change_page(self,offset):
        count=max(1,getattr(self,'page_count',1));self.card_page=(self.card_page+offset)%count;self.update_lobby()

    def join_team(self):
        if self.app.lobby_data.get('team_size')==4:self.app.connection.send('team',team=self.card_page+1)

    def update_lobby(self):
        if self.page!='lobby':return
        a=self.app;data=a.lobby_data;players=list(data.get('players',[]));squad=data.get('team_size')==4
        bot_base=max((p.get('team',1) for p in players),default=1)+1
        cards=players+[dict(id=1000+i,name=f'BOT {i+1:02}',ready=True,bot=True,team=bot_base+i//4 if squad else 1000+i) for i in range(data.get('bots',0))]
        self.page_count=max(2,max((p.get('team',1) for p in cards),default=1)) if squad else max(1,(len(cards)+3)//4)
        self.card_page=min(self.card_page,self.page_count-1)
        displayed=[p for p in cards if p.get('team')==self.card_page+1][:4] if squad else cards[self.card_page*4:self.card_page*4+4]
        signature=(self.card_page,tuple((p['id'],p['ready'],p['name']) for p in displayed))
        if signature!=self.roster_signature:
            for child in list(self.card_root.children):destroy(child)
            self.roster_signature=signature;a.lobby_stage.set_count(max(1,len(displayed)))
            for i in range(4):
                x=-.48+i*.36;p=displayed[i] if i<len(displayed) else None
                self.panel((x,-.16),(.33,.105),color.rgba32(190,207,214,27),parent=self.card_root)
                self.panel((x,-.107),(.33,.002),GOLD if p and p['ready'] else color.rgba32(210,220,220,80),parent=self.card_root)
                self.text(p['name'][:16] if p else 'EMPTY SLOT',(x-.145,-.123),.77,INK if p else MUTED,parent=self.card_root)
                self.text(('AI / ' if p.get('bot') else 'PLAYER / ')+('READY' if p['ready'] else '준비 중') if p else '친구를 초대하세요',(x-.145,-.172),.56,GOLD if p and p['ready'] else MUTED,parent=self.card_root)
        self.page_label.text=f'{"TEAM" if squad else "OPERATORS"} {self.card_page+1:02} / {self.page_count:02}'
        self.team_button.enabled=squad
        self.room_info.text=f'{data.get("name","")}\n{len(players)}명 + 봇 {data.get("bots",0)} / {data.get("capacity",0)}명\n'+('4인 스쿼드' if squad else '솔로 / 개인전')
        is_host=a.connection and a.connection.id==data.get('host')
        self.start_button.enabled=is_host;self.bot_remove.enabled=is_host;self.bot_add.enabled=is_host
        self.bots_label.text=f'AI OPERATORS  {data.get("bots",0):02}'
        mine=next((p for p in players if p['id']==a.connection.id),{})
        self.ready_button.text='준비 완료' if mine.get('ready') else '준비하기'

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
        self.text('배경음악',(.42,.26),.8,INK)
        music=Slider(parent=self.root,min=0,max=1,default=a.settings['music'],step=.01,position=(.42,.19),scale=.35,dynamic=True)
        music.on_value_changed=lambda:set_audio('music',music.value)
        self.text('효과음',(.42,.09),.8,INK)
        sound=Slider(parent=self.root,min=0,max=1,default=a.settings['volume'],step=.01,position=(.42,.02),scale=.35,dynamic=True)
        sound.on_value_changed=lambda:set_audio('volume',sound.value)
        def set_audio(key,value):
            a.settings[key]=round(value,2)
            for track in a.music_tracks.values():track.volume=a.settings['music']*.65
            for effect in a.sounds.values():effect.volume=a.settings['volume']*.5
            a.save_settings()
        def effects():
            a.settings['effects']=not a.settings['effects']; e.text='효과  '+('ON' if a.settings['effects'] else 'OFF'); a.save_settings()
        e=self.button('효과  '+('ON' if a.settings['effects'] else 'OFF'),(-.57,-.165),effects,.42)
        self.button('완료',(-.57,-.27),back or self.main,.42,True)
        def credits():
            import subprocess
            from game.config import ROOT
            subprocess.Popen(['notepad.exe',str(ROOT.parent/'ASSET_CREDITS.md')])
        self.button('에셋 출처 / 라이선스',(-.57,-.34),credits,.42)

    def hide(self):
        if self.root: destroy(self.root); self.root=None
        self.page='game'; self.notice=None
