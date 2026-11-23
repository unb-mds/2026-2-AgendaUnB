import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSemesterPlans } from '../contexts/SemesterPlansContext';
import { fieldErrors, needsAttention } from '../lib/semesterReview';
import { isProcessing } from '../lib/syllabus';
import { updateCandidateReviewItem } from '../lib/syllabusReview';
import HalftonePet from './HalftonePet';
import { Icon, NativeSelect } from './ManagementUI';

const formatDate = value => value ? value.split('-').reverse().join('/') : 'Sem data';
const filters = [
  ['all', 'Todas'],
  ['attention', 'Precisam de atenção'],
  ['added', 'Adicionadas'],
];

function CandidateLine({ item, label, disabled, update, select }) {
  const uid = useId();
  const { attention } = item;
  const errors = fieldErrors(item);
  const readOnly = disabled || !item.editable;
  const title = item.title || 'Avaliação sem título';
  const type = item.type === 'prova' ? 'Prova' : item.type === 'trabalho' ? 'Trabalho' : 'Tipo a definir';
  return <li className="semester-candidate">
    <div className="semester-candidate-summary">
      <input type="checkbox" checked={item.selected} disabled={readOnly || attention} aria-label={`Selecionar ${title} · ${label}`} onChange={event => select(event.target.checked)} />
      <div className="semester-candidate-title"><strong>{title}</strong><small>{label} · {type}</small></div>
      <div className="semester-candidate-date">{item.status === 'confirmado' ? (
        item.candidate.confirmedDate && <><strong>{formatDate(item.candidate.confirmedDate)}</strong><small>{item.candidate.confirmedTime || 'Dia inteiro'}</small></>
      ) : <><strong>{formatDate(item.date)}</strong><small>{
        item.time ? `${item.time.slice(0, 5)}${item.timeSource === 'catalog' ? ' · horário da turma' : ''}`
          : item.type === 'trabalho' ? 'Dia inteiro' : 'Sem horário'
      }</small></>}</div>
      {attention && <span className="semester-status attention">Revisar</span>}
      {!item.editable && (item.status === 'confirmado' && !item.candidate.removed
        ? <Link className="semester-agenda-status" to="/eventos?aba=meus">Data na agenda</Link>
        : <span className="semester-status">{item.status === 'confirmado' ? 'Removida da agenda' : 'Descartada'}</span>)}
      <button className="manage-icon-button" type="button" aria-expanded={item.open || false} aria-controls={uid}
        aria-label={`${item.open ? 'Fechar' : 'Ver detalhes de'} ${title}`} onClick={() => update({ open: !item.open })}><Icon>{item.open ? 'expand_less' : 'expand_more'}</Icon></button>
    </div>
    <div id={uid} hidden={!item.open} className="semester-candidate-detail">
      <p><strong>Trecho do plano</strong>{item.candidate.sourcePage ? ` · Página ${item.candidate.sourcePage}` : ''}</p>
      {item.candidate.sourceExcerpt ? <blockquote>{item.candidate.sourceExcerpt}</blockquote> : <p>Trecho indisponível.</p>}
      {!!item.candidate.ambiguousFields.length && <p>Confira no documento: {item.candidate.ambiguousFields.map(field => ({ date: 'data', time: 'horário', title: 'título', type: 'tipo', timezone: 'fuso' })[field] || field).join(', ')}.</p>}
      {item.editable && <fieldset disabled={readOnly} className="semester-edit-fields">
        <legend className="sr-only">Editar {title}</legend>
        {[
          ['title', 'Título', 'text'], ['type', 'Tipo', 'select'], ['date', 'Data', 'date'], ['time', 'Horário (Brasília)', 'time'],
        ].map(([field, name, type]) => {
          const props = {
            value: item[field],
            'aria-label': name,
            'aria-invalid': errors[field] ? true : undefined,
            'aria-describedby': errors[field] ? `${uid}-${field}-error` : undefined,
            onChange: event => update({ edits: { [field]: event.target.value }, checked: false }),
          };
          return <label className="semester-field" key={field}>{name}
            {type === 'select' ? <NativeSelect {...props}><option value="">Selecione</option>
              {!['', 'prova', 'trabalho'].includes(item.type) && <option value={item.type}>{item.type}</option>}
              <option value="prova">Prova</option><option value="trabalho">Trabalho</option>
            </NativeSelect> : <input {...props} type={type} step={type === 'time' ? 'any' : undefined} />}
            {errors[field] && <small className="semester-error" id={`${uid}-${field}-error`}>{errors[field]}</small>}
          </label>;
        })}
      </fieldset>}
      {item.ambiguous && !item.checked && item.editable && <button className="manage-button" disabled={readOnly || !!Object.keys(errors).length}
        onClick={() => update({ checked: true, selected: true })}>Usar estes dados</button>}
    </div>
  </li>;
}

function BulkEdit({ selected, disabled, apply, undo, hasUndo }) {
  const [field, setField] = useState('type');
  const [value, setValue] = useState('prova');
  const sameClass = selected.length > 1 && selected[0].offeringId && selected.every(item => item.offeringId === selected[0].offeringId);
  if (!sameClass && !hasUndo) return null;
  return <details className="semester-bulk-edit" open={hasUndo || undefined}>
    <summary>Editar em lote</summary>
    {sameClass && <form onSubmit={event => { event.preventDefault(); if (value && !disabled) apply(field, value); }}>
      <label className="semester-field">Campo
        <NativeSelect value={field} onChange={event => { setField(event.target.value); setValue(event.target.value === 'type' ? 'prova' : ''); }}>
          <option value="type">Tipo</option><option value="time">Horário</option>
        </NativeSelect>
      </label>
      <label className="semester-field">Novo valor{field === 'type' ?
        <NativeSelect value={value} onChange={event => setValue(event.target.value)}><option value="prova">Prova</option><option value="trabalho">Trabalho</option></NativeSelect> :
        <input type="time" required value={value} onChange={event => setValue(event.target.value)} />}
      </label>
      <button className="manage-button" disabled={disabled || !value}>Aplicar a {selected.length} avaliações</button>
    </form>}
    {hasUndo && <button className="management-text-button" onClick={undo} disabled={disabled}>Desfazer edição em lote</button>}
  </details>;
}

export default function SemesterReview({ plans, allPlans = plans, rows, offers, onPlan, onOpenCatalog, onOpenShared }) {
  const workspace = useSemesterPlans();
  const [filter, setFilter] = useState('all');
  const [course, setCourse] = useState('');
  const [undo, setUndo] = useState(null);
  const [opened, setOpened] = useState({});
  const bulkRef = useRef(null);
  const planNames = new Map(plans.map(plan => [plan.id, plan.disciplina || plan.fileName]));
  const hasFollowedOffers = Object.keys(offers || {}).length > 0;
  const pendingAuthPlan = allPlans.find(plan => plan.authorizationRequired && plan.preparedTextAvailable);
  const activeProcessing = allPlans.some(isProcessing);
  const petMode = activeProcessing ? 'processing'
    : rows.length ? 'filtered'
    : pendingAuthPlan ? 'awaiting_auth' : 'idle';
  const label = item => offers[item.offeringId]?.subject_name || planNames.get(item.planId);
  const groupKey = item => item.offeringId || item.planId;
  const courses = [...new Map(rows.map(item => [groupKey(item), offers[item.offeringId]
    ? `${label(item)} · Turma ${offers[item.offeringId].class_number}` : label(item)])).entries()];
  const locked = item => workspace.confirming || workspace.results[item.planId]?.verify;
  const visible = rows.filter(item => (!course || groupKey(item) === course) &&
    (filter === 'all' || (filter === 'attention' ? item.attention : item.status === 'confirmado')))
    .sort((a, b) => (a.date || '9999').localeCompare(b.date || '9999') || a.title.localeCompare(b.title, 'pt-BR'));
  const visibleKeys = new Set(visible.map(item => item.key));
  const eligible = visible.filter(item => item.editable && !item.attention && !workspace.results[item.planId]?.verify);
  const selected = rows.filter(item => item.selected && !workspace.results[item.planId]?.verify);
  const selectedOutside = selected.filter(item => !visibleKeys.has(item.key)).length;
  const selectedHere = eligible.filter(item => item.selected).length;
  const pending = rows.filter(item => item.attention).length;
  useEffect(() => { if (bulkRef.current) bulkRef.current.indeterminate = selectedHere > 0 && selectedHere < eligible.length; });
  useEffect(() => { if (course && !courses.some(([id]) => id === course)) setCourse(''); }, [course, courses]);

  const patch = (item, change) => {
    const { open, edits, ...flags } = change;
    if (open !== undefined) setOpened(current => ({ ...current, [item.key]: open }));
    if (edits || Object.keys(flags).length) {
      setUndo(null);
      const edited = updateCandidateReviewItem(item, edits || {}, offers[item.offeringId]?.schedule);
      const next = { ...edited, ...flags, edits: { ...item.edits, ...edits } };
      workspace.changeDrafts({ [item.key]: { ...next, selected: needsAttention(next) ? false : next.selected } });
    }
  };
  const applyBulk = (field, value) => {
    setUndo(previous => ({
      ...Object.fromEntries(selected.map(item => [item.key, workspace.drafts[item.key]])),
      ...previous,
    }));
    workspace.changeDrafts(Object.fromEntries(selected.map(item => {
      const edited = updateCandidateReviewItem(item, { [field]: value }, offers[item.offeringId]?.schedule);
      return [item.key, { ...edited, edits: { ...item.edits, [field]: value }, selected: !needsAttention(edited) }];
    })));
  };

  return <section className="semester-section semester-review" aria-labelledby="semester-review-title">
    <header className="semester-section-heading"><h2 id="semester-review-title" tabIndex={-1}>Avaliações</h2>
      <Link className="manage-button" to="/eventos?aba=meus"><Icon>calendar_month</Icon>Meus Eventos</Link>
    </header>
    {rows.length > 0 && <>
      <div className="semester-filters">
        <div className="semester-filter-buttons" role="group" aria-label="Estado das avaliações">
          {filters.map(([value, name]) => <button className="manage-button" key={value} type="button"
            aria-pressed={filter === value} onClick={() => setFilter(value)}>{name}{value === 'attention' && pending > 0 ? ` (${pending})` : ''}</button>)}
        </div>
        <label className="semester-field sr-only" htmlFor="semester-review-course">Filtrar avaliações por turma</label>
        <NativeSelect id="semester-review-course" value={course} onChange={event => setCourse(event.target.value)}>
          <option value="">Todas as turmas</option>{courses.map(([key, name]) => <option value={key} key={key}>{name}</option>)}
        </NativeSelect>
      </div>
      <div className="semester-selection">
        <label><input ref={bulkRef} type="checkbox" checked={eligible.length > 0 && selectedHere === eligible.length}
          disabled={workspace.confirming || !eligible.length} onChange={event => {
            const checked = event.target.checked;
            workspace.changeDrafts(Object.fromEntries(eligible.map(item => [item.key, { ...item, selected: checked }])));
            setUndo(null);
          }} />{course ? 'Selecionar válidas da turma' : 'Selecionar válidas no filtro'}</label>
        <BulkEdit selected={selected} disabled={workspace.confirming} apply={applyBulk} hasUndo={!!undo}
          undo={() => { workspace.changeDrafts(undo); setUndo(null); }} />
      </div>
    </>}
    {rows.length > 0 && <div className="semester-confirm">
      <p role="status"><strong>{selected.length} {selected.length === 1 ? 'selecionada' : 'selecionadas'}</strong>{selectedOutside ? ` · ${selectedOutside} fora do filtro` : ''}
        {pending > 0 ? ` · ${pending} fora do lote por precisar de revisão` : ''}</p>
      <button className="manage-button primary" disabled={!selected.length || workspace.confirming}
        onClick={() => { setUndo(null); workspace.confirm(selected); }}>
        <Icon>event_available</Icon>{workspace.confirming ? 'Adicionando…' : selected.length === 1 ? 'Adicionar 1 avaliação à agenda' : `Adicionar ${selected.length} avaliações à agenda`}
      </button>
    </div>}
    {visible.length > 0 && activeProcessing && <HalftonePet mode={petMode} />}
    {visible.length ? <ul className="semester-candidates">{visible.map(item => <CandidateLine key={item.key} item={{ ...item, open: opened[item.key] }}
      label={label(item)} disabled={locked(item)} update={change => patch(item, change)}
      select={checked => patch(item, { selected: checked })} />)}</ul> : <div className="semester-empty">
      <div className="semester-empty-copy">
        <div className="semester-empty-title">
          <Icon>event_note</Icon>
          <h3>{rows.length ? 'Nenhuma avaliação neste filtro' : 'As datas aparecem aqui'}</h3>
        </div>
        {!rows.length ? (
          <>
            <p>Adicione um plano e autorize a extração para revisar provas e trabalhos.</p>
            <ul className="semester-empty-steps" aria-label="Como começar">
              <li className={hasFollowedOffers ? 'is-done' : ''}>
                <Icon>{hasFollowedOffers ? 'check_circle' : 'school'}</Icon>
                <div>
                  <strong>Siga suas turmas do semestre</strong>
                  <small>Selecione as disciplinas na Etapa 1 para liberar o envio e os planos da turma.</small>
                </div>
              </li>
              <li className={allPlans.length > 0 ? 'is-done' : ''}>
                <Icon>{allPlans.length > 0 ? 'check_circle' : 'upload_file'}</Icon>
                <div>
                  <strong>Envie o PDF digital, cole o texto ou importe da turma</strong>
                  <small>O texto é preparado localmente e só segue para análise após sua autorização.</small>
                </div>
              </li>
              <li>
                <Icon>event_available</Icon>
                <div>
                  <strong>Revise e adicione em lote à agenda</strong>
                  <small>Provas e trabalhos extraídos aparecem nesta lista prontos para confirmação rápida.</small>
                </div>
              </li>
            </ul>
            <div className="semester-empty-actions">
              {pendingAuthPlan ? (
                <button type="button" className="manage-button primary" onClick={() => onPlan(pendingAuthPlan.id)}>
                  <Icon>article</Icon>Abrir texto pendente
                </button>
              ) : !hasFollowedOffers && onOpenCatalog ? (
                <button type="button" className="manage-button primary" onClick={onOpenCatalog}>
                  <Icon>search</Icon>Selecionar turmas no catálogo
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="manage-button primary"
                    onClick={() => {
                      const addBtn = document.getElementById('semester-add-pdfs');
                      if (addBtn && !addBtn.disabled) addBtn.focus();
                      else document.querySelector('.semester-plan-offer button')?.focus();
                    }}
                  >
                    Ir para envio de plano
                  </button>
                  {onOpenShared && (
                    <button type="button" className="manage-button" onClick={onOpenShared}>
                      Ver planos compartilhados
                    </button>
                  )}
                </>
              )}
            </div>
          </>
        ) : (
          <p>Altere o filtro acima ou selecione &ldquo;Todas&rdquo; para visualizar as avaliações extraídas.</p>
        )}
      </div>
      <HalftonePet mode={petMode} />
    </div>}
    {Object.entries(workspace.results).filter(([id]) => planNames.has(id)).map(([id, result]) => <div
      className={`semester-result${result.error ? ' semester-error' : ''}`} key={id} role={result.error ? 'alert' : 'status'}>
      <strong>{planNames.get(id)}</strong><span>{result.error || result.success}</span>
      {result.verify && <button className="manage-button" disabled={workspace.confirming} onClick={() => workspace.reconcile(id)}>Verificar confirmação</button>}
      {result.verify && workspace.planErrors[id] && <p>{workspace.planErrors[id]}</p>}
      {result.error && !result.verify && <button className="management-text-button" onClick={() => onPlan(id)}>Ver plano</button>}
    </div>)}
  </section>;
}
