// 배포 설정. 로컬(localhost)에서는 dev_server.py 의 /api/transit 을 자동으로 씀.
// transitProxy: Supabase 함수(transit)를 배포하면 "https://<프로젝트>.supabase.co/functions/v1/transit"
// supabaseKey 는 브라우저에 공개해도 되는 publishable 키 (테이블은 RLS로 본인만 접근). secret 키는 절대 여기 넣지 않는다.
window.HANJEOM_CONFIG = {
  transitProxy: "https://oenmrkgudxjdenegjibj.supabase.co/functions/v1/transit",
  supabaseUrl: "https://oenmrkgudxjdenegjibj.supabase.co",
  supabaseKey: "sb_publishable_TxguZHI5VLZiYhpTIhD2ng_dQNlGiWB",
};
