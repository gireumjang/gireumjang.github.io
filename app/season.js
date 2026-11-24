// 월별 제철 재료 → 식당 이름/메뉴/후기 메뉴에서 찾을 패턴.
// months: 제철 기간, peak: 가장 맛있는 달(없으면 생략), tip: 산지·먹는 법 한 줄.
window.SEASON_ITEMS = {
  굴:     { emoji: "🦪", re: /굴(?!다리|비)|석화/, months: [10, 11, 12, 1, 2], peak: [12, 1], note: "찬 바람 불 때 살이 차오르는 바다의 우유", tip: "통영·거제는 생굴, 보령 천북은 껍데기째 굴구이", origin: "경남:통영시|경남:거제시|충남:보령시|충남:서산시" },
  방어:   { emoji: "🐟", re: /방어/, months: [11, 12, 1, 2], peak: [12, 1], note: "겨울 대방어는 기름이 올라 고소함이 절정", tip: "8kg 넘는 대방어일수록 좋다. 뱃살·배꼽살·사잇살을 부위별로", origin: "제주:서귀포시|제주:제주시" },
  과메기: { emoji: "🐟", re: /과메기/, months: [11, 12, 1], peak: [12], note: "해풍에 말리는 포항 겨울 별미", tip: "요즘은 꽁치가 대부분. 김·쪽파·마늘·초장에 싸서", origin: "경북:포항시" },
  도루묵: { emoji: "🐟", re: /도루묵/, months: [11, 12, 1], peak: [11, 12], note: "동해안 초겨울, 알이 꽉 차는 때", tip: "알 밴 암컷은 구이, 수컷은 찌개로", origin: "강원:고성군|강원:속초시|강원:양양군" },
  양미리: { emoji: "🐟", re: /양미리/, months: [11, 12, 1], peak: [12], note: "그물째 걸어 말리는 속초 겨울 풍경", tip: "속초 동명항 연탄불 구이가 정석", origin: "강원:속초시" },
  도치:   { emoji: "🐡", re: /도치|심퉁이|뚝지/, months: [12, 1, 2], peak: [1, 2], note: "못생겨도 맛은 동해 겨울 으뜸", tip: "알탕과 데친 숙회로", origin: "강원:속초시|강원:삼척시" },
  곰치:   { emoji: "🐟", re: /곰치|물곰|물메기|꼼치/, months: [12, 1, 2, 3], peak: [1, 2], note: "흐물흐물한 살이 국물에 풀리는 해장국", tip: "삼척은 김치 넣은 곰칫국, 통영은 맑은 물메기탕", origin: "강원:삼척시|경남:통영시" },
  숭어:   { emoji: "🐟", re: /숭어/, months: [11, 12, 1, 2], peak: [12, 1], note: "겨울 숭어는 기름이 올라 쫄깃하다", tip: "두툼하게 썬 회로", origin: "전남:무안군|전남:신안군" },
  홍어:   { emoji: "🐟", re: /홍어/, months: [12, 1, 2, 3], peak: [1, 2], note: "겨울 흑산도 참홍어", tip: "삭힌 정도가 가게마다 달라 물어보고 주문", origin: "전남:신안군|전남:목포시" },
  새조개: { emoji: "🐚", re: /새조개/, months: [1, 2, 3], peak: [2, 3], note: "늦겨울 서해 한철 조개", tip: "홍성 남당항, 샤부샤부로 살짝 데쳐서", origin: "충남:홍성군|충남:보령시" },
  가자미: { emoji: "🐟", re: /가자미/, months: [12, 1, 2, 3], peak: [1, 2], note: "동해 참가자미 뼈째회", tip: "세꼬시로 썰어 초장, 남은 건 미역국", origin: "강원:속초시|경북:포항시" },
  대게:   { emoji: "🦀", re: /대게|킹크랩|홍게/, months: [12, 1, 2, 3, 4], peak: [2, 3], note: "살이 꽉 차는 겨울~초봄 제철", tip: "6~11월은 금어기. 다리 끝까지 살 찬 박달대게가 최상", origin: "경북:영덕군|경북:울진군" },
  꼬막:   { emoji: "🐚", re: /꼬막/, months: [11, 12, 1, 2, 3], peak: [12, 1], note: "벌교 참꼬막은 찬 바다에서 쫄깃해진다", tip: "참꼬막은 살짝만 삶아 핏기가 남게", origin: "전남:보성군|전남:여수시" },
  홍합:   { emoji: "🐚", re: /홍합|섭/, months: [11, 12, 1, 2], note: "겨울 홍합탕은 국물부터 달다", tip: "자연산 참홍합(섭)은 섭국으로", origin: "강원:속초시|강원:양양군" },
  대구:   { emoji: "🐟", re: /대구(탕|뽈|찜|지리|매운탕)/, months: [12, 1, 2], peak: [12, 1], note: "한겨울 산란기 전 가장 맛있는 대구", tip: "거제 외포항, 맑은 대구탕과 대구뽈찜", origin: "경남:거제시|경남:창원시" },
  생태:   { emoji: "🍲", re: /생태|동태/, months: [11, 12, 1, 2], note: "추울수록 생각나는 시원한 찌개", tip: "얼리지 않은 생태는 겨울에만", origin: "강원:고성군|강원:속초시" },
  아귀:   { emoji: "🐡", re: /아귀|아구/, months: [12, 1, 2], note: "겨울 아귀는 간까지 고소하다", tip: "간(애)이 가장 고소한 때, 수육으로도", origin: "경남:창원시|인천:중구" },
  매생이: { emoji: "🌿", re: /매생이/, months: [12, 1, 2], peak: [1], note: "겨울 한철만 나는 남도 바다 이끼", tip: "굴 넣은 매생이국, 김이 안 나도 뜨거우니 천천히", origin: "전남:장흥군|전남:완도군" },
  복어:   { emoji: "🐡", re: /복어|복집|복국|복지리/, months: [11, 12, 1, 2], note: "겨울 복국으로 속 풀기", tip: "참복은 지리로, 반드시 복어 자격 있는 곳에서", origin: "부산:해운대구|경남:통영시" },
  꽃게:   { emoji: "🦀", re: /꽃게/, months: [4, 5, 6, 9, 10, 11], note: "봄엔 알 찬 암게, 가을엔 살 찬 수게", tip: "6월 말~8월 중순은 금어기", origin: "인천:옹진군|인천:중구|충남:태안군" },
  전어:   { emoji: "🐟", re: /전어/, months: [9, 10], peak: [9], note: "집 나간 며느리도 돌아온다는 가을 전어", tip: "뼈째 썬 회, 통째 소금구이", origin: "전남:광양시|전남:보성군|충남:서천군" },
  대하:   { emoji: "🦐", re: /대하(?!여)/, months: [9, 10, 11], peak: [10], note: "가을 서해 대하 소금구이", tip: "자연산은 9~10월 잠깐, 대부분은 양식 흰다리새우", origin: "충남:홍성군|충남:태안군" },
  삼치:   { emoji: "🐟", re: /삼치/, months: [10, 11, 12, 1], peak: [11, 12], note: "기름진 늦가을 삼치", tip: "큰 삼치일수록 맛있다. 여수·거문도는 삼치회", origin: "전남:여수시|전남:완도군" },
  벚굴:   { emoji: "🦪", re: /벚굴/, months: [2, 3, 4], peak: [3], note: "섬진강 벚꽃 필 무렵의 강굴", tip: "손바닥만 한 굴을 구이나 찜으로", origin: "경남:하동군|전남:광양시" },
  주꾸미: { emoji: "🐙", re: /주꾸미|쭈꾸미/, months: [3, 4], note: "알이 꽉 찬 봄 주꾸미", tip: "알 찬 머리까지 살짝 데쳐서", origin: "충남:서천군|충남:보령시" },
  도다리: { emoji: "🐟", re: /도다리/, months: [3, 4], note: "봄 도다리쑥국", tip: "통영 도다리쑥국은 3~4월 한정", origin: "경남:통영시" },
  참돔:   { emoji: "🐟", re: /참돔|도미(?!노)/, months: [3, 4, 5], peak: [4], note: "벚꽃 필 때 붉게 오르는 봄 도미", origin: "경남:통영시|전남:여수시" },
  바지락: { emoji: "🐚", re: /바지락/, months: [3, 4, 5], note: "봄 바지락 칼국수", origin: "인천:옹진군|전북:군산시" },
  멍게:   { emoji: "🪸", re: /멍게|우렁쉥이/, months: [4, 5, 6], note: "봄~초여름 향 진한 멍게", origin: "경남:통영시|경남:거제시" },
  성게:   { emoji: "🌰", re: /성게|우니(?!버)/, months: [5, 6, 7], peak: [6], note: "초여름 노랗게 차오르는 성게알", tip: "제주 해녀 성게는 5~6월, 성게비빔밥이나 미역국", origin: "제주:제주시|강원:고성군" },
  병어:   { emoji: "🐟", re: /병어/, months: [5, 6], note: "초여름 신안 병어", tip: "뼈째 회, 감자 넣은 병어조림", origin: "전남:신안군" },
  농어:   { emoji: "🐟", re: /농어/, months: [6, 7, 8], peak: [7], note: "여름 농어는 보약", origin: "충남:보령시|전남:여수시" },
  갯장어: { emoji: "🐍", re: /갯장어|하모(?!니)/, months: [6, 7, 8], peak: [7, 8], note: "여수 하모 샤부샤부", tip: "뼈를 잘게 칼집 낸 갯장어를 육수에 살짝", origin: "전남:여수시|전남:고흥군" },
  민어:   { emoji: "🐟", re: /민어/, months: [6, 7, 8], peak: [7, 8], note: "복날 보양 1순위 민어", tip: "부레와 뱃살이 별미, 목포 민어거리", origin: "전남:목포시|전남:신안군" },
  장어:   { emoji: "🐍", re: /장어/, months: [6, 7, 8], note: "여름 보양식", origin: "전북:고창군|부산:기장군" },
  전복:   { emoji: "🐚", re: /전복/, months: [7, 8, 9], note: "여름 전복은 살이 오른다", origin: "전남:완도군|제주:제주시" },
  냉면:   { emoji: "🍜", re: /냉면|막국수|밀면|콩국수/, months: [6, 7, 8], note: "더운 날 줄 서는 면 요리", origin: "강원:춘천시|부산:중구" },
  조개:   { emoji: "🐚", re: /조개/, months: [11, 12, 1, 2, 3], note: "찬 바다 조개가 통통하다" },
  낙지:   { emoji: "🐙", re: /낙지/, months: [9, 10, 11], peak: [10], note: "가을 낙지는 소도 일으킨다", tip: "무안 뻘낙지는 탕탕이·연포탕으로", origin: "전남:무안군|전남:목포시" },
  고등어: { emoji: "🐟", re: /고등어/, months: [10, 11, 12], peak: [11], note: "찬 바람에 기름이 오르는 고등어", tip: "고등어회는 산지(제주·부산)에서", origin: "제주:제주시|부산:서구" },
  갈치:   { emoji: "🐟", re: /갈치/, months: [7, 8, 9, 10], note: "제주 은갈치 제철", origin: "제주:제주시|제주:서귀포시" },
  한치:   { emoji: "🦑", re: /한치/, months: [6, 7, 8], note: "제주 여름 한치 물회", origin: "제주:제주시|제주:서귀포시" },
  오징어: { emoji: "🦑", re: /오징어(?!참치)/, months: [8, 9, 10], note: "동해 오징어가 살 오르는 때", origin: "강원:속초시|강원:강릉시|경북:울릉군" },
  삼계탕: { emoji: "🍗", re: /삼계탕|백숙|반계탕/, months: [7, 8], note: "복날 몸보신" },
  추어탕: { emoji: "🍲", re: /추어/, months: [9, 10], note: "살찐 가을 미꾸라지", origin: "전북:남원시" },
  버섯:   { emoji: "🍄", re: /송이|능이|버섯/, months: [9, 10], note: "가을 송이·능이 향이 짙을 때", origin: "강원:양양군|경북:봉화군" },
  나물:   { emoji: "🌱", re: /나물|두릅|냉이|달래|산채|곤드레/, months: [3, 4, 5], note: "봄 향 가득한 산나물" },
  보쌈:   { emoji: "🥬", re: /보쌈/, months: [11, 12], note: "김장철엔 갓 담근 김치에 보쌈" },
  전골:   { emoji: "🍲", re: /전골|샤브|어탕/, months: [12, 1, 2], note: "추운 날 끓여 먹는 냄비 요리" },
  팥죽:   { emoji: "🥣", re: /팥죽|동지/, months: [12], note: "동지엔 팥죽 한 그릇" },
  떡국:   { emoji: "🥣", re: /떡국|떡만두국/, months: [1], note: "새해 첫 끼" },
  콩국수: { emoji: "🍜", re: /콩국수/, months: [6, 7, 8], note: "여름 한정 콩국수" },
  우럭:   { emoji: "🐟", re: /우럭/, months: [3, 4, 5], note: "봄 우럭은 살이 단단하다", origin: "충남:태안군|인천:옹진군" },
};

// "경남:통영시|…" → [{prov, area}]
window.originOf = function (key) {
  const it = window.SEASON_ITEMS[key];
  if (!it || !it.origin) return [];
  return it.origin.split("|").map((x) => { const [prov, area] = x.split(":"); return { prov, area, label: area.replace(/(시|군|구)$/, "") }; });
};

// 대표 메뉴일 때만 제철로 친다: 네이버 메뉴 앞 3개 + 후기 언급 상위 3개 + 가게 이름 (곁들임 메뉴는 제외)
const TOP_MENUS = 3, TOP_REVIEW_MENUS = 3;
window.seasonTags = function (place, month) {
  const sources = [
    ...(place.menus || []).slice(0, TOP_MENUS).map((m) => ({ text: m.name, menu: m })),
    ...(place.reviewMenus || []).slice(0, TOP_REVIEW_MENUS).map((m) => ({ text: m.name, review: m })),
    { text: place.name, isName: true },
  ];
  const out = [];
  for (const [key, item] of Object.entries(window.SEASON_ITEMS)) {
    if (!item.months.includes(month)) continue;
    const hit = sources.find((s) => s.text && item.re.test(s.text));
    if (hit) out.push({ key, ...item, via: hit });
  }
  return out;
};
