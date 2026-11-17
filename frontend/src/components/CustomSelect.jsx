import { useEffect, useId, useRef, useState } from 'react';

const normalizeSearch = text => text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR');

export default function CustomSelect({
  value, onChange, options, placeholder, dropUp = false, className = 'custom-input',
  wrapperWidth = '100%', ariaLabel, allowClear = true, disabled = false, searchLabel,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef(null);
  const triggerRef = useRef(null);
  const searchRef = useRef(null);
  const popupId = useId();
  const selected = options.find(option => option.value === value);
  const term = normalizeSearch(query.trim());
  const matches = term ? options.filter(option => normalizeSearch(option.label).includes(term)) : options;
  const choices = allowClear && !term ? [{ value: '', label: placeholder }, ...matches] : matches;

  useEffect(() => {
    if (!isOpen) return;
    searchRef.current?.focus({ preventScroll: true });
    const closeOutside = event => {
      if (!containerRef.current?.contains(event.target)) setIsOpen(false);
    };
    document.addEventListener('pointerdown', closeOutside);
    return () => document.removeEventListener('pointerdown', closeOutside);
  }, [isOpen]);

  const close = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };
  const select = option => {
    close();
    onChange(option.value);
  };

  return (
    <div ref={containerRef} className="custom-select" data-open={isOpen}
      style={{ width: wrapperWidth }}
      onBlur={event => {
        if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setIsOpen(false);
      }}
      onKeyDown={event => {
        if (isOpen && event.key === 'Escape') {
          event.preventDefault();
          event.stopPropagation();
          close();
        }
      }}>
      <button ref={triggerRef} type="button" className={`${className} custom-select-trigger`}
        disabled={disabled} aria-expanded={isOpen} aria-controls={isOpen ? popupId : undefined}
        aria-label={ariaLabel} aria-describedby={selected ? `${popupId}-value` : undefined}
        onClick={() => { setQuery(''); setIsOpen(open => !open); }}>
        <span id={`${popupId}-value`} title={selected?.title} className={selected ? undefined : 'custom-select-placeholder'}>{selected?.label ?? placeholder}</span>
        <span aria-hidden="true" className="material-symbols-outlined custom-select-chevron">{isOpen ? 'expand_less' : 'expand_more'}</span>
      </button>
      {isOpen && !disabled && (
        <div id={popupId} className={`custom-picker-popup custom-select-popup${dropUp ? ' custom-select-up' : ''}`}>
          {searchLabel && <div className="custom-select-search">
            <input ref={searchRef} type="search" aria-label={searchLabel} placeholder={searchLabel} value={query}
              onChange={event => setQuery(event.target.value)} onKeyDown={event => {
                if (event.key !== 'Enter' || event.nativeEvent.isComposing) return;
                event.preventDefault();
                if (term && matches.length === 1) select(matches[0]);
              }} />
          </div>}
          {!choices.length && <p className="custom-select-empty" role="status">Nenhum resultado encontrado.</p>}
          {choices.map(option => (
            <button key={option.value} type="button" aria-pressed={option.value === value}
              aria-label={option.detail} title={option.title ?? option.detail}
              className={`custom-picker-option${option.value === value ? ' active' : ''}`}
              onClick={() => select(option)}>
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
