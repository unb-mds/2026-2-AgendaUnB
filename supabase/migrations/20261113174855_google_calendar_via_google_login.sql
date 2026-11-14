-- Google delegates state/PKCE to Supabase Auth in the login flow.
drop table public.google_calendar_oauth_states;

-- Existing credentials came from a separate OAuth client. Keep the calendar
-- association so the same Google identity can resume after a new login.
update public.google_calendar_connections set granted_scope = '';
