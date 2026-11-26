-- 「한 점」 가게마다 내가 찍은 사진 최대 10장. Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run. 다시 실행해도 안전.
-- says.sql 을 먼저 실행해 둘 것. says.photo 에 사진 이름을 쉼표로 (최대 10장, 첫 장이 대표). 파일은 photos/{가게}/{이름}.jpg
-- 사진 파일은 Storage 'photos' 버킷: 누구나 주소로 볼 수 있고(공개), 올리고 바꾸고 지우는 건 로그인한 본인만.
-- kv · sync_requests · votes · grades 테이블은 건드리지 않는다.

alter table public.says add column if not exists photo text not null default '';
-- 사진 이름 목록 길이 제한 (10장이면 약 100자). 예전 제한(80자, 5장용)은 지우고 새로. 올린 사진·한마디는 그대로 남는다
do $$ declare c record; begin
  for c in select conname from pg_constraint where conrelid = 'public.says'::regclass and contype = 'c' and pg_get_constraintdef(oid) like '%photo%' loop
    execute format('alter table public.says drop constraint %I', c.conname);
  end loop;
end $$;
alter table public.says add constraint says_photo_len check (char_length(photo) <= 200);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('photos', 'photos', true, 3145728, array['image/jpeg'])
on conflict (id) do update set public = true, file_size_limit = 3145728, allowed_mime_types = array['image/jpeg'];

drop policy if exists "photos: 로그인한 나 보기" on storage.objects;
create policy "photos: 로그인한 나 보기" on storage.objects for select to authenticated using (bucket_id = 'photos');
drop policy if exists "photos: 로그인한 나 올리기" on storage.objects;
create policy "photos: 로그인한 나 올리기" on storage.objects for insert to authenticated with check (bucket_id = 'photos');
drop policy if exists "photos: 본인만 바꾸기" on storage.objects;
create policy "photos: 본인만 바꾸기" on storage.objects for update to authenticated using (bucket_id = 'photos' and owner = auth.uid()) with check (bucket_id = 'photos');
drop policy if exists "photos: 본인만 지우기" on storage.objects;
create policy "photos: 본인만 지우기" on storage.objects for delete to authenticated using (bucket_id = 'photos' and owner = auth.uid());
