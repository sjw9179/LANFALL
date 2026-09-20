from dataclasses import dataclass

@dataclass(frozen=True)
class Weapon:
    name: str
    damage: float
    magazine: int
    rate: float
    reload: float
    recoil: float
    spread: float
    range: float
    pellets: int = 1

WEAPONS = {
    'pistol': Weapon('92 / PISTOL', 24, 12, 3.5, 1.3, 1.1, .008, 100),
    'rifle': Weapon('M4A1 / ASSAULT', 22, 30, 8.0, 2.1, .65, .012, 180),
    'smg': Weapon('MP7 / SMG', 15, 32, 12.0, 1.6, .4, .021, 85),
    'shotgun': Weapon('870 / SHOTGUN', 13, 6, 1.0, 2.6, 2.7, .065, 45, 8),
    'dmr': Weapon('AKM-S / DMR', 55, 8, 1.5, 2.4, 2.2, .002, 280),
}
