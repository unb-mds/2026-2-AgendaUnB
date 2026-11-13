import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { searchPages, siteUrl } from '../lib/searchPages.js';

export default function SearchMetadata({ event }) {
  const { pathname, search } = useLocation();
  const path = pathname.replace(/\/$/, '') || '/';
  const page = searchPages[path] ?? event;
  const noindex = !page || (path === '/eventos' && new URLSearchParams(search).get('aba') === 'meus');

  useEffect(() => {
    document.title = page?.title || 'Agenda UnB';
    if (path !== '/') document.head.querySelector('[data-agenda-search]')?.remove();
    const elements = [
      ['meta', 'name', 'description', 'content', page?.description],
      ['link', 'rel', 'canonical', 'href', !noindex ? siteUrl + path : undefined],
      ['meta', 'name', 'robots', 'content', noindex ? 'noindex' : undefined],
      ['meta', 'property', 'og:title', 'content', !noindex ? page?.title : undefined],
      ['meta', 'property', 'og:description', 'content', !noindex ? page?.description : undefined],
      ['meta', 'property', 'og:url', 'content', !noindex ? siteUrl + path : undefined],
    ];
    for (const [tag, key, name, attr, value] of elements) {
      const existing = document.head.querySelector(`${tag}[${key}="${name}"]`);
      if (!value) {
        existing?.remove();
        continue;
      }
      const node = existing || document.createElement(tag);
      node.setAttribute(key, name);
      node.setAttribute(attr, value);
      if (!existing) document.head.append(node);
    }
  }, [noindex, page?.title, page?.description, path]);

  return null;
}
