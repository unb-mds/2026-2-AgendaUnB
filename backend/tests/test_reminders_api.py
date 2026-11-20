from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from src.database.models import PersonalEvent, PublicEvent, Reminder
from src.main import app
from src.middlewares.auth import CurrentUser, get_current_user

REMINDERS = "/api/v1/me/reminders"
START = datetime(2030, 4, 21, 3, tzinfo=timezone.utc)


def test_lists_only_own_fired_reminders_with_stable_pagination(api):
    client, sessions, authenticated, _ = api
    owner = authenticated["value"].id
    with sessions.begin() as db:
        private = PersonalEvent(user_id=owner, title="Compromisso", starts_at=START)
        public = PublicEvent(title="Palestra", description="Descrição", starts_at=START, status="aprovado")
        db.add_all([private, public])
        db.flush()
        common = {"event_starts_at": START, "scheduled_for": START - timedelta(days=1)}
        db.add_all([
            Reminder(id=UUID(int=1), user_id=owner, event_kind="pessoal", personal_event_id=private.id,
                     status="disparado", fired_at=START, **common),
            Reminder(id=UUID(int=2), user_id=owner, event_kind="publico_salvo", public_event_id=public.id,
                     status="disparado", fired_at=START, **common),
            Reminder(user_id=owner, event_kind="pessoal", personal_event_id=private.id, **common),
            Reminder(user_id=uuid4(), event_kind="publico_salvo", public_event_id=public.id,
                     status="disparado", fired_at=START, **common),
        ])
        private_id, public_id = private.id, public.id

    first = client.get(REMINDERS, params={"limit": 1})
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    public_item, = first.json()
    assert (public_item["id"], public_item["event_kind"], public_item["event_id"], public_item["title"]) == (
        str(UUID(int=2)), "saved_public", str(public_id), "Palestra",
    )
    private_item, = client.get(REMINDERS, params={"limit": 1, "offset": 1}).json()
    assert (private_item["id"], private_item["event_kind"], private_item["event_id"], private_item["title"]) == (
        str(UUID(int=1)), "personal", str(private_id), "Compromisso",
    )
    assert private_item["scheduled_at"].startswith("2030-04-20T03:00:00")
    assert private_item["starts_at"].startswith("2030-04-21T03:00:00")
    assert private_item["read_at"] is None
    assert client.get(REMINDERS, params={"offset": 2}).json() == []
    assert client.get(REMINDERS, params={"limit": 0}).status_code == 422
    assert client.get(REMINDERS, params={"offset": -1}).status_code == 422

    with sessions.begin() as db:
        db.get(PublicEvent, public_id).status = "rejeitado"
    assert client.get(REMINDERS).json()[0]["title"] is None


def test_read_is_idempotent_and_never_updates_another_account_or_pending_reminder(api):
    client, sessions, authenticated, _ = api
    owner = authenticated["value"].id
    other = uuid4()
    with sessions.begin() as db:
        public = PublicEvent(title="Palestra", description="Descrição", starts_at=START, status="aprovado")
        db.add(public)
        db.flush()
        common = {"event_kind": "publico_salvo", "public_event_id": public.id,
                  "event_starts_at": START, "scheduled_for": START - timedelta(days=1)}
        own = Reminder(user_id=owner, status="disparado", fired_at=START, **common)
        pending = Reminder(user_id=owner, **common)
        foreign = Reminder(user_id=other, status="disparado", fired_at=START, **common)
        db.add_all([own, pending, foreign])
        db.flush()
        own_id, pending_id, foreign_id = own.id, pending.id, foreign.id

    for reminder_id in (pending_id, foreign_id, uuid4()):
        response = client.put(f"{REMINDERS}/{reminder_id}/read")
        assert response.status_code == 404
        assert response.json() == {"detail": "Lembrete não encontrado"}
    path = f"{REMINDERS}/{own_id}/read"
    first_read = client.put(path)
    assert first_read.status_code == 200
    assert first_read.json()["read_at"]
    assert client.put(path).json() == first_read.json()
    assert client.get(REMINDERS).json()[0]["read_at"] == first_read.json()["read_at"]

    authenticated["value"] = CurrentUser(id=other, role="admin")
    assert client.put(path).status_code == 404
    assert client.get(REMINDERS).json()[0]["read_at"] is None
    app.dependency_overrides.pop(get_current_user)
    assert client.get(REMINDERS).status_code == 401
    assert client.put(path).status_code == 401
