import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Feedback, Icon } from './ManagementUI';
import { demoOffering, offeringLabel, searchOfferings } from '../lib/classCatalogDemo';
import '../styles/class-catalog.css';

const updatedAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeZone: 'America/Sao_Paulo' });

function OfferingDetails({ offer }) {
  return <div className="class-offer-details">
    <h3>{offer.title}</h3>
    <p>{offeringLabel(offer)}</p>
    <p>{offer.professor || 'Professor não informado'}</p>
  </div>;
}

export default function ClassCatalog({ state, catalog, onFollow, onOpen, message }) {
  const [period, setPeriod] = useState('');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState(null);
  const periodField = useRef(null);
  const myClassesHeading = useRef(null);
  const items = catalog.data?.items || [];
  const results = search ? searchOfferings(items, search.period, search.query) : [];
  const updated = Date.parse(catalog.data?.sourceUpdatedAt);
  const ready = !catalog.error && !catalog.loading;
  const submit = event => {
    event.preventDefault();
    setSearch({ period, query: query.trim() });
  };
  const retry = () => {
    catalog.retry();
    periodField.current?.focus();
  };

  return <div className="class-catalog">
    <section aria-labelledby="class-catalog-title">
      <header className="class-section-heading">
        <h2 id="class-catalog-title">Catálogo de turmas</h2>
        <p>Escolha o período e procure uma disciplina ou um professor.</p>
      </header>
      <form className="class-search" role="search" aria-label="Catálogo de turmas" onSubmit={submit}>
        <label htmlFor="class-period">Ano/Período</label>
        <select id="class-period" ref={periodField} required value={period} onChange={event => {
          setPeriod(event.target.value);
          setSearch(null);
        }}>
          <option value="" disabled>Selecione uma opção</option>
          {state.periods.map((value, index) => <option key={value} value={value}>
            {value} — {index === 0 ? 'Semestre atual' : 'Próximo semestre'}
          </option>)}
        </select>
        <label htmlFor="class-query">Matéria ou professor</label>
        <div className="class-search-input">
          <input id="class-query" type="search" value={query} maxLength={150} onChange={event => setQuery(event.target.value)}
            placeholder="Nome, código ou professor…" />
          <button type="submit" className="manage-icon-button" aria-label="Buscar turmas"><Icon>search</Icon></button>
        </div>
      </form>
      {!!state.followedCourses.length && <button type="button" className="management-text-button class-followed-shortcut"
        onClick={() => myClassesHeading.current?.focus()}>Ir para Minhas turmas<Icon>arrow_downward</Icon></button>}
      <div className="class-results">
        {catalog.error && <><Feedback error="Não foi possível carregar o catálogo de turmas." onRetry={retry} />
          <Link className="management-text-button" to="/eventos?aba=meus">Cadastrar um compromisso manualmente</Link></>}
        {ready && catalog.data?.stale && <div className="class-stale">
          <Icon>history</Icon><div><strong>Catálogo desatualizado</strong>
            <p>{Number.isFinite(updated) ? `Ofertas da última atualização, em ${updatedAt.format(updated)}.` : 'Exibindo as últimas ofertas disponíveis.'}</p>
            <button type="button" className="management-text-button" onClick={retry}>Atualizar catálogo</button>
          </div>
        </div>}
        <p className="class-search-status" role="status">{ready && catalog.data?.stale && <span className="sr-only">Catálogo desatualizado. </span>}{catalog.loading ? 'Carregando catálogo…' : catalog.error ? '' :
          !search ? (period ? 'Faça uma busca ou deixe o campo em branco para listar o período.' : 'Selecione um período para começar.') :
            results.length === 0 ? `Nenhuma turma encontrada em ${search.period}. Tente outro nome, código ou período.` :
              `${results.length} ${results.length === 1 ? 'turma encontrada' : 'turmas encontradas'} em ${search.period}${search.query ? ` para “${search.query}”` : ''}.`}</p>
        {ready && results.length > 0 && <ul className="class-offers">
          {results.map(offer => {
            const following = state.followedCourses.includes(offer.id);
            const action = following ? 'Deixar de seguir' : 'Seguir turma';
            return <li key={offer.id} className="class-offer">
              <OfferingDetails offer={offer} />
              <button type="button" className="manage-button" onClick={() => onFollow(offer, !following)}
                aria-label={`${action}: ${offer.title}, ${offeringLabel(offer)}`}>
                <Icon>{following ? 'remove' : 'add'}</Icon>{action}
              </button>
            </li>;
          })}
        </ul>}
      </div>
    </section>
    <section className="class-followed" aria-labelledby="class-followed-title">
      <header className="class-section-heading">
        <h2 id="class-followed-title" tabIndex={-1} ref={myClassesHeading}>Minhas turmas</h2>
        <p>Seguir uma turma é uma declaração sua e não comprova matrícula.</p>
      </header>
      <p className="class-feedback" role="status">{message}</p>
      {!state.followedCourses.length ? <div className="class-empty">
        <Icon>bookmark_border</Icon><div><h3>Você ainda não segue turmas</h3><p>Encontre uma oferta no catálogo e selecione “Seguir turma” para acessar seus planos aqui.</p></div>
      </div> : <>
        <ul className="class-offers">{state.followedCourses.map(id => {
          const offer = items.find(item => item.id === id) || demoOffering(id);
          const plan = state.plans[id];
          const available = ready && items.some(item => item.id === id);
          const action = plan?.candidates ? 'Ver plano' : 'Enviar plano';
          return <li key={id} className="class-offer class-followed-offer">
            <OfferingDetails offer={offer} />
            <p className="class-plan-status"><Icon>{plan?.candidates ? 'description' : 'info'}</Icon>
              {plan?.candidates ? 'Plano de exemplo disponível' : plan ? 'Preparando plano de exemplo…' :
                available ? 'Ainda não há plano para esta oferta' : 'Oferta indisponível para envio'}</p>
            <div className="class-offer-actions">
              {(plan?.candidates || (available && !plan)) &&
                <button type="button" className="manage-button primary" onClick={() => onOpen(id)}
                  aria-label={`${action}: ${offer.title}, ${offeringLabel(offer)}`}>{action}<Icon>arrow_forward</Icon></button>}
              <button type="button" className="manage-button" onClick={() => {
                onFollow(offer, false);
                myClassesHeading.current?.focus();
              }} aria-label={`Deixar de seguir: ${offer.title}, ${offeringLabel(offer)}`}>Deixar de seguir</button>
            </div>
          </li>;
        })}</ul>
        <p className="class-followed-note">Deixar de seguir não remove os compromissos já incluídos na agenda.</p>
      </>}
    </section>
  </div>;
}
