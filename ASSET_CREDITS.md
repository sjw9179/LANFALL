# LANFALL — asset sources and licenses

The game runs offline after installation. Original downloads are retained locally (not included in the source repository) under `game/assets/source` or the `kenney` directories. Runtime models are normalized GLB/BAM derivatives.

| Asset | Author / source | License | Changes |
|---|---|---|---|
| Drive for Speed map, supplied by the user | [amogusstrikesback2 / Sketchfab](https://sketchfab.com/3d-models/drive-for-speed-map-69235d34307f4df894492f13d8dded93) | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) according to the GLB metadata | Cropped playable district, scale/axis conversion, spatial batching, material adjustment, collision extraction. Original GLB preserved. |
| M4A1 | [nisu / 3DModelsCC0](https://opengameart.org/content/m4a1-assault-rifle) | CC0 | FBX → GLB/BAM, normalized scale, rebuilt material |
| Weathered AKM (DMR slot) | [LonesomeDucky](https://opengameart.org/content/akm) | CC0 | Blend → GLB/BAM, normalized scale |
| Beretta-style textured pistol | [Lotnik](https://opengameart.org/content/textured-pistol) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | Restored diffuse texture, axis conversion, normalized GLB/BAM |
| MP7 | [FaizanDurrany / Faizan Durrani](https://opengameart.org/content/mp7-lowpoly) | CC BY 3.0 | Removed display duplicates; dark material; normalized GLB/BAM |
| Remington 870 | [FaizanDurrany / Faizan Durrani](https://opengameart.org/content/remington-870-lowpoly) | CC BY 3.0 | Removed presentation objects and camo texture; dark material; normalized GLB/BAM |
| Elite soldier | [hc / hackcraft.de, based on LeeZH](https://opengameart.org/content/elite-soldier-model) | CC BY 3.0 (included LICENSE selects this license) | OBJ → GLB/BAM, relaxed arms, added leg rig, normalized height; original license retained |
| Firearm recordings | [Ben Jaszczak et al., Free Firearm Sound Library](https://opengameart.org/content/the-free-firearm-sound-library) | CC0 | Selected shots, trimmed onset/tail, normalized volume, encoded OGG |
| Rifle reload | [SpringySpringo](https://opengameart.org/content/gun-reload-sounds) | CC0 | Converted WAV to OGG |
| Footsteps | [GboxMikeFozzy](https://opengameart.org/content/footsteps-0) | CC0 | Selected variations |
| First-person arms | [para / MakeHuman team](https://opengameart.org/content/fps-arms-rigged-only) | CC0 | Baked sample pose, material restored, scale/camera alignment, GLB/BAM conversion |
| Sky | [Poly Haven / Kloppenheim 06 Pure Sky](https://polyhaven.com/a/kloppenheim_06_puresky) | CC0 | HDR → runtime PNG |
| Initial prototype weapons, characters and sci-fi audio | [Kenney Blaster Kit](https://kenney.nl/assets/blaster-kit), [Blocky Characters](https://kenney.nl/assets/blocky-characters), [Sci-fi Sounds](https://kenney.nl/assets/sci-fi-sounds) | CC0 | Archived source packs; weapons/character/fire sounds replaced in the current game |

The supplied map's noncommercial condition applies to redistribution of that asset. All CC BY assets require this attribution file to accompany distributed copies. No PUBG assets are included. Windows Malgun Gothic is loaded from the user's Windows installation, not redistributed.

The tactical map is an orthographic rendering of the supplied Drive for Speed map, with display gamma adjustment. Arms are split into left/right meshes, finger poses adjusted, and aligned to weapon-specific grips. The LANFALL icon is original geometric artwork.

Runtime software notices are included in `game/assets/licenses/software`. The Microsoft Concurrency Runtime (`concrt140.dll`) is bundled from the official portable Blender 4.3.2 distribution's `blender.crt` directory to satisfy Panda3D's Windows runtime dependency; it is Microsoft software, not a game art asset. This credits file can be opened from Settings → 에셋 출처 / 라이선스.


## 0.4 프레젠테이션 및 아이템

- First Aid Kit 3D — GGBotNet, CC0: https://opengameart.org/content/first-aid-kit-3d . 512px 텍스처 구급상자, 크기 정규화 및 GLB/BAM 변환. firstaid / medkit 크기 구분.
- Food Kit — Kenney, CC0: https://kenney.nl/assets/food-kit . soda-can을 에너지 드링크 아이템으로 사용.
- Survival Kit — Kenney, CC0: https://kenney.nl/assets/survival-kit . bottle과 bedroll-packed를 진통제/붕대 묶음으로 재구성.
- Blaster Kit — Kenney, CC0: https://kenney.nl/assets/blaster-kit . clip-large를 탄약/장전 탄창으로 사용.
- 방탄복 — 앞서 기재한 hc / hackcraft의 Elite soldier(CC BY 3.0)에서 vest 메시만 추출, 두 단계 크기/색 변형.
- The Hunt — Sudocolon, CC0: https://opengameart.org/content/the-hunt . 로비 반복 음악, 볼륨 조절.
- Epic Endgame Cinematic — cynicmusic, CC0: https://opengameart.org/content/epic-endgame-cinematic . 승리 음악용 32초 발췌와 끝부분 페이드. 작곡가: https://cynicmusic.com / https://pixelsphere.org .
- 로비/스플래시/HUD, 자기장 지도 셰이더, 피격/연기/궤적 효과는 LANFALL 자체 구현입니다. PUBG 음악·이미지·로고·모델은 포함하지 않습니다.
