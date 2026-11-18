import { useEffect, useId, useRef, useState } from 'react';

const normalizeSearch = text => text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR');

export default function CustomSelect({
  value, onChange, options, placeholder, dropUp = false, className = 'custom-input',
  wrapperWidth = '100%', ariaLabel, allowClear = true, disabled = false, searchLabel,
  multiple = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef(null);
  const triggerRef = useRef(null);
  const searchRef = useRef(null);
  const popupId = useId();

  const selectedValues = multiple
    ? (Array.isArray(value) ? value : (value ? [value] : []))
    : [];
  const selectedList = multiple
    ? options.filter(option => selectedValues.includes(option.value))
    : [];
  const selected = multiple ? null : options.find(option => option.value === value);

  const hasSelection = multiple ? selectedList.length > 0 : Boolean(selected);
  const triggerLabel = multiple
    ? (selectedList.length === 0
      ? placeholder
      : selectedList.length === 1
        ? selectedList[0].label
        : `${selectedList[0].label} +${selectedList.length - 1}`)
    : (selected?.label ?? placeholder);
  const triggerTitle = multiple
    ? (selectedList.length > 0 ? selectedList.map(option => option.label).join(', ') : undefined)
    : selected?.title;

  const term = normalizeSearch(query.trim());
  const matches = term ? options.filter(option => normalizeSearch(option.label).includes(term)) : options;
  const choices = allowClear && !term ? [{ value: '', label: placeholder, isClear: true }, ...matches] : matches;

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
    if (multiple) {
      if (option.isClear) {
        onChange([]);
        return;
      }
      const next = selectedValues.includes(option.value)
        ? selectedValues.filter(item => item !== option.value)
        : [...selectedValues, option.value];
      onChange(next);
      return;
    }
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
      <button ref={triggerRef} type="button"
        className={`${className} custom-select-trigger${hasSelection ? ' has-selection' : ''}`}
        disabled={disabled} aria-expanded={isOpen} aria-controls={isOpen ? popupId : undefined}
        aria-label={ariaLabel} aria-describedby={hasSelection ? `${popupId}-value` : undefined}
        onClick={() => { setQuery(''); setIsOpen(open => !open); }}>
        <span id={`${popupId}-value`} title={triggerTitle} className={hasSelection ? undefined : 'custom-select-placeholder'}>{triggerLabel}</span>
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
          {choices.map(option => {
            const isSelected = multiple
              ? (option.isClear ? selectedValues.length === 0 : selectedValues.includes(option.value))
              : option.value === value;
            return (
              <button key={option.isClear ? '__clear__' : option.value} type="button"
                role={multiple && !option.isClear ? 'checkbox' : undefined}
                aria-checked={multiple && !option.isClear ? isSelected : undefined}
                aria-pressed={!multiple || option.isClear ? isSelected : undefined}
                aria-label={option.detail} title={option.title ?? option.detail}
                className={`custom-picker-option${multiple && !option.isClear ? ' custom-picker-option-multi' : ''}${option.isClear && multiple ? ' custom-picker-option-clear' : ''}${isSelected ? ' active' : ''}`}
                onClick={() => select(option)}>
                {multiple && !option.isClear && (
                  <span className={`custom-select-checkbox${isSelected ? ' checked' : ''}`} aria-hidden="true">
                    {isSelected && <span className="material-symbols-outlined">check</span>}
                  </span>
                )}
                <span className="custom-select-option-label">{option.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
