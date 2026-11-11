import { request } from './api';
export const catalogApi = {
  shared: (id, offset, signal) => request(`/class-offerings/${encodeURIComponent(id)}/shared-plans?limit=20&offset=${offset}`, { auth: true, signal }),
  get: (id, signal) => request(`/class-offerings/${encodeURIComponent(id)}`, { auth: true, signal }),
  filters: signal => request('/class-offerings/filters', { auth: true, signal }),
  search: (filters, signal) => request(`/class-offerings?${new URLSearchParams(filters)}`, { auth: true, signal }),
  followed: signal => request('/me/class-offerings', { auth: true, signal }),
  follow: (id, following, signal) => request(`/me/class-offerings/${encodeURIComponent(id)}`, { auth: true, method: following ? 'PUT' : 'DELETE', signal }),
};
