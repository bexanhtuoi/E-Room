const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

function getTokens() {
  const access = localStorage.getItem('e-room-access-token');
  const refresh = localStorage.getItem('e-room-refresh-token');
  return { access, refresh };
}

function setTokens(access, refresh) {
  if (access) localStorage.setItem('e-room-access-token', access);
  if (refresh) localStorage.setItem('e-room-refresh-token', refresh);
}

function clearTokens() {
  localStorage.removeItem('e-room-access-token');
  localStorage.removeItem('e-room-refresh-token');
}

async function refreshTokens() {
  const { refresh } = getTokens();
  if (!refresh) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return { access: data.access_token, refresh: data.refresh_token };
  } catch {
    return null;
  }
}

export async function fetchJson(path, options = {}) {
  const { access } = getTokens();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (access) headers['Authorization'] = `Bearer ${access}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401 && path !== '/auth/refresh') {
    const refreshed = await refreshTokens();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${refreshed.access}`;
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
      if (!retryResponse.ok) {
        const body = await retryResponse.json().catch(() => ({}));
        const detail = Array.isArray(body.detail)
          ? body.detail.map((e) => e.msg).join('; ')
          : body.detail || `Request failed with status ${retryResponse.status}`;
        throw new Error(detail);
      }
      return retryResponse.json();
    }
    clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
    throw new Error('Session expired');
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((e) => e.msg).join('; ')
      : body.detail || `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return response.json();
}

export class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this._baseUrl = baseUrl;
  }

  async get(path, options = {}) {
    return fetchJson(path, { ...options, method: 'GET' });
  }

  async post(path, body, options = {}) {
    return fetchJson(path, { ...options, method: 'POST', body: JSON.stringify(body) });
  }

  async put(path, body, options = {}) {
    return fetchJson(path, { ...options, method: 'PUT', body: JSON.stringify(body) });
  }

  async patch(path, body, options = {}) {
    return fetchJson(path, { ...options, method: 'PATCH', body: JSON.stringify(body) });
  }

  async delete(path, options = {}) {
    return fetchJson(path, { ...options, method: 'DELETE' });
  }
}

export { getTokens, setTokens, clearTokens, API_BASE_URL };
