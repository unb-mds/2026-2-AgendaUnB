import '../styles/events-loading.css';

export default function EventsLoading() {
  return (
    <div className="events-loading" role="status">
      <span className="sr-only">Carregando eventos…</span>
      <svg className="events-loading-spinner" viewBox="0 0 48 48" aria-hidden="true">
        <circle className="events-loading-arc" cx="24" cy="24" r="20" />
      </svg>
    </div>
  );
}
