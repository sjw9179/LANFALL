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
    args=parser.parse_args()
    loadPrcFileData('', 'coordinate-system y-up-left\nwin-size 1280 720\nsync-video true\nshow-frame-rate-meter false\nnotify-level warning\naudio-library-name p3openal_audio\ntextures-auto-power-2 false\ntextures-power-2 none\ntexture-max-dimension 1024\nframebuffer-multisample 0')
    from ursina import Ursina,application,window
    application.asset_folder=root/'game/assets'
    app=Ursina(title='LANFALL',borderless=False,fullscreen=False,development_mode=False,vsync=True)
    window.exit_button.visible=False; window.fps_counter.enabled=False
    from game.client.app import Game
    game=Game(args)
    app.run()

if __name__=='__main__': main()
