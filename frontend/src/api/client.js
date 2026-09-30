const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api/v1';

export function toApiError(body, status) {
  const detail = Array.isArray(body.detail)
    ? body.detail.map((e) => e.msg).join('; ')
    : body.detail || `Request failed with status ${status}`;
  const error = new Error(detail);
  if (body.code) error.code = body.code;
  error.status = status;
  return error;
}

export async function fetchJson(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };

  const response = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include', ...options, headers });

  if (response.status === 401) {
    const body = await response.json().catch(() => ({}));
    window.dispatchEvent(new CustomEvent('auth:logout'));
    throw toApiError(body, response.status);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw toApiError(body, response.status);
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

export { API_BASE_URL };
