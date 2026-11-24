#!/bin/zsh
# 주간 수집 뒤 바뀐 지도 데이터(app/)만 GitHub 에 올린다 → Actions 가 Pages 로 배포.
# 원격 저장소(origin)가 없으면 아무것도 하지 않는다.
cd "$(dirname "$0")/.." || exit 0
git remote get-url origin >/dev/null 2>&1 || { echo "publish: origin 없음, 건너뜀"; exit 0; }
git add app
git diff --cached --quiet && { echo "publish: 바뀐 것 없음"; exit 0; }
git commit -m "주간 데이터 갱신 $(date +%Y-%m-%d)" && git push origin HEAD:main
