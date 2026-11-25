# 「한 점」 — 나만의 제철 맛집 지도

네이버 지도에 저장한 맛집(954곳)을 지도 하나에 모아, "이번 달 제철인 걸 어디서 먹을 수 있나"를 바로 고르게 해 주는 개인용 웹앱.
사용자는 나 + 친구·가족(링크로 보기). 아이폰 웹앱(홈 화면 추가) 기준, 반응 좋으면 앱. 목표: 12월 안 MVP (겨울 제철 시즌).

기획 결정 사항(12회 문답 + 2026-11-24 바뀐 결정)은 [docs/prd-notes.md](docs/prd-notes.md)에 있다. 새 기능을 만들기 전에 먼저 읽을 것.

## 실행

```bash
python3 scripts/dev_server.py     # http://localhost:5173  (app/ + /api/transit 중계 + /api/sync)
```

- 정적 파일만 필요하면 아무 서버나 되지만, 대중교통 실제 시간(/api/transit)과 동기화 버튼(/api/sync)은 dev_server.py 에서만 동작한다.
- Python 3 + curl 필요. 외부 패키지 없음.
- 작업 PC는 2026-11-24부터 Windows (그 전엔 맥). 배포 push는 `sync.py`의 `publish()`가 git을 직접 부른다 (서버가 띄운 프로세스에선 `bash`가 WSL로 잡혀 셸 스크립트가 안 돌았음).
- PC 전용 비밀 파일(저장소 밖, `data/`): `shares.json`(네이버 공유 폴더 ID), `supabase.json`(url + `sb_secret_` 키, 폰 동기화 처리용). 새 PC로 옮길 때 같이 가져올 것.

## 구조

| 경로 | 내용 |
| --- | --- |
| `app/index.html` | 앱 전체 (HTML·CSS·JS 한 파일). 지도는 SVG, 돋보기 투영(`warp`)으로 지역 확대 |
| `app/season.js` | 월별 제철 음식표 (`SEASON_ITEMS`: emoji, 정규식, months, peak(절정 달), note, tip(산지·먹는 법), origin) + `seasonTags`, `originOf` |
| `app/places.js` `geo.js` `types.js` | `build_data.py` 가 만드는 데이터 (직접 수정 금지) |
| `app/dong/{도 코드}.json` | `build_dong.py` 가 만드는 행정동 경계·이름 (도별 17개, 합계 약 5MB). 시·군·구를 눌렀을 때 그 도 파일만 받는다 |
| `scripts/build_dong.py` | `data/geo_raw/HangJeongDong_ver*.geojson`(가장 최신) → `app/dong/`. 지도의 시·군·구 자료가 예전 경계라 이름 대신 동 중심점 위치로 묶음 |
| `app/food/{음식 이름}.png` | 제철 음식 그림 50개 (2026-11-25, ChatGPT 그림판을 잘라 만듦, 약 120px 투명 PNG). `index.html`의 `FOOD_IMG`에 있는 이름만 그림, 나머지는 `season.js` 이모지. 가자미·대게·꼬막은 아직 없음. 그림을 넣으면 `FOOD_IMG`에 이름 추가 |
| `app/config.js` | 배포용 설정 (`transitProxy`) |
| `scripts/sync.py` | '지금 동기화': 저장 목록(raw) 다시 받기 → 새 가게·실패했던 가게만 수집 → 전화 보강 → 빌드 → `publish()`(app/ 바뀐 것만 커밋·push → 자동 배포) |
| `scripts/collect_naver.py` | 저장 가게마다 네이버 플레이스 홈 1페이지 → `data/naver/{sid}.json` (메뉴·가격·후기 요약·키워드·별점·영업시간). 기본은 아직 안 받은 곳만, `--refresh`면 전부 |
| `scripts/fill_phones.py` | 전화번호 없는 곳을 네이버 검색 결과에서 보강 (도로명+건물번호가 번호 옆에 있을 때만, 30일에 1번) |
| `scripts/classify.py` | 유형 19종 분류 (업종 + 대표 메뉴) |
| `scripts/build_data.py` | raw + naver + geo → `app/*.js` |
| `scripts/dev_server.py` | 로컬 서버 + 네이버 대중교통 경로 중계 + 동기화 실행·진행 조회 |
| `supabase/votes.sql` | 약속·투표 테이블(`votes`, `vote_people`)과 함수. 테이블은 아무도 직접 못 읽고, 친구(anon)는 투표 ID를 넘기는 함수로만 그 약속 하나를 읽고 씀. SQL Editor에서 다시 실행해도 안전 |
| `supabase/grades.sql` | 내 등급(`grades`: place_id → S·A·B·C). 누구나(anon) 읽기, 로그인한 본인만 쓰기. SQL Editor에서 다시 실행해도 안전 |
| `supabase/says.sql` | 내 한마디(`says`: place_id → say 120자·dish 40자 '꼭 시킬 것'). 누구나 읽기, 로그인한 본인만 쓰기. 상세(친구에게만 상자로 보임, 나는 입력칸)·목록 줄(💬)에 나옴 |
| `supabase/photos.sql` | 내 사진(가게당 최대 5장, 첫 장이 대표). Storage 공개 버킷 `photos/{가게}/{이름}.jpg`, 이름 목록은 `says.photo`(쉼표). 올릴 때 긴 쪽 1280px JPEG 0.82로 줄임(`shrinkPhoto`). 상세 맨 위 넘겨 보기 `.pgal`(HSEL, 휠·끌기는 한 장씩) |
| `supabase/schema.sql` | Supabase 테이블·RLS·권한 (`kv`: 방문 기록·메모, `sync_requests`: 폰 동기화 요청). SQL Editor에서 다시 실행해도 안전 |
| `scripts/com.matjip.weekly.plist` | 예전 맥의 주간 자동 수집 설정. 더 안 씀 |
| `supabase/functions/transit` | 배포 후 대중교통 중계 (dev_server의 /api/transit 과 같은 일) |
| `.github/workflows/pages.yml` | app/ → GitHub Pages 배포 |
| `data/` | 네이버 원본·수집 캐시·기록·로그(`sync.log`). **공개 저장소에 올리지 않음** (.gitignore) |

## 데이터 흐름

1. `data/raw/{폴더}.json` — 네이버 공유 폴더 API에서 받은 저장 목록 (`sync.py`가 다시 받음). 폴더는 `data/shares.json`에 넣은 것 전부(2026-11-25: 맛집리스트·찐맛집·홍어·짬뽕·제주도). 같은 가게가 여러 폴더에 있으면 한 곳으로 합침. 폴더를 더하려면 네이버 앱에서 폴더를 공개 → 공유 링크(naver.me) → 넘어간 주소 끝의 32자 ID를 shares.json에
   - 공유 폴더 ID·링크는 `data/shares.json`에만 둔다 (공개 저장소에 올리면 누구나 저장 목록·닉네임을 볼 수 있음). 새 PC면 이 파일을 옮겨 올 것
   - API: `https://pages.map.naver.com/save-pages/api/maps-bookmark/v3/shares/{shareId}/bookmarks?start=0&limit=5000`
2. `collect_naver.py` → `data/naver/{sid}.json` + `data/naver/history/{sid}.jsonl`(수집할 때마다 스냅샷)
3. `fill_phones.py` → 같은 json 에 `phoneSearch`
4. `build_data.py` → `app/places.js` 등

**수집 기준 (2026-11-24 결정):** 후기·별점·메뉴는 가게를 처음 저장했을 때 1번만 받는다. 주간 자동 수집은 없앴고, 앱의 '↻ 동기화' 버튼(목록 화면 '전국 954곳' 옆)을 누를 때만 `sync.py`가 돈다. 전부 다시 받고 싶을 때만 `python3 scripts/collect_naver.py --refresh`.

## 주의 (겪은 문제)

- **Python urllib 요청은 네이버가 429로 막는다.** 모든 요청은 `curl` subprocess로 보낸다.
- 요청 간격 2.5~4초. 더 빠르면 차단된다.
- 수집 중 컴퓨터가 잠들면 네트워크가 끊겨 대량 실패한다. 실패해도 기존 데이터는 덮어쓰지 않게 되어 있다 (목록 받기 실패 시에도 예전 목록 유지).
- **Windows 인코딩:** 파일 읽기·쓰기는 반드시 `encoding="utf-8"`, 쓰기는 `newline="\n"` (안 하면 cp949·CRLF로 저장됨). 하위 스크립트는 `python -I -X utf8`로 실행 (`-I`는 `PYTHONUTF8` 환경변수를 무시함).
- 네이버 대중교통(`map.naver.com/p/api/directions/pubtrans`)은 `departureTime=YYYY-MM-DDTHH:MM:SS`(한국 시간)을 받는다 (중계는 `time` 파라미터로 넘김). CORS가 없어 브라우저에서 직접 못 부른다 → 중계 필요.
- 블로그 글에 다른 가게 전화번호가 섞인다 → 주소 일치할 때만 채택 (이름만 맞는 건 버림).
- 제철 정규식은 오탐 주의: '메밀면에대하여'→대하, 수육→보쌈 같은 사례로 고쳐 왔다. 고칠 땐 `season.js` 정규식을 고친다 (수동 태그 기능은 만들지 않기로 결정). 새 항목을 넣으면 실제로 어느 가게·메뉴에 걸리는지 확인할 것 (하모→하모니, 도미→도미노 같은 함정).
- 수집은 한 PC에서만 돌린다 (두 곳에서 돌면 네이버 요청이 두 배).
- `/api/sync` POST는 `X-Hanjeom: sync` 헤더가 있어야 받는다 (다른 사이트가 몰래 부르는 것 방지).
- **행정동 경계 출처 표시 필수:** vuski/admdongkor(CC BY 4.0) + 통계청 SGIS(공공누리 1유형). 앱에서는 동이 보일 때 지도 왼쪽 아래 `.attr`에 표시. 지우지 말 것. 원본 geojson(34.6MB)은 `data/geo_raw/`에만 둔다.
- 브라우저 창이 숨겨져 있으면 requestAnimationFrame이 거의 안 돌아 지도 애니메이션이 멈춘 것처럼 보인다 (테스트할 때 착각 주의).

## 현재 상태 (2026-11-24)

약속·투표(2026-11-24): 로그인하면 첫 화면에 '🍻 약속 잡기' → 이름·인원 정하면 링크(`#v=<32자 ID>`). 친구는 로그인 없이 이름+출발지(`geocode` 재사용, 좌표는 소수 3자리로 저장). 정한 인원이 다 모이면 참여자 기기 하나가 `claim_compute`로 계산을 맡음(2분 넘게 멈추면 다른 기기가 이어받음): 954곳을 거리 추정 합으로 6곳 → 6곳×인원만 실제 경로(새 요청마다 0.6초 쉼) → 합 작은 3곳. 모두 투표하면 자동 마감(표 많은 곳, 같으면 이동시간 합 작은 곳), 같은 링크가 결과 화면. 만든 사람은 '지금 n명으로 시작', 투표 중엔 '투표 안 한 사람 빼고 지금 마감하기'(`close_now`, 1표 이상) 가능. 만들 때 '먹고 싶은 것'(검색어, `votes.want`)을 쓰면 앱 검색과 같은 방식(`p.hay`)으로 그걸 파는 곳 중에서만 후보를 고름. 후보 화면은 평균 이동시간으로 보여 줌(순서는 합 기준). 참여할 때 '현재 위치'는 `placeName`이 행정동 경계로 '성동구 성수2가3동'처럼 바꿔 저장. 공유는 메시지 없이 링크만(`navigator.share({url})`), 카톡 미리보기는 `index.html`의 og 태그 + `app/og.png`(흰 바탕 로고 800×420). 이 기기가 누구인지는 localStorage `vote:{id}` = {pid, token}. 시험 때 숨겨진 창에선 CSS 애니메이션이 멈춰 클릭 좌표가 어긋남(실사용 문제 아님).

구현·확인됨: 전국 지도(지역 누르면 그 지역만 확대, 휠·두 손가락 핀치로 자유 확대 1~12배 + 확대 중 드래그 이동 + '↺ 전체 보기', 직접 확대한 상태에선 탭이 도 대신 핀을 고름, 1.6배 넘게 확대하면 시·군·구 경계와 이름(서울 구 포함)이 나타남 — 이름은 저장한 가게 많은 곳부터 겹치지 않게 배치, '성남시분당구'는 '분당구'·'포항시북구'는 '포항 북구'로 표시, `drawZoomDetail`; 시·군·구를 누르면 그 지역이 지도에 꽉 차게 자동 확대되고 행정동 경계·이름이 나옴, `loadDongs`·`fitArea`·`drawDongs`), 지역 드릴다운(도→시·군·구), 유형 19종 필터, 검색(메뉴·후기 메뉴 포함, 동 이름도 — `build_data.py`가 좌표로 행정동을 찾아 `p.dong`에 넣고 `dongNames`가 '자양3동'→'자양동', '성수1가1동'→'성수동'·'성수1가'로 넓힘. 동 이름과 딱 맞으면('압구정'처럼 '동'을 빼도) 한 구에 모여 있을 때 `dongArea`로 그 구로 확대. 지하철역: '○○역'이거나 결과가 0곳이면 `maybeStation`이 OpenStreetMap으로 '○○역' 위치를 찾아(친 글자만 보냄, 결과 기억) 800m 안 가게를 가까운 순 + '🚇 ○○역에서 걸어서 n분', 검색어가 있으면 지도가 보는 지역과 상관없이 항상 전국 결과, 새 검색은 유형·제철 조건을 풀고 지도를 전국으로, 가게 이름이 맞는 곳이 먼저), 로고 누르면 처음 화면(검색·필터·지역·확대 초기화), 이달 제철 음식 카드 → 가게(대표 메뉴 기준), 다음 달 미리보기·이번 달로 끝나는 제철, 산지 표시, 제철 '절정' 배지와 한 줄 팁, 첫 화면 '지금 갈 만한 곳'(현재 위치 근처 제철·오늘 영업), 가게 하나 공유(상세 '공유' → `#p=<가게 id>` 링크, 열면 그 가게 상세, `placeFromHash`), 가게 상세(추천 메뉴 막대, 상호·주소·전화 — 대표 메뉴·키워드는 13회차에 뺌), 휴무·체인·본점 배지, 내 등급 S·A·B·C(2026-11-25, 방문 기록 버튼을 대신함: 상세에서 로그인한 나만 매기고 같은 등급을 다시 누르면 지움, 친구도 봄. 이름 옆 글자 배지 — S 색 흐름+빛+커졌다 작아짐+✦, A 금색에 빛 지나감, B 파랑 물결, C 회색. S·A 핀은 조금 크게. 유형 칩 줄의 제철 다음에 등급 칩(S·A·B·C, 매긴 곳 있을 때만) — 누르면 그 등급만(`state.grade`), 다시 누르면 풂. 등급 높은 가게의 유형을 추천 순서에 가중 S4·A3·B2·C1. 처음 로그인할 때 예전 방문 횟수를 한 번만 등급으로 옮김: 20+ S · 10+ A · 5+ B · 그 밖 C, `migrateVisits`), 가게당 메모 1개(로그인했을 때만 보임, `kv`), 검색창 예시는 그달 제철 상위 2개로 자동, 대중교통 실제 시간(로컬), 큰 뒤로가기(브라우저 뒤로·스와이프·Esc), 동기화 버튼(로컬).

제철표: 53종. 11월 기준 도루묵·양미리·도치·곰치·숭어·홍어·새조개·가자미·벚굴·참돔·성게·병어·농어·갯장어 추가(2026-11-24). 대게는 금어기(6~11월) 반영해 12~4월로 고침.

디자인: iOS 기본 스타일 확정. 지도는 흰 땅·연한 회청색 바다 (파란 바다·초록 산줄기는 해봤다가 "그림판 같다"고 되돌림, 애플 지도 스타일도 되돌림). B·C 시안은 폐기.
'찐맛집' 개념은 뺐다(칩·태그·보라 핀·정렬 가중 모두). 저장 폴더 이름도 화면에 안 보임. 자주 가는 곳은 방문 횟수 태그로 드러난다.
로고(`.logo`): 2026-11-25부터 'gireumjang'(사용자 인스타 부계 '기름장' 영문 로고, 흰 글자 + 노란 기름 방울 2개). 원본은 검은 배경이라 배경을 투명하게 만든 `app/logo-dark.png`(원색, 다크 모드)와 `app/logo-light.png`(글자만 검정, 방울은 노랑 그대로, 라이트 모드) 두 장(방울은 뺀 글자만). 방울은 `app/drop0.png`(j 위, 말랑하게 출렁 `dwobble`)·`drop1.png`(g 끝, 맺혔다가 똑 떨어짐 `drip`)를 % 위치로 겹침, 동작 줄이기면 멈춤. 탭 아이콘은 노란 기름 방울(`favicon.svg`·`favicon-32.png`, 아이폰 홈 화면은 흰 바탕 `apple-touch-icon.png` 180px). 가로로 긴 모양이라 높이는 아이폰 44px·넓은 화면 54px. 이미지를 바꾸면 `index.html`의 `?v=` 숫자를 올릴 것(브라우저·카톡 캐시). 카톡 미리보기 `og.png`는 흰 바탕 800×420에 로고를 가운데 400px 안에 둠(카톡이 정사각형으로 잘라도 보이게). 위쪽 제목(`#title`)은 첫 화면에서 '전국', 그다음 지역 이름.

제철 범위(12회차 결정): 대표 메뉴만 — 네이버 메뉴 앞 3개 + 후기 언급 상위 3개 + 가게 이름 (`season.js`의 `TOP_MENUS`, `TOP_REVIEW_MENUS`). 11월 284곳 → 187곳. 검색은 여전히 모든 메뉴를 본다.
폐업: 앱에서 따로 표시 안 함. 네이버 저장 목록에서 `available: false`(없는 장소)인 곳은 빌드·수집에서 뺌(2026-11-25, 8곳). 네이버에서 저장을 지우고 동기화하면 빌드에서 빠진다 (build_data는 raw 목록에 있는 가게만 만든다).

## 할 일 (우선순위 순)

- [x] **배포 완료 (2026-11-24):** https://gireumjang.github.io/ ← 저장소 https://github.com/gireumjang/gireumjang.github.io (공개, main. 2026-11-25에 msroe84-web/hanjeom 에서 조직 gireumjang 으로 옮김, 예전 주소는 안 열림). `app/` 이나 워크플로가 바뀐 push 때마다 GitHub Actions가 자동 배포. 액션은 upload-pages-artifact@v5 + deploy-pages@v5 짝, 올리기(build)·게시(deploy)는 반드시 다른 job (한 job이면 'No artifacts named github-pages'로 자주 실패)
  - 공개 저장소라 개인 정보 주의: 네이버 공유 폴더 ID·닉네임은 올리지 않음(ID는 `data/shares.json`), 옛 plist는 .gitignore
- [x] **Supabase 연결 (2026-11-24):** 프로젝트 `oenmrkgudxjdenegjibj` (서울). 로그인은 이메일+비밀번호(메일 템플릿은 SMTP 없이 못 고쳐서 OTP 코드 방식 포기), 이메일 확인 끔, 새 가입 막음(계정 1개). 목록 위 '☁︎ 로그인' 버튼
  - 방문 기록·메모: `kv` 테이블. 기기에서 처음 로그인할 때만 기존 기록과 합치고(방문은 가게별 더 많은 쪽, 메모는 합침), 그다음부턴 클라우드 기준. 로그인 안 하면 예전처럼 localStorage만
  - 폰 동기화: 로컬 서버가 없으면 동기화 버튼이 `sync_requests`에 요청 → PC dev_server가 1분마다 확인해 처리(시험: 104초에 완료). 이 프로젝트는 새 테이블 권한을 자동으로 안 줘서 schema.sql에 grant 필요
- [x] Supabase `transit` 함수 배포 (2026-11-24, 대시보드 편집기로 — `index.ts` 파일을 지우면 'Entrypoint path does not exist'). Verify JWT 끔, `ALLOW_ORIGIN=https://gireumjang.github.io` (다른 주소는 403). 앱은 로컬이면 dev_server `/api/transit`, 배포 사이트면 `config.js`의 `transitProxy`. 함수 코드를 고치면 대시보드에 다시 붙여넣어 배포해야 함
- [x] 약속·투표 (2026-11-24): 출발지 모이면 이동시간 합 최소 3곳 자동 추천 → 전원 투표 시 자동 마감 → 같은 링크가 결과 화면 (`supabase/votes.sql`)
- [x] (13회차) 상세: 별점만 이름 옆에 작게(`.drate`), 후기 수·블로그 수·한 줄 요약 뺌
- [x] (13회차) 아이폰 핀 묶기: 화면 폭 720 미만에서만, 34px 칸마다 3개 이상이면 숫자 동그라미(`computeClusters`·`drawClusters`, 제철 있으면 주황). 거의 포개진 동그라미는 합침, 누르면 그 자리 2.6배 확대. 선택한 핀은 안 묶음
- [x] (13회차) 약속: 날짜+시간(`votes.meet_at`, 그 시간에 안 여는 곳 제외 — 3곳 미만이면 영업시간 무시, 경로는 `departureTime`=약속 − 대략 시간 − 5분) · 만든 사람이 '🔄 다른 후보 보기'(`reroll`, 지금 3곳을 `votes.skip`에 넣고 다시 계산, 투표 지워짐)
- [x] (13회차) 친구가 내 지도를 볼 때 단골 표시 → 내 등급(S·A·B·C)으로 바꿔서 보이게 (메모는 나만)
- [ ] (13회차) 이번 달 새로 시작한 제철 음식에 'NEW' 배지

## 작업 방식 메모

- 사용자는 한국어로 대화. 아이폰 기준 디자인, iOS 스프링 애니메이션 느낌 선호.
- 화면 변경 후에는 브라우저에서 아이폰(375×812)·넓은 화면 둘 다 확인.
- **PC 마우스로도 확인:** 가로로 넘기는 줄(`.chips`·`.foodstrip`·`.dstrip`)은 아이폰은 손가락으로 밀지만 PC는 휠·끌기로만 넘어간다 (`HSEL` 처리). 새로 가로 줄을 만들면 `HSEL`에 넣고, 실제 휠·끌기로 끝까지 보이는지 확인할 것 (2026-11-25 날짜·시간 칩이 PC에서 안 넘어가 뒤쪽 시간이 안 보였음).
- 확인용 링크는 claude.ai 아티팩트 말고 localhost 주소로 준다 (사용자가 브라우저에서 직접 열어봄).
- 네이버로 넘기는 링크는 넣지 않는다 (정보는 앱 안에서 끝). 예외: 상세의 '길찾기'(2026-11-25) — 네이버지도·카카오맵·애플 지도의 **길안내 화면**만 연다(`openRoute`, 폰은 앱 주소 `nmap://`·`kakaomap://`, 앱이 없거나 PC면 웹 주소). 가게 소개 페이지로는 보내지 않는다.
