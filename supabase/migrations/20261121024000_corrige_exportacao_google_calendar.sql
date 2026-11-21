-- O limite superior de uma repetição em regex no PostgreSQL é 255.
set local lock_timeout = '5s';

alter table public.google_calendar_event_exports
  drop constraint google_calendar_event_exports_google_event_id_check,
  add constraint google_calendar_event_exports_google_event_id_check
    check (char_length(google_event_id) between 5 and 1024 and google_event_id ~ '^[a-v0-9]+$');
