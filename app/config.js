// 배포 설정. 로컬(localhost)에서는 dev_server.py 의 /api/transit 을 자동으로 씀.
// 배포 후 Supabase 함수를 만들면 transitProxy 에 그 주소를 넣는다.
//   예: "https://<프로젝트>.supabase.co/functions/v1/transit"
window.HANJEOM_CONFIG = {
  transitProxy: "",
};
