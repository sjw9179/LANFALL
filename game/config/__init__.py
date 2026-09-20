from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
MAGIC = 'LANFALL'
VERSION = 1
DISCOVERY_PORT = 29740
GAME_PORT = 29741
TICK_RATE = 30
SNAPSHOT_RATE = 15
MAX_PLAYERS = 50
MAP_ID = 'drive_city'

def map_config():
    return json.loads((ASSETS / 'cache' / 'city.json').read_text(encoding='utf8'))
