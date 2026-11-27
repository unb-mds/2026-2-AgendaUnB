import { Link } from 'react-router-dom';
import { useCallback, useEffect, useRef, useState } from 'react';
import { catalogApi } from '../lib/classCatalogApi';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import CustomSelect from './CustomSelect';
import { Feedback, Icon } from './ManagementUI';

const PAGE_SIZE = 20;

function groupOffers(offers) {
  const units = new Map();
  for (const offer of offers) {
    const unitKey = offer.unit || `${offer.unit_code || ''}:${offer.unit_name || ''}`;
    if (!units.has(unitKey)) units.set(unitKey, { key: unitKey, name: [offer.unit_code, offer.unit_name].filter(Boolean).join(' — ') || 'Unidade não informada', subjects: new Map() });
    const unit = units.get(unitKey);
    const key = `${offer.subject_code}:${offer.year}.${offer.semester}`;
    if (!unit.subjects.has(key)) unit.subjects.set(key, { key, name: offer.subject_name, code: offer.subject_code, offers: [] });
    unit.subjects.get(key).offers.push(offer);
  }
  return [...units.values()].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}

const validateResults = result => {
  if (!Array.isArray(result?.items) || !Number.isInteger(result.total)) throw new Error('Resposta do catálogo inválida.');
  return result;
};

export default function SemesterCatalog({
  userId, period, periods, followed, onFollowed, onContinue, onPeriodChange,
}) {
  const [query, setQuery] = useState('');
  const [unit, setUnit] = useState('');
  const [search, setSearch] = useState(null);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState({});
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [justFollowed, setJustFollowed] = useState([]);
  const request = useRef(null);
  const { data: filters, error: filtersError, retry: retryFilters } = useSyllabusResource(userId, catalogApi.filters);
  const choices = [...new Set([...(filters?.periods || []), ...periods])].sort().reverse();
  const selectedPeriod = period || choices[0] || '';
  const periodOptions = choices.includes(selectedPeriod) || !selectedPeriod ? choices : [selectedPeriod, ...choices];
  const activeSearch = search && `${search.year}.${search.semester}` === selectedPeriod ? search : null;
  const load = useCallback(async signal => validateResults(await catalogApi.search({ ...activeSearch, limit: PAGE_SIZE, offset }, signal)), [activeSearch, offset]);
  const catalog = useSyllabusResource(activeSearch ? JSON.stringify([userId, activeSearch, offset]) : null, load);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (filtersError?.status !== 503 && catalog.error?.status !== 503) return;
    const timer = setTimeout(() => { retryFilters(); catalog.retry(); }, 15000);
    return () => clearTimeout(timer);
  }, [filtersError, catalog.error]);
  async function follow(offers, following = true) {
    if (request.current || !offers.length) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setErrors({});
    setMessage('');
    setJustFollowed([]);
    const saved = [];
    try {
      for (const offer of offers) {
        if (controller.signal.aborted) break;
        try {
          await catalogApi.follow(offer.id, following, controller.signal);
          if (controller.signal.aborted) break;
          onFollowed(offer, following);
          setSelected(current => {
            const next = { ...current };
            delete next[offer.id];
            return next;
          });
          saved.push(offer.id);
        } catch (error) {
          if (!controller.signal.aborted) setErrors(current => ({ ...current, [offer.id]: error.message || 'Tente novamente.' }));
        }
      }
      if (!controller.signal.aborted && saved.length) {
        if (following) setJustFollowed(saved);
        setMessage(following
          ? `${saved.length} ${saved.length === 1 ? 'turma adicionada' : 'turmas adicionadas'} à sua lista.`
          : 'Turma removida da sua lista. Seus compromissos foram preservados.');
      }
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const followedIds = new Set(followed.map(offer => offer.id));
  const selectedOffers = Object.values(selected).filter(offer => !followedIds.has(offer.id));
  return <div className="semester-step-classes">
    <section className="semester-section semester-catalog" aria-labelledby="semester-catalog-title">
      <h2 id="semester-catalog-title" tabIndex={-1}>Catálogo de turmas</h2>
      <p className="semester-catalog-intro">Busque suas matérias, abra as opções e selecione as turmas que deseja acompanhar.</p>
      <form className="semester-catalog-form" role="search" aria-label="Catálogo de turmas" onSubmit={event => {
        event.preventDefault();
        if (!selectedPeriod || catalog.loading) return;
        const [year, semester] = selectedPeriod.split('.');
        setOffset(0);
        setSearch({ year, semester, ...(query.trim() ? { q: query.trim() } : {}), ...(unit ? { unit } : {}) });
        catalog.retry();
      }}>
        <div className="semester-field semester-catalog-filter">
          <span>Semestre</span>
          <CustomSelect ariaLabel="Semestre" value={selectedPeriod} onChange={onPeriodChange} placeholder="Selecione"
            allowClear={false} disabled={!periodOptions.length} options={periodOptions.map(value => ({ value, label: value }))} />
        </div>
        <div className="semester-field semester-catalog-filter semester-unit-filter">
          <span>Unidade</span>
          <CustomSelect ariaLabel="Unidade" value={unit} onChange={setUnit} placeholder="Todas" searchLabel="Pesquisar unidade"
            options={(filters?.units || []).map(item => {
              const label = item.code ? `${item.code} — ${item.name}` : item.name;
              return { value: item.id, label, title: label };
            })} />
        </div>
        <label className="semester-field">Disciplina, código, professor ou turma
          <input type="search" maxLength={150} value={query} placeholder="Ex.: FGA0108" onChange={event => setQuery(event.target.value)} />
        </label>
        <button className={`manage-button${selectedOffers.length ? '' : ' primary'}`} disabled={catalog.loading || !selectedPeriod}><Icon>search</Icon>Buscar turmas</button>
      </form>
      <Feedback error={filtersError && 'Não foi possível carregar os períodos do catálogo.'} onRetry={retryFilters} />
      <Feedback error={catalog.error?.message} onRetry={catalog.retry} />
      <p role="status">{catalog.loading ? 'Buscando turmas…' : catalog.data ? `${catalog.data.total} ${catalog.data.total === 1 ? 'turma encontrada' : 'turmas encontradas'}` : ''}</p>
      {catalog.data?.stale && <p>Catálogo desatualizado. A busca usa os últimos dados disponíveis.</p>}
      {!activeSearch && <p className="semester-muted">Busque pelo nome da matéria, código ou professor. Use a unidade para refinar os resultados.</p>}
      {catalog.data?.total === 0 && <p className="semester-muted">Tente outro nome ou código, ou busque em todas as unidades.</p>}
      <div className="semester-catalog-results" aria-busy={catalog.loading}>
        {groupOffers(catalog.data?.items || []).map(unitGroup => <section className="semester-catalog-unit" key={unitGroup.key} aria-label={unitGroup.name}>
          <h3>{unitGroup.name}</h3>
          {[...unitGroup.subjects.values()].map(subject => <details className="semester-catalog-subject" key={subject.key}>
            <summary><Icon>chevron_right</Icon><span className="semester-subject-name">{subject.name}<small>{subject.code}</small></span>
              <span className="semester-subject-count">{subject.offers.length} {subject.offers.length === 1 ? 'turma' : 'turmas'}
                {subject.offers.some(offer => selected[offer.id] || followedIds.has(offer.id)) && <small>{subject.offers.filter(offer => selected[offer.id] || followedIds.has(offer.id)).length} na sua seleção</small>}
              </span>
            </summary>
            <ul className="semester-catalog-options">{subject.offers.map(offer => <li key={offer.id}>
          <label className={`semester-offer-option${selected[offer.id] ? ' is-selected' : ''}`}>
            <input type="checkbox" aria-label={`Selecionar turma ${offer.class_number} de ${offer.subject_name}`}
              checked={followedIds.has(offer.id) || !!selected[offer.id]} disabled={busy || followedIds.has(offer.id) || !offer.available}
              onChange={event => {
                const checked = event.target.checked;
                setSelected(current => {
                  const next = { ...current };
                  if (checked) next[offer.id] = offer;
                  else delete next[offer.id];
                  return next;
                });
              }} />
            <span className="semester-offer-info"><strong>Turma {offer.class_number}</strong><span>{offer.teacher || 'Professor não informado'}</span>
              {offer.level && <small>{offer.level}</small>}
              {followedIds.has(offer.id) ? <small>Turma seguida</small> : !offer.available && <small>Oferta indisponível</small>}
            </span>
            <span className="semester-offer-schedule"><Icon>schedule</Icon>{offer.schedule || 'Horário não informado'}</span>
          </label>
        </li>)}</ul>
          </details>)}
        </section>)}
      </div>
      {catalog.data?.total > PAGE_SIZE && <div className="semester-pagination">
        <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, catalog.data.total)} de {catalog.data.total} turmas · grupos desta página</span>
        <button className="manage-button" disabled={catalog.loading || !offset} onClick={() => setOffset(offset - PAGE_SIZE)}>Anterior</button>
        <button className="manage-button" disabled={catalog.loading || offset + PAGE_SIZE >= catalog.data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Próxima</button>
      </div>}
      {selectedOffers.length > 0 && <div className="semester-catalog-selection">
        <div className="semester-section-heading"><strong role="status">{selectedOffers.length} {selectedOffers.length === 1 ? 'turma selecionada' : 'turmas selecionadas'}</strong>
          <button type="button" className="management-text-button" disabled={busy} onClick={() => setSelected({})}>Limpar seleção</button></div>
        <ul className="semester-selected-offers">{selectedOffers.map(offer => <li key={offer.id}>
          <span>{offer.subject_name} · Turma {offer.class_number}<small>{offer.subject_code} · {offer.year}.{offer.semester}</small></span>
          <button type="button" className="manage-button" aria-label={`Remover turma ${offer.class_number} de ${offer.subject_name} da seleção`} disabled={busy}
            onClick={() => setSelected(current => { const next = { ...current }; delete next[offer.id]; return next; })}><Icon>close</Icon></button>
        </li>)}</ul>
        <p className="semester-muted">Seguir uma turma é uma declaração sua e não comprova matrícula.</p>
        <button type="button" className="manage-button primary" disabled={busy} onClick={() => follow(selectedOffers)}>
          {busy ? 'Adicionando turmas…' : `Seguir ${selectedOffers.length} ${selectedOffers.length === 1 ? 'turma selecionada' : 'turmas selecionadas'}`}
        </button>
      </div>}
      {(message || Object.keys(errors).length > 0) && (
        <div className="semester-catalog-feedback">
          {message && (
            <div className="semester-catalog-status-row">
              <p role="status">{message}</p>
              {justFollowed.length > 0 && followed.length > 0 && onContinue && (
                <button type="button" className="manage-button primary"
                  onClick={() => onContinue(justFollowed.length === 1 ? justFollowed[0] : undefined)}>
                  Avançar para organizar datas<Icon>arrow_forward</Icon>
                </button>
              )}
            </div>
          )}
          {Object.entries(errors).map(([id, error]) => (
            <Feedback key={id} error={`${selected[id]?.subject_name || followed.find(offer => offer.id === id)?.subject_name || 'Turma'}: ${error}`} />
          ))}
        </div>
      )}
    </section>

    <section className="semester-section semester-followed-panel" aria-labelledby="semester-followed-title">
      <div className="semester-section-heading">
        <div>
          <h2 id="semester-followed-title" tabIndex={-1}>Suas turmas ({followed.length})</h2>
          <p className="semester-muted">Turmas em que você declarou vínculo para enviar planos ou importar datas compartilhadas.</p>
        </div>
        {followed.length > 0 && onContinue && (
          <button type="button" className="manage-button primary" onClick={() => onContinue()}>
            Avançar para organizar datas<Icon>arrow_forward</Icon>
          </button>
        )}
      </div>
      {followed.length === 0 ? (
        <p className="semester-followed-empty">
          Nenhuma turma selecionada ainda. Use o catálogo acima para buscar suas matérias do semestre.
        </p>
      ) : (
        <ul className="semester-followed-list">
          {followed.map(offer => <li key={offer.id}>
            <div className="semester-followed-info">
              <h3>{offer.subject_name}</h3>
              <p><span className="semester-followed-code">{offer.subject_code}</span> · Turma {offer.class_number} · {offer.year}.{offer.semester}</p>
              {(offer.unit_name || offer.level) && <p>{[
                [offer.unit_code, offer.unit_name].filter(Boolean).join(' — '), offer.level,
              ].filter(Boolean).join(' · ')}</p>}
              <p>{offer.teacher || 'Professor não informado'} · {offer.schedule || 'Horário não informado'}</p>
              {!offer.available && <p className="semester-followed-warning"><Icon>info</Icon>Oferta indisponível para novos envios</p>}
            </div>
            <div className="semester-followed-actions">
              <Link className="manage-button" to={`?oferta=${encodeURIComponent(offer.id)}&etapa=2&visao=compartilhados`}>
                <Icon>description</Icon>Ver planos da turma
              </Link>
              <button type="button" className="manage-button semester-unfollow" disabled={busy} onClick={() => follow([offer], false)}>
                <Icon>remove</Icon>Deixar de seguir
              </button>
            </div>
          </li>)}
        </ul>
      )}
    </section>
  </div>;
}
