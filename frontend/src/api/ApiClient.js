const BASE_URL = '/api/v1';

function getToken() {
  try {
    const stored = localStorage.getItem('auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.token || parsed.access_token || null;
    }
  } catch {

  }
  return null;
}

async function request(method, path, body = null) {
  const headers = {
    'Content-Type': 'application/json',
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = { method, headers };
  if (body) {
    config.body = JSON.stringify(body);
  }

  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, config);

  if (!response.ok) {
    let detail = '';
    try {
      const errBody = await response.json();
      detail = errBody.detail || errBody.message || '';
    } catch {

    }
    const error = new Error(detail || `API ${response.status}: ${response.statusText}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;

  return response.json();
}

const ApiClient = {
  get(path) {
    return request('GET', path);
  },

  post(path, body) {
    return request('POST', path, body);
  },

  put(path, body) {
    return request('PUT', path, body);
  },

  patch(path, body) {
    return request('PATCH', path, body);
  },

  delete(path) {
    return request('DELETE', path);
  },
};

export default ApiClient;
