import { request } from './api';

export const remindersApi = {
  list: (limit, offset) => request(`/me/reminders?${new URLSearchParams({ limit, offset })}`, { auth: true }),
  markRead: id => request(`/me/reminders/${encodeURIComponent(id)}/read`, { method: 'PUT', auth: true }),
};
