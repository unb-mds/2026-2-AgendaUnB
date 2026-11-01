import { useId, useRef, useState } from 'react';
import { validateReviewItem } from '../lib/syllabusReview';
import '../styles/syllabus-review.css';

// Controlled local draft: the owner preserves edits and resets on plan/account changes.
// No persistence, network request or agenda confirmation is performed here.
export default function SyllabusReviewEditor({ value, onChange, disabled = false, emptyMessage = 'Nenhuma avaliação disponível para revisão.' }) {
  const prefix = useId();
  const root = useRef(null);
  const [checked, setChecked] = useState(false);
  const selected = value.filter(item => item.decision === 'selected');
  const invalid = selected.some(item => Object.keys(validateReviewItem(item)).length);
  function update(id, patch) {
    setChecked(false);
    onChange(value.map(item => item.id === id ? { ...item, ...patch } : item));
  }
  function check() {
    setChecked(true);
    // Validation feedback is rendered before moving focus to the first invalid field.
    requestAnimationFrame(() => root.current?.querySelector('[aria-invalid="true"]')?.focus());
  }
  return <section className="syllabus-review" ref={root} aria-labelledby={`${prefix}-heading`}>
    <h2 id={`${prefix}-heading`}>Revisar avaliações</h2>
    {!value.length ? <p className="management-muted" role="status">{emptyMessage}</p> : <>
      <p className="management-muted">Corrija os dados e escolha os itens que deseja incluir. A conferência abaixo não salva eventos na agenda.</p>
      <p className="management-muted">As edições ficam apenas nesta tela. O fuso deve ser informado para a data de cada avaliação, sem preenchimento automático.</p>
      {value.map((item, index) => {
        const base = `${prefix}-${index}`;
        const errors = checked ? validateReviewItem(item) : {};
        const fields = [
          ['title', 'Título', 'text'], ['type', 'Tipo', 'text'],
          ['date', 'Data', 'date'], ['time', 'Horário', 'time'], ['utcOffset', 'Fuso UTC', 'text'],
        ];
        return <fieldset key={item.id} disabled={disabled} className="syllabus-review-item">
          <legend>Avaliação {index + 1}</legend>
          <label className="syllabus-review-choice" htmlFor={`${base}-decision`}>Decisão</label>
          <select id={`${base}-decision`} value={item.decision} onChange={e => update(item.id, { decision: e.target.value })}>
            <option value="pending">Ainda não decidi</option>
            <option value="selected">Selecionar para inclusão</option>
            <option value="discarded">Descartar da seleção</option>
          </select>
          <div className="syllabus-review-fields">
            {fields.map(([name, label, type]) => <div className={`syllabus-review-field field-${name}`} key={name}>
              <label htmlFor={`${base}-${name}`}>{label}{item.decision === 'selected' && name !== 'type' ? ' *' : ''}</label>
              <input id={`${base}-${name}`} type={type} value={item[name]}
                disabled={item.decision === 'discarded'}
                required={item.decision === 'selected' && name !== 'type'}
                aria-invalid={errors[name] ? true : undefined}
                aria-describedby={[errors[name] && `${base}-${name}-error`, name === 'utcOffset' && `${base}-zone-hint`].filter(Boolean).join(' ') || undefined}
                placeholder={name === 'utcOffset' ? 'Ex.: -03:00' : undefined}
                onChange={e => update(item.id, { [name]: e.target.value })} />
              {name === 'utcOffset' && <small id={`${base}-zone-hint`}>Diferença para UTC na data escolhida. Ex.: -03:00.</small>}
              {errors[name] && <p className="syllabus-review-error" id={`${base}-${name}-error`}>{errors[name]}</p>}
            </div>)}
          </div>
          {item.decision === 'discarded' && <p className="management-muted">Item fora da seleção. Suas edições foram mantidas; você pode selecioná-lo novamente.</p>}
        </fieldset>;
      })}
      <div className="syllabus-review-actions">
        <button type="button" className="manage-button" onClick={check} disabled={disabled || !selected.length}>Conferir selecionados</button>
        <p role="status">{selected.length} {selected.length === 1 ? 'avaliação selecionada' : 'avaliações selecionadas'}</p>
      </div>
      {checked && <p role={invalid ? 'alert' : 'status'} className={invalid ? 'syllabus-review-error' : 'management-muted'}>
        {invalid ? 'Corrija os campos indicados para continuar.' : 'Campos conferidos. Nenhum evento foi salvo na agenda.'}
      </p>}
    </>}
  </section>;
}
