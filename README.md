# 🎯 LANFALL

> **Python-based LAN Multiplayer 3D Battle Royale FPS**

**LANFALL**은 같은 로컬 네트워크에 연결된 플레이어들이 별도의 인터넷 서버 없이 함께 플레이할 수 있도록 제작하는 소규모 3D 배틀로얄 FPS 프로젝트입니다.

Python과 Ursina Engine을 기반으로 제작하며, LAN 환경에서 **UDP Broadcast를 이용해 게임방을 자동 탐색**하고 실제 게임 데이터는 Host와 Client 간의 통신으로 동기화하는 것을 목표로 합니다.

본 프로젝트는 **영주고등학교 게임 프로그래밍 과목 수행평가**를 위해 제작한 학습용 프로젝트입니다. 제한된 개발 기간 안에서 3D 게임 제작, Python 프로그래밍, LAN 기반 네트워크 통신 구조를 직접 적용해 보는 것을 목적으로 하며, 상용 게임 수준보다는 핵심 기능 구현과 기술 학습에 중점을 두어 가볍게 제작하였습니다.

---

## 🎮 Game Rule

플레이어들은 맵의 서로 다른 위치에서 시작합니다.

맵 곳곳에서 총기, 탄약, 방어구와 회복 아이템을 획득하고 다른 플레이어와 전투합니다. 시간이 지나면서 안전구역이 점점 좁아지며, 안전구역 밖에서는 지속적으로 피해를 받습니다.

**마지막까지 살아남은 플레이어가 승리합니다.**

* Players: `2 ~ 10`
* Mode: `Solo Battle Royale`
* Match Time: `5 ~ 10 min`
* Respawn: `Disabled`
* Winner: `Last Survivor`

---

## 🌐 LAN Multiplayer

LANFALL은 별도의 온라인 서버를 사용하지 않습니다.

한 플레이어의 PC가 **Host** 역할을 하며, 같은 네트워크에 연결된 다른 플레이어들이 해당 게임에 접속하는 구조입니다.

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

게임방 탐색과 실제 게임 통신을 분리하여 불필요한 Broadcast 트래픽을 줄이고, Host가 중요한 게임 상태를 관리하도록 구성하는 것이 네트워크 설계의 핵심입니다.

실시간성이 중요한 위치, 방향, 이동 상태 등의 정보는 빠른 전송을 우선하고, 게임 시작, 사망, 아이템 획득, 승리 판정과 같이 반드시 전달되어야 하는 정보는 신뢰성 있는 방식으로 처리하는 구조를 목표로 합니다.

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

## ✨ Features

* LAN 멀티플레이
* UDP Broadcast 기반 게임방 탐색
* Host / Client 구조
* 3D FPS 이동 및 조준
* 총기 및 탄약 시스템
* HP 및 방어구
* 아이템 획득
* 랜덤 스폰
* 안전구역 축소
* 플레이어 사망 및 관전
* 생존 인원 표시
* 최종 승자 판정
* Windows EXE 빌드

---

## 🔫 Weapons

기본적으로 다음 종류의 무기를 구현하는 것을 목표로 합니다.

```text
Assault Rifle
SMG
Shotgun
Sniper / DMR
Pistol
```

각 무기는 다음과 같은 서로 다른 특성을 갖도록 설계합니다.

* Damage
* Fire Rate
* Magazine
* Reload Time
* Recoil
* Spread
* Effective Range

사격 판정은 조준 방향을 기준으로 Raycast를 사용하며, 벽을 통과해 적을 공격하거나 잘못된 방향으로 총알이 발사되지 않도록 충돌 판정을 처리합니다.

---

## 🗺 Map

게임 맵은 소규모 LAN 플레이에 맞게 제작하며 다음과 같은 지역으로 구성합니다.

```text
Small Town
Warehouse
Research Lab
Hill
Forest
Central Combat Area
```

평평한 지형만 사용하는 것이 아니라 언덕, 경사면, 건물, 계단 등의 높낮이를 활용해 다양한 방향에서 교전이 발생하도록 구성합니다.

캐릭터가 경사면이나 계단에서 비정상적으로 튀거나 지형 안으로 들어가는 현상을 줄이기 위해 충돌 판정과 지면 감지를 함께 사용합니다.

---

## 🧪 Testing & Debugging

게임 개발 과정에서는 기능 구현 이후 실제 플레이 상황을 기준으로 반복적으로 테스트하고 수정합니다.

특히 다음 항목을 중점적으로 확인합니다.

* 평지와 경사면에서의 이동
* 계단과 작은 단차 통과
* 벽 및 지형 충돌
* 점프와 착지
* 총기 발사 방향
* 벽 관통 여부
* 탄약 및 재장전 처리
* 플레이어 위치 동기화
* 네트워크 지연 및 패킷 처리
* 아이템 중복 획득
* 자기장 동기화
* 사망 및 관전 처리
* 최종 생존자 판정

개발 중에는 FPS, 좌표, 이동 속도, 네트워크 Ping, Host 여부 등의 정보를 확인할 수 있는 디버그 기능을 활용하여 문제를 확인하고 수정하는 것을 목표로 합니다.

---

## ▶ Run

개발 환경에서 실행하려면 필요한 Python 패키지를 설치합니다.

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
LANFALL/
│
├── main.py
├── game/
│   ├── client/
│   ├── assets/
│   ├── network/
│   ├── player/
│   ├── weapons/
│   ├── world/
│   └── ui/
│
├── tools/
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## 📦 Download & Release

LANFALL은 개발 완료 후 Windows에서 바로 실행할 수 있는 형태로 빌드하여 배포할 예정입니다.

최종 배포 버전은 Python, Ursina Engine 등의 개발 환경을 사용자가 별도로 설치하지 않아도 실행할 수 있도록 **Windows 실행 파일(EXE)** 형태로 패키징합니다.

소스 코드는 GitHub Repository에서 관리하며, 실제 플레이용 완성본은 **GitHub Releases**를 통해 별도로 배포합니다.

사용자는 Release 페이지에서 Windows용 배포 파일을 다운로드한 뒤 압축을 해제하고 `LANFALL.exe`를 실행하는 방식으로 플레이할 수 있도록 구성할 예정입니다.

```text
GitHub Repository
        │
        ├── Source Code
        │
        └── GitHub Releases
                │
                └── LANFALL-v1.0.0-Windows-x64.zip
                        │
                        ├── LANFALL.exe
                        ├── Game Assets
                        └── Required Runtime Files
```

최종 배포 형태는 다음을 목표로 합니다.

* 별도 Python 설치 불필요
* 별도 Ursina 설치 불필요
* Windows에서 바로 실행 가능
* 같은 LAN 환경에서 멀티플레이 가능
* GitHub Releases에서 다운로드 가능

빌드에는 **Nuitka**를 활용할 예정이며, 실행에 필요한 Python Runtime과 라이브러리 및 게임 에셋을 함께 패키징합니다.

---

## 🚧 Development Status

**Currently in development**

현재 첫 번째 개발 목표는 같은 LAN에 연결된 Windows PC에서 한 플레이어가 방을 생성하고, 다른 플레이어가 자동으로 해당 방을 검색하여 접속한 뒤 하나의 배틀로얄 매치를 끝까지 플레이할 수 있도록 만드는 것입니다.

주요 개발 순서는 다음과 같습니다.

```text
Player Movement
      ↓
FPS Camera
      ↓
Weapon System
      ↓
LAN Discovery
      ↓
Host / Client Connection
      ↓
Player Synchronization
      ↓
Battle Royale System
      ↓
Safe Zone
      ↓
Spectating
      ↓
Windows EXE Build
```

---

## 📄 License

This project is licensed under the **MIT License**.

자세한 내용은 `LICENSE` 파일을 참고하세요.

---

## 🎯 LANFALL

> **Drop in. Connect locally. Survive the fall.**
