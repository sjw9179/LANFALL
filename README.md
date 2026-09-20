# 🎯 PACKET DROP

> **Python-based LAN Multiplayer 3D Battle Royale FPS**

**PACKET DROP**은 같은 로컬 네트워크에 연결된 플레이어들이 별도의 인터넷 서버 없이 함께 플레이할 수 있도록 제작하는 소규모 3D 배틀로얄 FPS 프로젝트입니다.

Python과 Ursina Engine을 기반으로 제작하며, LAN 환경에서 **UDP Broadcast를 이용해 게임방을 자동 탐색**하고 실제 게임 데이터는 Host와 Client 간의 통신으로 동기화하는 것을 목표로 합니다.

본 프로젝트는 **영주고등학교 게임 프로그래밍 과목 수행평가**를 위해 제작한 학습용 프로젝트입니다. 제한된 개발 기간 안에서 3D 게임 제작과 Python 프로그래밍, LAN 기반 네트워크 통신을 직접 적용해 보는 것을 목적으로 하며, 상용 게임 수준보다는 핵심 기능 구현과 기술 학습에 중점을 두어 가볍게 제작하였습니다.

---

## 🎮 Game Rule

플레이어들은 맵의 서로 다른 위치에서 시작합니다.

맵 곳곳에서 총기, 탄약, 방어구와 회복 아이템을 획득하고 다른 플레이어와 전투하게 됩니다. 시간이 지나면서 안전구역이 점점 좁아지며, 안전구역 밖에서는 지속적으로 피해를 받습니다.

**마지막까지 살아남은 플레이어가 승리합니다.**

* Players: `2 ~ 10`
* Mode: `Solo Battle Royale`
* Match Time: `5 ~ 10 min`
* Respawn: `Disabled`
* Winner: `Last Survivor`

---

## 🌐 LAN Multiplayer

PACKET DROP은 별도의 온라인 서버를 사용하지 않습니다.

한 플레이어의 PC가 **Host** 역할을 하며 같은 네트워크의 다른 플레이어들이 해당 게임에 접속합니다.

```text
                UDP Broadcast
                     │
                     ▼
              ┌─────────────┐
              │    HOST     │
              │  + Player   │
              └──────┬──────┘
                     │
             ┌───────┼───────┐
             │       │       │
          Client   Client   Client
```

UDP Broadcast는 같은 서브넷 안에서 실행 중인 게임방을 찾는 **LAN Discovery** 용도로 사용합니다.

게임방을 찾은 이후에는 Host와 각 Client가 직접 통신하여 플레이어 위치, 사격, HP, 아이템, 자기장 등의 상태를 동기화합니다.

---

## 🛠 Tech Stack

| Category      | Technology    |
| ------------- | ------------- |
| Language      | Python        |
| Game Engine   | Ursina Engine |
| 3D Engine     | Panda3D       |
| Networking    | Python Socket |
| LAN Discovery | UDP Broadcast |
| Multiplayer   | UDP / TCP     |
| Build         | Nuitka        |
| Platform      | Windows       |

---

## ✨ Planned Features

* [ ] FPS Player Movement
* [ ] Shooting & Raycast
* [ ] Weapon System
* [ ] HP & Armor
* [ ] Item Looting
* [ ] Random Spawn
* [ ] Shrinking Safe Zone
* [ ] Player Death & Spectating
* [ ] LAN Room Discovery
* [ ] Host / Client Multiplayer
* [ ] Player Position Synchronization
* [ ] Kill Feed
* [ ] Game Lobby
* [ ] Battle Royale Winner System
* [ ] Windows EXE Build

---

## 🔫 Weapons

현재 기본적으로 다음 종류의 무기를 구현하는 것을 목표로 합니다.

```text
Assault Rifle
SMG
Shotgun
Sniper / DMR
Pistol
```

각 무기는 Damage, Fire Rate, Magazine, Reload Time, Recoil 등의 서로 다른 특성을 갖도록 설계합니다.

---

## 🗺 Map

게임 맵은 소규모 LAN 플레이에 맞게 제작하며 다음과 같은 지역으로 구성할 예정입니다.

```text
Small Town
Warehouse
Research Lab
Hill
Forest
Central Combat Area
```

평지만 사용하는 것이 아니라 언덕, 경사면, 건물, 계단 등의 높낮이를 활용해 전투가 다양한 방향에서 발생하도록 설계합니다.

---

## 📡 Network Concept

```text
LAN Discovery
     │
     │ UDP Broadcast
     ▼
Find Host
     │
     ▼
Connect
     │
     ├── Player Movement
     ├── Shooting
     ├── HP
     ├── Items
     ├── Safe Zone
     └── Game State
```

게임방 탐색과 실제 게임 통신을 분리하여 Broadcast 트래픽을 줄이고, Host가 중요한 게임 상태를 관리하도록 구성하는 것이 네트워크 설계의 핵심입니다.

---

## ▶ Development

```bash
git clone <repository>
cd packet-drop
```

필요한 Python 패키지 설치:

```bash
pip install -r requirements.txt
```

게임 실행:

```bash
python main.py
```

---

## 📂 Project Structure

```text
packet-drop/
│
├── main.py
├── assets/
├── network/
├── player/
├── weapons/
├── world/
├── ui/
├── tests/
│
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🚧 Development Status

**Currently in development**

첫 번째 목표는 같은 LAN에 연결된 Windows PC에서 한 플레이어가 방을 생성하고 다른 플레이어가 자동으로 해당 방을 검색하여 접속한 뒤 하나의 배틀로얄 매치를 끝까지 플레이할 수 있도록 만드는 것입니다.

---

## 📄 License

This project is licensed under the **MIT License**.

---

### PACKET DROP

**Drop in. Loot up. Stay connected. Be the last one standing.**
