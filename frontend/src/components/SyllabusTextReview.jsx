import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Feedback } from './ManagementUI';
import { syllabusApi } from '../lib/syllabusApi';
import { approvedTextSize, MAX_APPROVED_TEXT_BYTES } from '../lib/approvedText';
import { syllabusError } from '../lib/syllabus';

export function SyllabusTextInput({ onPrepared, offeringId }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(null);
  const size = new TextEncoder().encode(text).length;
  const overLimit = size > MAX_APPROVED_TEXT_BYTES;
  useEffect(() => () => pending.current?.abort(), []);
  async function submit(event) {
    event.preventDefault();
    if (pending.current || overLimit || !text.trim()) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true); setError('');
    try {
      const plan = await syllabusApi.prepareText(text, controller.signal, offeringId);
      if (!controller.signal.aborted) { setText(''); onPrepared(plan); }
    } catch (failure) {
      if (!controller.signal.aborted) setError(syllabusError(failure, 'envio'));
    } finally { pending.current = null; if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="plan-text-input" aria-labelledby="plan-text-input-title">
    <h2 id="plan-text-input-title">Prefere colar o cronograma?</h2>
    <p>Até 40.000 bytes de texto. A preparação é local; você revisa antes de autorizar qualquer envio ao Gemini.</p>
    <form onSubmit={submit} aria-busy={busy}>
      <label htmlFor="raw-plan-text">Texto do plano</label>
      <textarea id="raw-plan-text" required rows={7} value={text} disabled={busy} aria-describedby="raw-text-size" aria-invalid={overLimit || undefined} onChange={event => setText(event.target.value)} />
      <p id="raw-text-size" role="status">{size.toLocaleString('pt-BR')} de 40.000 bytes{overLimit ? ' — reduza o texto para continuar.' : '.'}</p>
      <Feedback error={error} />
      <button className="manage-button" disabled={busy || overLimit || !text.trim()}>{busy ? 'Preparando texto…' : 'Preparar texto para revisão'}</button>
      {error && <Link className="management-text-button" to="/eventos?aba=meus">Organizar prazos manualmente</Link>}
    </form>
  </section>;
}

export default function SyllabusTextReview({ plan, onAuthorized }) {
  const [preview, setPreview] = useState(null);
  const [pages, setPages] = useState([]);
  const [authorized, setAuthorized] = useState(false);
  const [eligible, setEligible] = useState(false);
  const [reprocess, setReprocess] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [uncertain, setUncertain] = useState(false);
  const pending = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setPreview(null); setPages([]);
    setAuthorized(false); setEligible(false); setReprocess(false);
    syllabusApi.text(plan.id, controller.signal).then(data => {
      if (!controller.signal.aborted) { setPreview(data); setPages(data.pages); }
    })
      .catch(failure => { if (!controller.signal.aborted) setError(failure.message || 'Não foi possível carregar o texto.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); pending.current?.abort(); };
  }, [plan.id, attempt]);
  function edit(index, text) {
    setPages(current => current.map((page, i) => i === index ? { ...page, texto: text } : page));
    setAuthorized(false); setEligible(false);
  }
  async function submit(event) {
    event.preventDefault();
    if (pending.current || !authorized || !eligible || busy || loading || active || uncertain || !preview?.providerAvailable
      || overLimit || !pages.some(page => page.texto.trim()) || (!awaiting && !reprocess)) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true); setError('');
    try {
      await syllabusApi.authorize(plan.id, pages, reprocess, controller.signal);
      if (!controller.signal.aborted) { setAuthorized(false); setEligible(false); setReprocess(false); onAuthorized(); }
    } catch (failure) {
      if (!controller.signal.aborted) {
        setAuthorized(false); setEligible(false); setReprocess(false);
        if (!failure.status || failure.status >= 500 || failure.status === 409) {
          setUncertain(true);
          setError('Não foi possível verificar a autorização. Consulte o estado salvo antes de tentar novamente.');
        } else setError(syllabusError(failure));
      }
    } finally { pending.current = null; if (!controller.signal.aborted) setBusy(false); }
  }
  const size = approvedTextSize(pages);
  const overLimit = size > MAX_APPROVED_TEXT_BYTES;
  const awaiting = plan.authorizationRequired;
  const active = !awaiting && ['pendente', 'processando'].includes(plan.status);
  return <details className="plan-text-review" open={awaiting || undefined}>
    <summary>{awaiting ? 'Revise o texto antes de autorizar' : 'Rever texto e solicitar nova análise'}</summary>
    {loading && <p role="status">Carregando o texto preparado…</p>}
    <Feedback error={error} />
    {uncertain && <button type="button" className="manage-button" onClick={onAuthorized}>Consultar autorização</button>}
    {error && !preview && <button className="manage-button" onClick={() => setAttempt(value => value + 1)}>Tentar carregar novamente</button>}
    {preview && <form onSubmit={submit}>
      <p>Destino: <strong>{preview.provider}</strong>. Somente o texto abaixo será enviado. {pages[0]?.pagina === null ? 'O texto colado não tem referência de página.' : 'O PDF original foi descartado após a preparação.'}</p>
      <p id="text-privacy-note">A remoção automática de identificadores é limitada. Remova nomes, matrículas, contatos e conteúdo pessoal, sensível ou confidencial.</p>
      <fieldset disabled={busy || active || uncertain}>
        {pages.map((page, index) => <div className="management-field" key={page.pagina ?? 'raw'}>
          <label htmlFor={`review-page-${index}`}>{page.pagina === null ? 'Texto sem referência de página' : `Texto da página ${page.pagina}`}</label>
          <textarea id={`review-page-${index}`} aria-describedby="text-privacy-note" rows={7} maxLength={40000} value={page.texto} onChange={event => edit(index, event.target.value)} />
        </div>)}
        <p role="status">{size.toLocaleString('pt-BR')} de 40.000 bytes{overLimit ? ' — reduza o texto para continuar.' : '.'}</p>
        <label className="plan-consent"><input type="checkbox" checked={eligible} onChange={event => setEligible(event.target.checked)} />Revisei e removi conteúdo pessoal, sensível e confidencial.</label>
        <label className="plan-consent"><input type="checkbox" checked={authorized} onChange={event => setAuthorized(event.target.checked)} />Autorizo o envio somente do texto acima ao Google Gemini.</label>
        {!awaiting && <label className="plan-consent"><input type="checkbox" checked={reprocess} onChange={event => setReprocess(event.target.checked)} />Quero executar uma nova análise deste texto.</label>}
      </fieldset>
      {active && <p role="status">O texto autorizado está aguardando ou em análise. Aguarde o resultado antes de solicitar outra execução.</p>}
      {!preview.providerAvailable && <p role="status">A análise com IA ainda não está disponível. Você pode organizar seus prazos manualmente.</p>}
      <button className="manage-button primary" disabled={busy || active || uncertain || !preview.providerAvailable || !eligible || !authorized || overLimit || !pages.some(page => page.texto.trim()) || (!awaiting && !reprocess)}>{busy ? 'Registrando autorização…' : 'Autorizar envio ao Gemini'}</button>
    </form>}
    <Link className="management-text-button" to="/eventos?aba=meus">Organizar prazos manualmente</Link>
  </details>;
}
