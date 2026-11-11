import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Feedback, Icon } from './ManagementUI';
import { catalogApi } from '../lib/classCatalogApi';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import '../styles/class-catalog.css';

export function OfferingDetails({ offer }) {
  return <div className="class-offer-details"><h3>{offer.subject_name}</h3>
    <p>{offer.subject_code} · Turma {offer.class_number} · {offer.year}.{offer.semester} · {offer.unit_name ? `${offer.unit_code ? `${offer.unit_code} — ` : ''}${offer.unit_name}` : 'Unidade não informada'}{offer.level ? ` · ${offer.level}` : ''}</p>
    <p>{offer.teacher || 'Professor não informado'} · {offer.schedule || 'Horário não informado'}</p></div>;
}

export default function RealClassCatalog({ userId, onOpen }) {
  const [period, setPeriod] = useState('');
  const [unit, setUnit] = useState('');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const pending = useRef(null);
  const heading = useRef(null);
  useEffect(() => () => pending.current?.abort(), []);
  const filters = useSyllabusResource(userId, catalogApi.filters);
  const followed = useSyllabusResource(userId, catalogApi.followed);
  const load = useCallback(signal => search ? catalogApi.search({ ...search, limit: 20, offset }, signal) : Promise.resolve(null), [search, offset]);
  const catalog = useSyllabusResource(JSON.stringify([userId, search, offset]), load);
  async function follow(offer, value) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setBusy(offer.id); setError(''); setMessage('');
    try {
      await catalogApi.follow(offer.id, value, controller.signal);
      if (!controller.signal.aborted) {
        followed.retry(); setMessage(value ? 'Turma seguida. Ela ficará disponível na sua conta.' : 'Você deixou de seguir a turma. Seus compromissos foram preservados.');
      }
    } catch (failure) { if (!controller.signal.aborted) setError(failure.message || 'Não foi possível atualizar o vínculo. Tente novamente.'); }
    finally { pending.current = null; if (!controller.signal.aborted) setBusy(null); }
  }
  useEffect(() => {
    if (filters.error?.status !== 503 && catalog.error?.status !== 503) return undefined;
    const timer = setTimeout(() => { filters.retry(); catalog.retry(); }, 15000);
    return () => clearTimeout(timer);
  }, [filters.error, catalog.error]);
  const groups = Object.values((catalog.data?.items || []).reduce((result, offer) => {
    const key = offer.subject_name.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();
    (result[key] ||= { name: offer.subject_name, offers: [] }).offers.push(offer);
    return result;
  }, {}));
  const items = followed.data?.items || [];
  const cache = catalog.data || filters.data;
  const retry = () => { filters.retry(); catalog.retry(); };
  return <div className="class-catalog">
    <section aria-labelledby="real-catalog-title"><header className="class-section-heading"><h2 id="real-catalog-title">Catálogo de turmas</h2><p>Escolha a oferta pelo código, unidade, turma e período.</p></header>
      <form className="class-search" role="search" aria-label="Catálogo de turmas" onSubmit={event => {
        event.preventDefault(); const [year, semester] = period.split('.');
        setOffset(0); setSearch({ year, semester, ...(unit ? { unit } : {}), ...(query.trim() ? { q: query.trim() } : {}) });
      }}>
        <label htmlFor="real-class-period">Ano/Período</label><select id="real-class-period" required value={period} onChange={e => setPeriod(e.target.value)}><option value="">Selecione um período</option>{filters.data?.periods.map(p => <option key={p}>{p}</option>)}</select>
        <label htmlFor="real-class-unit">Unidade</label><select id="real-class-unit" value={unit} onChange={e => setUnit(e.target.value)}><option value="">Todas as unidades</option>{filters.data?.units.map(u => <option key={u.id} value={u.id}>{u.code ? `${u.code} — ` : ''}{u.name}</option>)}</select>
        <label htmlFor="real-class-query">Disciplina, código, professor ou turma</label><div className="class-search-input"><input id="real-class-query" type="search" maxLength={150} value={query} onChange={e => setQuery(e.target.value)} placeholder="Nome, código, professor ou turma…" /><button className="manage-icon-button" aria-label="Buscar turmas" disabled={catalog.loading || !filters.data}><Icon>search</Icon></button></div>
      </form>
      <button className="management-text-button class-followed-shortcut" onClick={() => heading.current?.focus()}>Ir para Minhas turmas<Icon>arrow_downward</Icon></button>
      {(filters.error || catalog.error) && <><Feedback error={(filters.error || catalog.error)?.status === 503 ? "O catálogo ainda não está disponível. A primeira carga precisa concluir; tente novamente em alguns minutos." : "Não foi possível carregar o catálogo de turmas."} onRetry={retry} /><Link className="management-text-button" to="/eventos?aba=meus">Cadastrar um compromisso manualmente</Link></>}
      {cache?.stale && <div className="class-stale"><Icon>history</Icon><div><strong>Catálogo desatualizado</strong><p>Última atualização: {new Date(cache.source_updated_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}.</p><button className="management-text-button" onClick={retry}>Tentar novamente</button></div></div>}
      <p role="status" className="class-search-status">{filters.loading || catalog.loading ? 'Carregando catálogo…' : catalog.error ? '' : !search ? 'Selecione um período para começar.' : `${catalog.data?.total ?? 0} turmas encontradas.`}</p>
      {!catalog.loading && !catalog.error && search && catalog.data?.total === 0 && <p>Nenhuma turma encontrada. Tente outro nome, código, unidade ou período.</p>}
      <Feedback error={error} /><p role="status">{message}</p>
      {!catalog.loading && !catalog.error && <div className="class-subject-groups">{groups.map(group => <details key={group.name} className="class-subject-group"><summary>{group.name} — {[...new Set(group.offers.map(o => o.subject_code))].join(', ')} ({group.offers.length})</summary><ul className="class-offers">{group.offers.map(offer => {
        const following = items.some(item => item.id === offer.id);
        return <li key={offer.id} className="class-offer"><OfferingDetails offer={offer} /><button className="manage-button" disabled={!!busy || followed.loading || !!followed.error} onClick={() => follow(offer, !following)}>{busy === offer.id ? 'Salvando…' : following ? 'Deixar de seguir' : 'Seguir turma'}</button></li>;
      })}</ul></details>)}</div>}
      {!!catalog.data?.total && <nav className="plan-pagination" aria-label="Páginas de turmas"><span>Página {offset / 20 + 1} de {Math.ceil(catalog.data.total / 20)}</span><div><button className="manage-button" disabled={catalog.loading || offset === 0} onClick={() => setOffset(offset - 20)}>Anterior</button><button className="manage-button" disabled={catalog.loading || offset + 20 >= catalog.data.total} onClick={() => setOffset(offset + 20)}>Próxima</button></div></nav>}
    </section>
    <section className="class-followed" aria-labelledby="real-followed-title"><header className="class-section-heading"><h2 id="real-followed-title" ref={heading} tabIndex={-1}>Minhas turmas</h2><p>Seguir uma turma é uma declaração sua e não comprova matrícula.</p></header>
      <Feedback error={followed.error && 'Não foi possível carregar suas turmas.'} onRetry={followed.retry} />
      {followed.loading && <p role="status">Carregando suas turmas…</p>}
      {!followed.loading && !followed.error && !items.length && <p>Você ainda não segue turmas. Encontre uma oferta no catálogo para começar.</p>}
      <ul className="class-offers">{items.map(offer => <li key={offer.id} className="class-offer"><OfferingDetails offer={offer} /><div className="class-offer-actions"><button className="manage-button primary" onClick={() => onOpen(offer)}>Ver planos<Icon>arrow_forward</Icon></button><button className="manage-button" disabled={!!busy} onClick={() => follow(offer, false)}>Deixar de seguir</button></div>{!offer.available && <p>Oferta fora do catálogo atual. Seus planos continuam disponíveis; novos envios estão bloqueados.</p>}</li>)}</ul>
      <p className="class-followed-note">Deixar de seguir não remove os compromissos já incluídos na agenda.</p>
    </section>
  </div>;
}
