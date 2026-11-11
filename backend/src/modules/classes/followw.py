"""Adaptador público: destino fixo, sem sessão de usuário e sem redirecionamento."""
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
import httpx

PATHS = frozenset({"/public/classrooms/units", "/public/classrooms", "/public/subjects"})


class CatalogError(Exception):
    pass


class FollowwClient:
    def __init__(self, *, transport=None, sleep=time.sleep, clock=time.monotonic):
        self.transport, self.sleep, self.clock = transport, sleep, clock
        self.last_request = None

    def get(self, path, **params):
        if path not in PATHS:
            raise CatalogError("endpoint_proibido")
        if path != "/public/classrooms/units":
            if not (params.get("unit") or params.get("code")) or not re.fullmatch(r"20\d{2}\.[12]", str(params.get("semester", ""))):
                raise CatalogError("filtros_invalidos")
        if set(params) - {"unit", "code", "semester"}:
            raise CatalogError("filtros_invalidos")
        for attempt in range(2):
            if self.last_request is not None:
                self.sleep(max(0, 1 - (self.clock()-self.last_request)))
            self.last_request = self.clock()
            try:
                # Um cliente por chamada impede reaproveitar Set-Cookie da origem.
                with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, transport=self.transport) as client:
                    response = client.get("https://api.followw.app" + path, params=params)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == 0:
                    continue
                raise CatalogError("origem_indisponivel") from None
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                retry = response.headers.get("Retry-After", "1")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = (parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError):
                        raise CatalogError("retry_after_invalido") from None
                if not 0 <= delay <= 60:
                    raise CatalogError("limite_da_origem")
                self.sleep(delay)
                continue
            if response.status_code != 200:
                raise CatalogError("resposta_http_invalida")
            try:
                data = response.json()
            except ValueError:
                raise CatalogError("resposta_invalida") from None
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise CatalogError("resposta_invalida")
            return data


def normalize(live, subjects, unit, period):
    """Presença vem da busca ao vivo; só correspondências exatas enriquecem o ID."""
    result, rejected = [], []
    for row in live:
        subject = row.get("subject") or {}
        code, number = subject.get("code"), row.get("number")
        if not isinstance(code, str) or not code.strip() or not isinstance(number, str) or not number.strip() or row.get("semester") != period or not subject.get("name"):
            rejected.append({"code": "identidade_incompleta", "unit": unit["id"], "period": period})
            continue
        code, number = code.strip().upper(), number.strip()
        matches = [c for s in subjects if s.get("code") == code and (s.get("unit") or {}).get("id") == unit["id"]
                   for c in s.get("classrooms", []) if c.get("number") == number and c.get("semester") == period]
        ids = {str(c["sigaa_id"]) for c in matches if c.get("sigaa_id") is not None}
        if len(ids) > 1:
            rejected.append({"code": "identidade_conflitante", "subject_code": code, "unit": unit["id"], "period": period, "number": number})
            continue
        result.append({"origem": "followw", "codigo": code, "nome": subject["name"],
            "disciplina_origem_id": str(subject["sigaa_id"]) if subject.get("sigaa_id") is not None else None,
            "oferta_origem_id": next(iter(ids)) if len(matches) == 1 and ids else None,
            "unidade": str(unit["id"]), "nivel": None, "turma": number,
            "ano": int(period[:4]), "semestre": int(period[-1]),
            "professor": ", ".join(row.get("professors") or []) or None, "horarios": row.get("schedule")})
    unique, conflicts = {}, set()
    for offer in result:
        key = (offer["codigo"], offer["unidade"], offer["turma"], offer["ano"], offer["semestre"])
        if key in unique and unique[key] != offer:
            conflicts.add(key)
        unique[key] = offer
    for key in conflicts:
        rejected.append({"code": "identidade_conflitante", "subject_code": key[0], "unit": unit["id"], "period": period})
    return [offer for key, offer in unique.items() if key not in conflicts], rejected
