"""Shared medical definitions; the server owns consumption and healing."""
MEDICAL = {
    'bandage': dict(name='붕대', seconds=4., heal=15, cap=75, boost=0),
    'firstaid': dict(name='구급상자', seconds=6., heal=75, cap=75, boost=0),
    'medkit': dict(name='의료용 키트', seconds=8., heal=100, cap=100, boost=0),
    'energy': dict(name='에너지 드링크', seconds=4., heal=0, cap=100, boost=40),
    'painkiller': dict(name='진통제', seconds=6., heal=0, cap=100, boost=60),
}

def starting_medical():
    return dict(bandage=3, firstaid=1, medkit=0, energy=1, painkiller=0)
