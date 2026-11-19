import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from './AuthContext';
import { syllabusApi } from '../lib/syllabusApi';
import { isProcessing, syllabusError, validatePdf } from '../lib/syllabus';
import { buildReviewConfirmation, MAX_CONFIRMATION_CANDIDATES } from '../lib/syllabusReview';
import { reviewKey } from '../lib/semesterReview';

const Context = createContext(null);
const MAX_PREPARATIONS = 2;
const POLL_INTERVAL = 5000;
const uncertain = error => !error.status || error.status >= 500;
const upsert = (items, item) => [...items.filter(other => other.id !== item.id), item];

export function SemesterPlansProvider({ children }) {
  const { user } = useAuth();
  return <SemesterPlansSession key={user?.id || 'guest'} userId={user?.id}>{children}</SemesterPlansSession>;
}

function SemesterPlansSession({ children, userId }) {
  const [uploads, setUploads] = useState([]);
  const [plans, setPlans] = useState({});
  const [recent, setRecent] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [texts, setTexts] = useState({});
  const [authorizations, setAuthorizations] = useState({});
  const [planErrors, setPlanErrors] = useState({});
  const [results, setResults] = useState({});
  const [confirming, setConfirming] = useState(false);
  const [uploadNotice, setUploadNotice] = useState({});
  const [rawText, setRawText] = useState({ text: '' });
  const [processing, setProcessing] = useState([]);
  const session = useRef(null);
  const requests = useRef(new Map());
  const operations = useRef(new Map());
  const prepared = useRef(new Map());
  const confirmLock = useRef(false);
  const plansRef = useRef(plans);
  plansRef.current = plans;
  const polling = useRef([]);
  polling.current = [...new Set([...processing, ...Object.values(plans).filter(isProcessing).map(plan => plan.id)])]
    .filter(id => (!plans[id] || isProcessing(plans[id])) && !planErrors[id]);

  useEffect(() => {
    const controller = new AbortController();
    session.current = controller;
    const activeRequests = requests.current;
    return () => {
      controller.abort();
      activeRequests.forEach(request => request.abort());
      activeRequests.clear();
    };
  }, []);

  const savePlan = useCallback(plan => setPlans(current => ({ ...current, [plan.id]: plan })), []);
  const loadPlan = useCallback(async (id, force = false) => {
    const key = `read:${id}`;
    const previous = requests.current.get(key);
    if ((previous && !force) || requests.current.has(`authorize:${id}`) || requests.current.has(`confirm:${id}`)) return;
    previous?.abort();
    const controller = new AbortController();
    requests.current.set(key, controller);
    try {
      const data = await syllabusApi.get(id, controller.signal);
      if (controller.signal.aborted) return;
      if (data.id !== id) throw new Error('O plano retornado não corresponde ao plano solicitado.');
      if (data.userId && data.userId !== userId) throw new Error('Abra os planos compartilhados pelo catálogo da turma.');
      savePlan(data);
      setPlanErrors(current => ({ ...current, [id]: '' }));
      return data;
    } catch (error) {
      if (!controller.signal.aborted) setPlanErrors(current => ({ ...current, [id]: syllabusError(error) }));
    } finally {
      if (requests.current.get(key) === controller) requests.current.delete(key);
    }
  }, [savePlan, userId]);

  const observe = useCallback(items => {
    setProcessing(current => [...new Set([...current, ...items.filter(isProcessing).map(item => item.id)])]);
    for (const item of items) {
      if (!plansRef.current[item.id] && (isProcessing(item) || item.status === 'concluido')) loadPlan(item.id);
    }
  }, [loadPlan]);

  const hasActivePlans = polling.current.length > 0;
  useEffect(() => {
    if (!hasActivePlans) return;
    const tick = () => { if (!document.hidden) polling.current.forEach(id => loadPlan(id)); };
    const timer = setInterval(tick, POLL_INTERVAL);
    document.addEventListener('visibilitychange', tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [hasActivePlans, loadPlan]);

  const needsWarning = uploads.some(item => item.status !== 'invalid') ||
    Object.keys(drafts).length > 0 ||
    Object.values(texts).some(item => item?.dirty) || rawText.text.trim() ||
    Object.values(authorizations).some(item => item.busy) || confirming;
  useEffect(() => {
    if (!needsWarning) return;
    const warn = event => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [needsWarning]);

  const addFiles = (files, offer) => {
    if (!offer?.available) return;
    const queued = Array.from(files, file => {
      const error = validatePdf(file);
      return { id: crypto.randomUUID(), name: file.name, file: error ? null : file, offer: error ? null : offer,
        status: error ? 'invalid' : 'queued', error };
    });
    setUploads(current => [...current, ...queued]);
  };
  const addText = (text, offer) => {
    setUploads(current => [...current, { id: crypto.randomUUID(), name: 'Texto colado', text, offer, status: 'queued' }]);
  };
  const remove = id => setUploads(current => current.filter(item => item.id !== id || item.status === 'sending'));
  const retryUpload = id => setUploads(current => current.map(item => item.id === id && item.status === 'failed'
    ? { ...item, error: '', status: 'queued' } : item));
  const onPrepared = useCallback(plan => {
    savePlan(plan);
    setRecent(current => upsert(current, plan));
  }, [savePlan]);

  const authorize = useCallback(async (id, pages, reprocess) => {
    const key = `authorize:${id}`;
    const automatic = pages === null;
    if (requests.current.has(key) || (!automatic && confirmLock.current)) return;
    requests.current.get(`read:${id}`)?.abort();
    const controller = new AbortController();
    requests.current.set(key, controller);
    setAuthorizations(current => ({ ...current, [id]: { busy: true, automatic } }));
    let submitting = false;
    try {
      if (automatic) {
        const preview = await syllabusApi.text(id, controller.signal);
        if (controller.signal.aborted) return;
        if (!preview.providerAvailable) {
          setAuthorizations(current => ({ ...current, [id]: {} }));
          return;
        }
        pages = preview.pages;
      }
      submitting = true;
      const response = await syllabusApi.authorize(id, pages, reprocess, controller.signal);
      if (controller.signal.aborted) return;
      if (response.id !== id || (response.userId && response.userId !== userId)) throw new Error('Resposta da autorização inválida.');
      setPlans(current => ({ ...current, [id]: { ...current[id], ...response } }));
      setTexts(current => ({ ...current, [id]: undefined }));
      setAuthorizations(current => ({ ...current, [id]: {} }));
    } catch (error) {
      if (!controller.signal.aborted) setAuthorizations(current => ({
        ...current, [id]: { error: syllabusError(error), uncertain: submitting && (uncertain(error) || error.status === 409) },
      }));
    } finally {
      requests.current.delete(key);
    }
  }, [userId]);

  useEffect(() => {
    const signal = session.current?.signal;
    if (!signal || signal.aborted) return;
    const queued = uploads.filter(item => item.status === 'queued' && !prepared.current.has(item.id));
    for (const item of queued.slice(0, Math.max(0, MAX_PREPARATIONS - prepared.current.size))) {
      prepared.current.set(item.id, item);
      setUploads(current => current.map(row => row.id === item.id ? { ...row, status: 'sending' } : row));
      const request = item.file
        ? syllabusApi.upload({ file: item.file, offeringId: item.offer.id }, signal)
        : syllabusApi.prepareText(item.text, signal, item.offer.id);
      request.then(plan => {
        if (signal.aborted) return;
        if (plan.offeringId !== item.offer.id || (plan.userId && plan.userId !== userId)) throw new Error('O envio retornou uma turma diferente. Consulte o histórico.');
        onPrepared(plan);
        if (plan.authorizationRequired && plan.preparedTextAvailable) void authorize(plan.id, null, false);
        setUploads(current => current.filter(row => row.id !== item.id));
      }).catch(error => {
        if (signal.aborted) return;
        setUploads(current => current.map(row => row.id === item.id
          ? { ...row, status: uncertain(error) ? 'uncertain' : 'failed',
            error: uncertain(error) ? 'Não foi possível confirmar o envio. Confira o histórico antes de tentar de novo.' : syllabusError(error, 'envio'),
          } : row));
      }).finally(() => prepared.current.delete(item.id));
    }
  }, [uploads, onPrepared, authorize, userId]);

  const checkAuthorization = async id => {
    const plan = await loadPlan(id, true);
    if (!plan) return;
    setAuthorizations(current => ({ ...current, [id]: {} }));
    if (!plan.authorizationRequired) setTexts(current => ({ ...current, [id]: undefined }));
  };

  const setText = (id, value) => setTexts(current => ({ ...current, [id]: value }));
  const changeDrafts = useCallback(changes => setDrafts(current => {
    const next = { ...current };
    for (const [key, value] of Object.entries(changes)) {
      if (value === undefined) delete next[key];
      else next[key] = value;
    }
    return next;
  }), []);

  const acknowledgeUpload = id => {
    setUploadNotice(current => ({ ...current, [id]: true }));
  };
  const retryUncertainUpload = id => {
    if (!uploadNotice[id]) return;
    setUploadNotice(current => ({ ...current, [id]: false }));
    setUploads(current => current.map(item => item.id === id && item.status === 'uncertain'
      ? { ...item, error: '', status: 'queued' } : item));
  };

  const writeResult = (id, result) => setResults(current => ({ ...current, [id]: result }));

  async function sendOperation(operation, signal) {
    const { id, payload, key, draftKeys } = operation;
    requests.current.get(`read:${id}`)?.abort();
    const controller = session.current;
    requests.current.set(`confirm:${id}`, controller);
    try {
      const events = await syllabusApi.confirm(id, payload, { idempotencyKey: key, signal });
      if (signal.aborted) return false;
      const savedById = new Map(payload.map(item => [item.candidateId, item]));
      const liveIds = new Set(events.map(event => event.origin.candidateId));
      setPlans(current => {
        const plan = current[id];
        if (!plan?.candidates) return current;
        return { ...current, [id]: { ...plan, candidates: plan.candidates.map(item => {
          const saved = savedById.get(item.id);
          if (!saved) return item;
          const [date, time] = saved.startsAt?.split('T') ?? [saved.start_date, ''];
          return { ...item, status: 'confirmado', title: saved.title, type: saved.type,
            confirmedDate: liveIds.has(item.id) ? date : null, confirmedTime: time?.slice(0, 5),
            removed: !liveIds.has(item.id) };
        }) } };
      });
      changeDrafts(Object.fromEntries(draftKeys.map(item => [item, undefined])));
      operations.current.delete(id);
      setResults(current => {
        const count = events.length + (current[id]?.count || 0);
        const removed = payload.length - events.length + (current[id]?.removed || 0);
        return { ...current, [id]: { count, removed, success: `${count} na agenda${removed ? ` · ${removed} removida(s) anteriormente` : ''}` } };
      });
      return true;
    } catch (error) {
      if (signal.aborted) return false;
      const verify = uncertain(error) || [409, 422].includes(error.status);
      if (verify) operations.current.set(id, { ...operation, retryable: uncertain(error) });
      writeResult(id, { error: syllabusError(error), verify });
      return false;
    } finally {
      requests.current.delete(`confirm:${id}`);
    }
  }

  async function confirm(items) {
    if (confirmLock.current) return;
    const signal = session.current?.signal;
    if (!signal || signal.aborted) return;
    const groups = new Map();
    for (const item of items) {
      if (operations.current.has(item.planId) || requests.current.has(`authorize:${item.planId}`)) continue;
      if (!groups.has(item.planId)) groups.set(item.planId, []);
      groups.get(item.planId).push(item);
    }
    confirmLock.current = true;
    setConfirming(true);
    try {
      for (const [id, group] of groups) {
        if (signal.aborted) break;
        for (let offset = 0; offset < group.length; offset += MAX_CONFIRMATION_CANDIDATES) {
          const chunk = group.slice(offset, offset + MAX_CONFIRMATION_CANDIDATES);
          const plan = plans[id];
          let payload;
          try {
            payload = buildReviewConfirmation(chunk.map(item => ({ ...item, decision: 'selected' })), plan.candidates);
          } catch (error) {
            writeResult(id, { error: syllabusError(error) });
            break;
          }
          const saved = await sendOperation({ id, payload, key: crypto.randomUUID(), draftKeys: chunk.map(item => item.key) }, signal);
          if (!saved) break;
        }
      }
    } finally {
      confirmLock.current = false;
      if (!signal.aborted) setConfirming(false);
    }
  }

  async function reconcile(id) {
    const operation = operations.current.get(id);
    if (!operation || confirmLock.current) return;
    const signal = session.current?.signal;
    if (!signal || signal.aborted) return;
    confirmLock.current = true;
    setConfirming(true);
    try {
      const plan = await loadPlan(id, true);
      if (!plan || signal.aborted) return;
      const candidates = new Map((plan.candidates || []).map(item => [item.id, item]));
      const confirmed = operation.payload.filter(item => candidates.get(item.candidateId)?.status === 'confirmado').length;
      const sameVersion = operation.payload.every((item, index) => {
        const candidate = candidates.get(item.candidateId);
        return candidate && operation.draftKeys[index] === reviewKey(id, candidate);
      });
      if (operation.retryable && sameVersion && confirmed === 0 && plan.status === 'concluido' &&
          operation.payload.every(item => candidates.get(item.candidateId)?.status === 'pendente')) {
        await sendOperation(operation, signal);
      } else {
        operations.current.delete(id);
        changeDrafts(Object.fromEntries(operation.draftKeys.flatMap((key, index) =>
          candidates.get(operation.payload[index].candidateId)?.status === 'confirmado' ? [[key, undefined]] : [])));
        writeResult(id, { success: `${confirmed} de ${operation.payload.length} confirmada(s) no último envio. Confira as pendentes.` });
      }
    } finally {
      confirmLock.current = false;
      if (!signal.aborted) setConfirming(false);
    }
  }

  return <Context.Provider value={{
    uploads, rawText, setRawText, addFiles, addText, remove, retryUpload, uploadNotice, acknowledgeUpload, retryUncertainUpload,
    plans, recent, planErrors, loadPlan, observe, drafts, changeDrafts, texts, setText, authorizations, authorize,
    checkAuthorization, results, confirming, confirm, reconcile,
  }}>{children}</Context.Provider>;
}

export const useSemesterPlans = () => useContext(Context);
