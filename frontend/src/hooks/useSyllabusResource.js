import { useEffect, useState } from 'react';

// One request at a time. Stop on errors/final states, and suspend while hidden.
// The key also prevents stale account/page data from appearing during transitions.
export function useSyllabusResource(key, load, shouldPoll, interval = 5000) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({ key: null, data: null, error: null, loading: false });
  useEffect(() => {
    if (!key) return undefined;
    let active = true;
    let timer;
    let controller;
    let stopped = false;
    let attempt = 0;
    setState(previous => ({ key, data: previous.key === key ? previous.data : null, error: null, loading: true }));
    const run = async () => {
      if (!active || stopped || document.hidden) return;
      controller = new AbortController();
      const current = controller;
      try {
        const data = await load(current.signal);
        if (!active || current.signal.aborted) return;
        setState({ key, data, error: null, loading: false });
        stopped = !shouldPoll(data);
        if (!stopped) timer = setTimeout(run, Math.min(interval * (1 + attempt++ / 4), 30000));
      } catch (error) {
        if (!active || current.signal.aborted) return;
        stopped = true;
        setState(previous => ({ ...previous, loading: false, error }));
      }
    };
    const onVisibility = () => {
      clearTimeout(timer);
      controller?.abort();
      if (!document.hidden && !stopped) run();
    };
    document.addEventListener('visibilitychange', onVisibility);
    run();
    return () => {
      active = false;
      clearTimeout(timer);
      controller?.abort();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [key, revision, load, shouldPoll, interval]);
  return {
    ...(state.key === key ? state : { data: null, error: null, loading: !!key }),
    retry: () => setRevision(value => value + 1),
  };
}
