import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { catalogApi } from '../lib/classCatalogApi';
import {
  authorRoleLabel,
  buildRevisionCandidatesPayload,
  buildSharedDrafts,
  formatVersionTimestamp,
  normalizeSharedCandidate,
  sortSharedVersions,
  validateSharedRevisionItem,
} from '../lib/sharedPlans';
import { fieldErrors, needsAttention } from '../lib/semesterReview';
import { syllabusError } from '../lib/syllabus';
import { syllabusApi } from '../lib/syllabusApi';
import { buildReviewConfirmation, updateCandidateReviewItem } from '../lib/syllabusReview';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { Feedback, Icon } from './ManagementUI';

const formatDate = value => (value ? value.split('-').reverse().join('/') : 'Sem data');
const formatTimeLabel = item => (
  item.time
    ? `${item.time.slice(0, 5)}${item.timeSource === 'catalog' ? ' · horário da turma' : ''}`
    : item.type === 'trabalho'
      ? 'Dia inteiro'
      : 'Sem horário'
);

function SharedCandidateRow({ item, disabled, canWithdraw, onPatch, onSelect, onWithdrawCandidate }) {
  const uid = useId();
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const errors = fieldErrors(item);
  const title = item.title || 'Avaliação sem título';
  const typeLabel = item.type === 'prova' ? 'Prova' : item.type === 'trabalho' ? 'Trabalho' : 'Tipo a definir';
  const readOnly = disabled || item.imported;

  return <li className="semester-candidate">
    <div className="semester-candidate-summary">
      <input
        type="checkbox"
        checked={item.selected}
        disabled={readOnly || item.attention}
        aria-label={`Selecionar ${title}`}
        onChange={event => onSelect(event.target.checked)}
      />
      <div className="semester-candidate-title">
        <strong>{title}</strong>
        <small>{typeLabel}</small>
      </div>
      <div className="semester-candidate-date">
        <strong>{formatDate(item.date)}</strong>
        <small>{formatTimeLabel(item)}</small>
      </div>
      <span className={`semester-status${item.attention ? ' attention' : item.modifiedSinceImport ? ' updated' : ''}`}>
        {item.imported
          ? 'Na agenda'
          : item.modifiedSinceImport
            ? 'Atualizado'
            : item.attention
              ? 'Revisar'
              : 'Disponível'}
      </span>
      <button
        className="manage-icon-button"
        type="button"
        aria-expanded={item.open || false}
        aria-controls={uid}
        aria-label={`${item.open ? 'Fechar' : 'Ver detalhes de'} ${title}`}
        onClick={() => onPatch({ open: !item.open })}
      >
        <Icon>{item.open ? 'expand_less' : 'expand_more'}</Icon>
      </button>
    </div>
    <div id={uid} hidden={!item.open} className="semester-candidate-detail">
      <p><strong>Trecho do plano</strong>{item.candidate.sourcePage ? ` · Página ${item.candidate.sourcePage}` : ''}</p>
      {item.candidate.sourceExcerpt ? <blockquote>{item.candidate.sourceExcerpt}</blockquote> : <p>Trecho indisponível.</p>}
      {!!item.candidate.ambiguousFields.length && (
        <p>Confira no documento: {item.candidate.ambiguousFields.map(field => ({
          date: 'data', time: 'horário', title: 'título', type: 'tipo', timezone: 'fuso',
        })[field] || field).join(', ')}.</p>
      )}
      {!item.imported && (
        <fieldset disabled={readOnly} className="semester-edit-fields">
          <legend className="sr-only">Ajustar {title} antes de importar</legend>
          {[
            ['title', 'Título', 'text'],
            ['type', 'Tipo', 'select'],
            ['date', 'Data', 'date'],
            ['time', 'Horário (Brasília)', 'time'],
          ].map(([field, name, type]) => {
            const props = {
              value: item[field],
              'aria-label': name,
              'aria-invalid': errors[field] ? true : undefined,
              'aria-describedby': errors[field] ? `${uid}-${field}-error` : undefined,
              onChange: event => onPatch({ edits: { [field]: event.target.value }, checked: false }),
            };
            return <label className="semester-field" key={field}>
              {name}
              {type === 'select' ? (
                <select {...props}>
                  <option value="">Selecione</option>
                  {!['', 'prova', 'trabalho'].includes(item.type) && <option value={item.type}>{item.type}</option>}
                  <option value="prova">Prova</option>
                  <option value="trabalho">Trabalho</option>
                </select>
              ) : (
                <input {...props} type={type} step={type === 'time' ? 'any' : undefined} />
              )}
              {errors[field] && <small className="semester-error" id={`${uid}-${field}-error`}>{errors[field]}</small>}
            </label>;
          })}
        </fieldset>
      )}
      <div className="shared-candidate-actions">
        {item.ambiguous && !item.checked && !item.imported && (
          <button
            className="manage-button"
            type="button"
            disabled={readOnly || !!Object.keys(errors).length}
            onClick={() => onPatch({ checked: true, selected: true })}
          >
            Usar estes dados
          </button>
        )}
        {canWithdraw && (
          !confirmWithdraw ? (
            <button
              className="management-text-button shared-danger-action"
              type="button"
              disabled={disabled}
              onClick={() => setConfirmWithdraw(true)}
            >
              Retirar evento
            </button>
          ) : (
            <span className="shared-inline-confirm">
              <span>Retirar evento desta versão?</span>
              <button
                className="manage-button"
                type="button"
                disabled={disabled}
                onClick={() => {
                  setConfirmWithdraw(false);
                  onWithdrawCandidate(item.id);
                }}
              >
                Confirmar retirada
              </button>
              <button
                className="management-text-button"
                type="button"
                disabled={disabled}
                onClick={() => setConfirmWithdraw(false)}
              >
                Cancelar
              </button>
            </span>
          )
        )}
      </div>
    </div>
  </li>;
}

function RevisionEditor({ version, classSchedule, busy, onCancel, onPublish }) {
  const [items, setItems] = useState(() => buildSharedDrafts(version, classSchedule, {}).map(item => ({
    ...item,
    editable: true,
  })));
  const [error, setError] = useState('');

  const updateItem = (id, patch) => {
    setError('');
    setItems(current => current.map(item => {
      if (item.id !== id) return item;
      return updateCandidateReviewItem(item, patch, classSchedule);
    }));
  };

  const removeItem = id => {
    setError('');
    setItems(current => (current.length > 1 ? current.filter(item => item.id !== id) : current));
  };

  const submit = event => {
    event.preventDefault();
    try {
      const candidates = buildRevisionCandidatesPayload(items);
      onPublish(candidates);
    } catch (err) {
      setError(err.message || 'Revise os campos antes de publicar.');
    }
  };

  return <form className="shared-revision-editor" onSubmit={submit}>
    <div className="semester-section-heading">
      <div>
        <h3>Revisar datas da Versão {version.number}</h3>
        <p>Publicar cria uma nova versão compartilhada com seu nome e data. Eventos já importados na agenda de colegas são preservados.</p>
      </div>
    </div>
    <Feedback error={error} />
    <ul className="shared-revision-list">
      {items.map((item, index) => {
        const errors = validateSharedRevisionItem(item);
        return <li key={item.id} className="shared-revision-item">
          <div className="shared-revision-item-head">
            <strong>Avaliação {index + 1}</strong>
            {items.length > 1 && (
              <button
                type="button"
                className="management-text-button"
                disabled={busy}
                onClick={() => removeItem(item.id)}
              >
                Remover da revisão
              </button>
            )}
          </div>
          <div className="semester-edit-fields">
            <label className="semester-field">
              Título
              <input
                type="text"
                value={item.title}
                disabled={busy}
                aria-invalid={errors.title ? true : undefined}
                onChange={event => updateItem(item.id, { title: event.target.value })}
              />
              {errors.title && <small className="semester-error">{errors.title}</small>}
            </label>
            <label className="semester-field">
              Tipo
              <select
                value={item.type}
                disabled={busy}
                aria-invalid={errors.type ? true : undefined}
                onChange={event => updateItem(item.id, { type: event.target.value })}
              >
                <option value="">Selecione</option>
                <option value="prova">Prova</option>
                <option value="trabalho">Trabalho</option>
              </select>
              {errors.type && <small className="semester-error">{errors.type}</small>}
            </label>
            <label className="semester-field">
              Data
              <input
                type="date"
                value={item.date}
                disabled={busy}
                aria-invalid={errors.date ? true : undefined}
                onChange={event => updateItem(item.id, { date: event.target.value })}
              />
              {errors.date && <small className="semester-error">{errors.date}</small>}
            </label>
            <label className="semester-field">
              Horário (Brasília)
              <input
                type="time"
                value={item.time}
                disabled={busy}
                aria-invalid={errors.time ? true : undefined}
                onChange={event => updateItem(item.id, { time: event.target.value })}
              />
              {errors.time && <small className="semester-error">{errors.time}</small>}
            </label>
          </div>
        </li>;
      })}
    </ul>
    <div className="shared-revision-actions">
      <button className="manage-button primary" type="submit" disabled={busy}>
        <Icon>publish</Icon>{busy ? 'Publicando revisão…' : 'Publicar versão revisada'}
      </button>
      <button className="manage-button" type="button" disabled={busy} onClick={onCancel}>
        Cancelar revisão
      </button>
    </div>
  </form>;
}

export default function SharedClassPlans({ offeringId, offer, offers = [], onSelectOffer, onImported }) {
  const [offset, setOffset] = useState(0);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [opened, setOpened] = useState({});
  const [editingRevision, setEditingRevision] = useState(false);
  const [confirmWithdrawVersion, setConfirmWithdrawVersion] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const importKeyRef = useRef(null);

  const load = useCallback(signal => catalogApi.shared(offeringId, offset, signal), [offeringId, offset]);
  const plans = useSyllabusResource(`${offeringId}:${offset}`, load);

  const versions = sortSharedVersions(plans.data?.items || []);
  const activePlan = versions.find(v => v.id === selectedVersionId) || versions[0] || null;
  const updatedPlan = versions.find(v => v.has_imported_update) || null;
  const classSchedule = offer?.schedule || null;

  useEffect(() => {
    setSelectedVersionId(null);
    setDrafts({});
    setOpened({});
    setEditingRevision(false);
    setConfirmWithdrawVersion(false);
    setActionError('');
    setActionSuccess('');
    importKeyRef.current = null;
  }, [offeringId]);

  const rows = activePlan ? buildSharedDrafts(activePlan, classSchedule, drafts).map(item => ({
    ...item,
    open: opened[item.key] || false,
  })) : [];
  const selectedRows = rows.filter(item => item.selected && !item.imported);

  const patchRow = (item, change) => {
    const { open, edits, ...flags } = change;
    if (open !== undefined) setOpened(current => ({ ...current, [item.key]: open }));
    if (edits || Object.keys(flags).length) {
      importKeyRef.current = null;
      const edited = updateCandidateReviewItem({ ...item, editable: true }, edits || {}, classSchedule);
      const next = { ...edited, ...flags, edits: { ...item.edits, ...edits } };
      setDrafts(current => ({
        ...current,
        [item.key]: { ...next, selected: needsAttention(next) ? false : next.selected },
      }));
    }
  };

  const handleVote = async value => {
    if (!activePlan || busy) return;
    setBusy(true);
    setActionError('');
    setActionSuccess('');
    try {
      await syllabusApi.voteVersion(activePlan.syllabus_id, activePlan.id, value);
      setActionSuccess(value === 'confirm' ? 'Voto positivo registrado.' : 'Divergência sinalizada.');
      plans.retry();
    } catch (error) {
      setActionError(syllabusError(error));
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async () => {
    if (!activePlan || !selectedRows.length || busy) return;
    setBusy(true);
    setActionError('');
    setActionSuccess('');
    try {
      const normalized = activePlan.candidates.map(c => normalizeSharedCandidate(c, activePlan.id));
      const payload = buildReviewConfirmation(
        selectedRows.map(item => ({ ...item, decision: 'selected' })),
        normalized,
      );
      const key = importKeyRef.current || crypto.randomUUID();
      importKeyRef.current = key;
      const events = await syllabusApi.confirm(activePlan.syllabus_id, payload, {
        idempotencyKey: key,
        versionId: activePlan.id,
      });
      importKeyRef.current = null;
      setDrafts({});
      setActionSuccess(`${events.length} ${events.length === 1 ? 'avaliação importada' : 'avaliações importadas'} para sua agenda.`);
      plans.retry();
      onImported?.();
    } catch (error) {
      setActionError(syllabusError(error));
    } finally {
      setBusy(false);
    }
  };

  const handlePublishRevision = async candidates => {
    if (!activePlan || busy) return;
    setBusy(true);
    setActionError('');
    setActionSuccess('');
    try {
      const created = await syllabusApi.createRevision(activePlan.syllabus_id, {
        sourceVersionId: activePlan.id,
        candidates,
      });
      setEditingRevision(false);
      setDrafts({});
      setSelectedVersionId(created.id);
      setActionSuccess(`Versão ${created.number} publicada com sucesso.`);
      plans.retry();
    } catch (error) {
      setActionError(syllabusError(error));
    } finally {
      setBusy(false);
    }
  };

  const handleWithdrawVersion = async () => {
    if (!activePlan || busy) return;
    setBusy(true);
    setActionError('');
    setActionSuccess('');
    try {
      await syllabusApi.withdrawVersion(activePlan.syllabus_id, activePlan.id);
      setConfirmWithdrawVersion(false);
      setSelectedVersionId(null);
      setActionSuccess(`Versão ${activePlan.number} retirada da turma. Eventos já importados permanecem nas agendas.`);
      plans.retry();
    } catch (error) {
      setActionError(syllabusError(error));
    } finally {
      setBusy(false);
    }
  };

  const handleWithdrawCandidate = async candidateId => {
    if (!activePlan || busy) return;
    setBusy(true);
    setActionError('');
    setActionSuccess('');
    try {
      await syllabusApi.withdrawCandidate(activePlan.syllabus_id, activePlan.id, candidateId);
      setActionSuccess('Evento retirado desta versão compartilhada.');
      plans.retry();
    } catch (error) {
      setActionError(syllabusError(error));
    } finally {
      setBusy(false);
    }
  };

  return <section className="semester-section shared-plans-section" aria-labelledby="shared-class-plans">
    <header className="semester-section-heading">
      <div>
        <h2 id="shared-class-plans">Planos compartilhados da turma</h2>
        {offer && <p>{offer.subject_name} · {offer.subject_code} · Turma {offer.class_number}</p>}
      </div>
      {offers.length > 1 && onSelectOffer && (
        <label className="semester-field shared-offer-picker">
          <span className="sr-only">Selecionar turma da biblioteca</span>
          <select
            aria-label="Selecionar turma da biblioteca"
            value={offeringId}
            onChange={event => onSelectOffer(event.target.value)}
          >
            {offers.map(item => (
              <option key={item.id} value={item.id}>
                {item.subject_name} · Turma {item.class_number}
              </option>
            ))}
          </select>
        </label>
      )}
    </header>

    <Feedback error={plans.error?.message} onRetry={plans.retry} />
    <Feedback error={actionError} success={actionSuccess} />

    {updatedPlan && (
      <div className="shared-update-alert" role="status">
        <Icon>notifications_active</Icon>
        <div>
          <strong>Alterações disponíveis na Versão {updatedPlan.number}</strong>
          <p>
            O plano desta matéria recebeu atualizações após sua importação da Versão {updatedPlan.imported_from_version_number}.
            Seus eventos pessoais já importados foram preservados na agenda.
          </p>
        </div>
        {activePlan?.id !== updatedPlan.id && (
          <button
            className="manage-button"
            type="button"
            onClick={() => { setSelectedVersionId(updatedPlan.id); setEditingRevision(false); }}
          >
            Ver Versão {updatedPlan.number}
          </button>
        )}
      </div>
    )}

    {plans.loading && <p role="status">Consultando planos compartilhados…</p>}
    {!plans.loading && !plans.error && versions.length === 0 && (
      <p className="semester-muted">
        Ainda não há plano compartilhado nesta oferta. Você pode enviar um plano na fila ao lado para compartilhá-lo com a turma.
      </p>
    )}

    {activePlan && (
      <article className="shared-version-card" aria-label={`Versão ${activePlan.number}`}>
        <header className="shared-version-header">
          <div className="shared-version-meta">
            <div className="shared-version-badges">
              <strong>Versão {activePlan.number}</strong>
              {(activePlan.is_default || activePlan.id === versions[0]?.id) && (
                <span className="shared-badge is-default">Versão padrão</span>
              )}
              <span className={`shared-badge is-role-${activePlan.author_role}`}>
                {authorRoleLabel(activePlan.author_role)}
              </span>
              <span className={`shared-badge ${activePlan.institutional_provenance ? 'is-verified' : 'is-community'}`}>
                {activePlan.institutional_provenance ? 'Origem institucional verificada' : 'Sem comprovação institucional'}
              </span>
            </div>
            <p className="shared-version-attribution">
              <span>Por <strong>{activePlan.author_name || 'Participante da turma'}</strong></span>
              <span> · {activePlan.source_version_number ? `Revisão da versão ${activePlan.source_version_number}` : 'Plano extraído originalmente'}</span>
              <span> · Atualizado em {formatVersionTimestamp(activePlan.updated_at || activePlan.shared_at || activePlan.created_at)}</span>
            </p>
            {activePlan.institutional_source_url && (
              <p className="shared-version-source">
                Fonte: <a href={activePlan.institutional_source_url} target="_blank" rel="noreferrer">{activePlan.institutional_source_url}</a>
              </p>
            )}
          </div>

          <div className="shared-version-votes" role="group" aria-label={`Votação na Versão ${activePlan.number}`}>
            <button
              type="button"
              className={`manage-button${['confirma', 'confirm'].includes(activePlan.my_vote) ? ' primary' : ''}`}
              aria-pressed={['confirma', 'confirm'].includes(activePlan.my_vote)}
              disabled={busy}
              onClick={() => handleVote('confirm')}
            >
              <Icon>thumb_up</Icon>Confirmar ({activePlan.confirm_count ?? 0})
            </button>
            <button
              type="button"
              className={`manage-button${['contesta', 'contest'].includes(activePlan.my_vote) ? ' is-contested' : ''}`}
              aria-pressed={['contesta', 'contest'].includes(activePlan.my_vote)}
              disabled={busy}
              onClick={() => handleVote('contest')}
            >
              <Icon>thumb_down</Icon>Contestar ({activePlan.contest_count ?? 0})
            </button>
          </div>
        </header>

        <div className="shared-version-toolbar">
          {!editingRevision && activePlan.can_edit !== false && (
            <button className="manage-button" type="button" disabled={busy || !activePlan.candidates.length} onClick={() => setEditingRevision(true)}>
              <Icon>edit</Icon>Revisar datas desta versão
            </button>
          )}
          {activePlan.can_withdraw && !editingRevision && (
            !confirmWithdrawVersion ? (
              <button className="management-text-button shared-danger-action" type="button" disabled={busy} onClick={() => setConfirmWithdrawVersion(true)}>
                Retirar versão
              </button>
            ) : (
              <span className="shared-inline-confirm">
                <span>Retirar esta versão da turma?</span>
                <button className="manage-button" type="button" disabled={busy} onClick={handleWithdrawVersion}>Confirmar retirada</button>
                <button className="management-text-button" type="button" disabled={busy} onClick={() => setConfirmWithdrawVersion(false)}>Cancelar</button>
              </span>
            )
          )}
        </div>

        {editingRevision ? (
          <RevisionEditor
            key={activePlan.id}
            version={activePlan}
            classSchedule={classSchedule}
            busy={busy}
            onCancel={() => setEditingRevision(false)}
            onPublish={handlePublishRevision}
          />
        ) : rows.length ? (
          <>
            <ul className="semester-candidates">
              {rows.map(item => (
                <SharedCandidateRow
                  key={item.key}
                  item={item}
                  disabled={busy}
                  canWithdraw={Boolean(activePlan.can_withdraw)}
                  onPatch={change => patchRow(item, change)}
                  onSelect={checked => patchRow(item, { selected: checked })}
                  onWithdrawCandidate={handleWithdrawCandidate}
                />
              ))}
            </ul>
            <div className="semester-confirm">
              <p role="status">
                <strong>{selectedRows.length} {selectedRows.length === 1 ? 'selecionada' : 'selecionadas'}</strong>
                {rows.some(r => r.imported) && ` · ${rows.filter(r => r.imported).length} já na agenda`}
              </p>
              <div className="shared-import-actions">
                <button
                  type="button"
                  className="manage-button primary"
                  disabled={!selectedRows.length || busy}
                  onClick={handleImport}
                >
                  <Icon>event_available</Icon>
                  {busy
                    ? 'Importando…'
                    : selectedRows.length === 1
                      ? 'Importar 1 avaliação para a agenda'
                      : `Importar ${selectedRows.length} avaliações para a agenda`}
                </button>
                <Link className="manage-button" to="/eventos?aba=meus">
                  <Icon>calendar_month</Icon>Meus Eventos
                </Link>
              </div>
            </div>
          </>
        ) : (
          <p className="semester-muted">Esta versão não possui avaliações disponíveis.</p>
        )}
      </article>
    )}

    {versions.length > 0 && (
      <div className="shared-version-history">
        <h3>Histórico de versões ({versions.length})</h3>
        <ul className="shared-version-history-list">
          {versions.map((version, index) => {
            const isCurrent = activePlan?.id === version.id;
            return <li key={version.id} className={isCurrent ? 'is-current' : ''}>
              <div className="shared-history-info">
                <strong>
                  Versão {version.number}
                  {(version.is_default || index === 0) ? ' · Padrão' : ''}
                </strong>
                <span>
                  {authorRoleLabel(version.author_role)} · {version.author_name || 'Participante da turma'}
                  {version.source_version_number ? ` · Revisão da versão ${version.source_version_number}` : ' · Original'}
                </span>
                <small>
                  Atualizado em {formatVersionTimestamp(version.updated_at || version.shared_at || version.created_at)}
                  {' · '}{version.confirm_count ?? 0} positiva(s) · {version.contest_count ?? 0} contestação(ões)
                </small>
              </div>
              <button
                type="button"
                className={`manage-button${isCurrent ? ' primary' : ''}`}
                aria-current={isCurrent ? 'true' : undefined}
                disabled={isCurrent}
                onClick={() => {
                  setSelectedVersionId(version.id);
                  setEditingRevision(false);
                  setConfirmWithdrawVersion(false);
                  setActionError('');
                }}
              >
                {isCurrent ? 'Versão aberta' : 'Abrir versão'}
              </button>
            </li>;
          })}
        </ul>
      </div>
    )}

    {!!plans.data?.total && plans.data.total > 20 && (
      <nav className="semester-pagination" aria-label="Páginas de planos compartilhados">
        <button className="manage-button" disabled={plans.loading || !offset} onClick={() => setOffset(offset - 20)}>Anterior</button>
        <button className="manage-button" disabled={plans.loading || offset + 20 >= plans.data.total} onClick={() => setOffset(offset + 20)}>Próxima</button>
      </nav>
    )}
  </section>;
}
