"""Publicações completas em PostgreSQL local, incluindo rollback no meio da varredura."""
import json
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from src.modules.classes.sync import synchronize
from src.modules.classes.followw import CatalogError


class Source:
    def __init__(self, code):
        self.code, self.fail, self.empty, self.source_id = code, False, False, None
    def get(self, path, **params):
        if path.endswith('/units'):
            return [{'id': 673, 'code': 'FCTE', 'name': 'Gama'}, {'id': 674, 'code': 'CIC', 'name': 'Computação'}]
        if self.fail and params['unit'] == 674:
            raise CatalogError('origem_indisponivel')
        if path == '/public/subjects':
            return [{'code': self.code, 'unit': {'id': 673}, 'classrooms': [{'number': '01', 'semester': '2026.2', 'sigaa_id': self.source_id}]}]
        if self.empty or params['unit'] == 674:
            return []
        return [{'subject': {'code': self.code, 'name': 'Teste catálogo'}, 'number': '01', 'semester': '2026.2', 'professors': ['Docente sintético']}]


def test_atomic_publication_identity_adoption_removal_and_failure():
    url = os.getenv('TEST_SUPABASE_DB_URL')
    if not url:
        pytest.skip('TEST_SUPABASE_DB_URL not configured')
    parsed = make_url(url)
    assert parsed.host in ('localhost', '127.0.0.1')
    # Teste faz commits: exige banco descartável dedicado, nunca o Supabase da aplicação.
    if not parsed.database.startswith('agenda_catalog_'):
        pytest.skip('Requires dedicated agenda_catalog_* database')
    engine = create_engine(url)
    code = 'TEST' + uuid4().hex[:12].upper()
    source = Source(code)
    runs = []
    with engine.connect() as conn:
        before = set(conn.scalars(text('select id from public.sincronizacoes_catalogo')))
        conn.commit()
        try:
            first = synchronize(conn, ['2026.2'], source)
            oid = conn.scalar(text('select o.id from public.ofertas_turma o join public.disciplinas d on d.id=o.disciplina_id where d.codigo=:c'), {'c': code})
            conn.commit()
            source.source_id = int(uuid4().hex[:10], 16)
            second = synchronize(conn, ['2026.2'], source)
            row = conn.execute(text('select id,origem_id,publicacao_id from public.ofertas_turma where id=:id'), {'id': oid}).one()
            assert str(row.publicacao_id) == second['id'] and row.origem_id == str(source.source_id)
            conn.commit()
            source.fail = True
            with pytest.raises(CatalogError): synchronize(conn, ['2026.2'], source)
            assert str(conn.scalar(text('select publicacao_id from public.ofertas_turma where id=:id'), {'id': oid})) == second['id']
            state = conn.scalar(text('select public.estado_catalogo()'))
            assert state['tem_cache'] and state['desatualizado']
            conn.commit()
            source.fail, source.empty = False, True
            empty = synchronize(conn, ['2026.2'], source)
            assert empty['offers'] == 0
            assert conn.scalar(text('select count(*) from public.ofertas_turma where publicacao_id=:id'), {'id': empty['id']}) == 0
            assert conn.scalar(text('select count(*) from public.ofertas_turma where id=:id'), {'id': oid}) == 1
            assert conn.scalar(text('select public.estado_catalogo()'))['tem_cache']
        finally:
            conn.rollback()
            conn.execute(text('delete from public.ofertas_turma where disciplina_id in (select id from public.disciplinas where codigo=:c)'), {'c': code})
            conn.execute(text('delete from public.disciplinas where codigo=:c'), {'c': code})
            for rid in set(conn.scalars(text('select id from public.sincronizacoes_catalogo'))) - before:
                conn.execute(text('delete from public.sincronizacoes_catalogo where id=:id'), {'id': rid})
            conn.commit()
    engine.dispose()
