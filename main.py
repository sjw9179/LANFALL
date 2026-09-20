"""LANFALL entry point. Run with Python 3.12+ or launch Play-LANFALL.cmd."""
import argparse
import os
from pathlib import Path
from panda3d.core import loadPrcFileData

def main():
    root=Path(__file__).resolve().parent
    os.chdir(root)
    parser=argparse.ArgumentParser(description='LANFALL — LAN battle royale')
    parser.add_argument('--name',default='Player')
    parser.add_argument('--port',type=int,default=29741)
    parser.add_argument('--join',default='')
    parser.add_argument('--auto-host',action='store_true')
    parser.add_argument('--bots',type=int,default=3)
    parser.add_argument('--smoke',type=float,default=0,help='Run a visible automated game and save screenshots')
    parser.add_argument('--offscreen',action='store_true',help='Render smoke checks without interrupting the desktop')
    parser.add_argument('--presentation-test',action='store_true',help='Exercise death, spectating, reload and result screens')
    parser.add_argument('--squad',action='store_true',help='Create a four-player squad room with --auto-host')
    args=parser.parse_args()
    loadPrcFileData('', 'coordinate-system y-up-left\nwin-size 1280 720\nsync-video true\nshow-frame-rate-meter false\nnotify-level warning\naudio-library-name p3openal_audio\ntextures-auto-power-2 false\ntextures-power-2 none\ntexture-max-dimension 1024\nframebuffer-multisample 0')
    from ursina import Ursina,application,window
    loadPrcFileData('', 'textures-auto-power-2 false\ntextures-power-2 up\ntexture-max-dimension 4096')
    application.asset_folder=root/'game/assets'
    app=Ursina(title='LANFALL',icon=str(root/'game/assets/cache/lanfall.ico'),borderless=True,fullscreen=not args.offscreen,development_mode=False,vsync=True,window_type='offscreen' if args.offscreen else 'onscreen')
    window.exit_button.visible=False; window.fps_counter.enabled=False
    if args.offscreen:
        from ursina import mouse,camera
        # Offscreen buffers have no OS cursor. Keep test input entirely synthetic.
        mouse.enabled=False
        type(mouse).locked=property(lambda s:False,lambda s,v:None)
        type(mouse).visible=property(lambda s:False,lambda s,v:None)
        camera.ui_lens.setFilmSize(20*window.aspect_ratio,20)
    from ursina import Text,application
    font=Path('C:/Windows/Fonts/malgun.ttf')
    if font.exists():application.fonts_folder=font.parent;Text.default_font=font.name
    from game.ui.style import LoadingScreen
    splash=LoadingScreen(subtitle='엔진 초기화 · 렌더러와 오디오 준비')
    from game.client.app import Game
    game=Game(args,splash)
    if args.smoke:game.capture('splash')
    splash.close()
    if args.smoke:
        for page in ('main','create','maps','settings'):
            getattr(game.screens,page)();game.capture('ui-'+page)
        game.screens.main()
    app.run()

if __name__=='__main__':
    try:main()
    except Exception:
        import traceback,ctypes
        report=Path.home()/'.lanfall/error.log';report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(traceback.format_exc(),encoding='utf8')
        traceback.print_exc()
        if not '--offscreen' in os.sys.argv:
            ctypes.windll.user32.MessageBoxW(None,f'LANFALL을 실행하지 못했습니다.\n오류 기록: {report}','LANFALL',0x10)
        raise SystemExit(1)
