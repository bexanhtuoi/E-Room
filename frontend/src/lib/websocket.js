

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = API_BASE_URL.replace(/^http/, 'ws');
const PING_INTERVAL = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY = 1000;

export class RoomSocket {
  constructor(roomId, token, options = {}) {
    this.roomId = roomId;
    this.token = token;
    this.onEvent = options.onEvent || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxAttempts = options.maxAttempts || MAX_RECONNECT_ATTEMPTS;
    this.baseDelay = options.baseDelay || BASE_RECONNECT_DELAY;
    this._intentionalClose = false;
    this._pingTimer = null;
    this.ws = null;

    this.connect();
  }

  get status() {
    if (!this.ws) return 'disconnected';
    const map = { 0: 'connecting', 1: 'connected', 2: 'closing', 3: 'disconnected' };
    return map[this.ws.readyState] || 'unknown';
  }

  connect() {
    if (this._intentionalClose) return;

    const url = `${WS_BASE}/ws/rooms/${this.roomId}?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._startPing();
      this.onStatusChange('connected');
      this._emit('connected');
    };

    this.ws.onclose = (event) => {
      this._stopPing();
      if (!this._intentionalClose && this.reconnectAttempts < this.maxAttempts) {
        this._scheduleReconnect();
      } else {
        this.onStatusChange('disconnected');
        this._emit('disconnected', { code: event.code, reason: event.reason });
      }
    };

    this.ws.onerror = () => {

      this.ws.close();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.onEvent(msg.type, msg);
        this._emit(msg.type, msg);
        this._emit('message', msg);
      } catch (err) {
        console.warn('[RoomSocket] Failed to parse message:', err);
      }
    };
  }

  _scheduleReconnect() {
    const delay = Math.min(
      this.baseDelay * Math.pow(2, this.reconnectAttempts),
      30_000
    );
    this.reconnectAttempts++;
    this.onStatusChange('reconnecting', { attempt: this.reconnectAttempts, delay });
    this._emit('reconnecting', { attempt: this.reconnectAttempts, delay });

    setTimeout(() => this.connect(), delay);
  }

  _startPing() {
    this._stopPing();
    this._pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, PING_INTERVAL);
  }

  _stopPing() {
    if (this._pingTimer) {
      clearInterval(this._pingTimer);
      this._pingTimer = null;
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  close() {
    this._intentionalClose = true;
    this._stopPing();
    if (this.ws) {
      this.ws.close(1000, 'Client closed');
      this.ws = null;
    }
    this.onStatusChange('disconnected');
    this._emit('disconnected', { intentional: true });
    this.listeners.clear();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    const set = this.listeners.get(event);
    if (set) {
      set.delete(callback);
      if (set.size === 0) this.listeners.delete(event);
    }
  }

  _emit(event, data) {
    const set = this.listeners.get(event);
    if (set) {
      set.forEach((cb) => {
        try { cb(data); } catch (err) { console.warn('[RoomSocket] Listener error:', err); }
      });
    }
  }
}

export function createRoomSocket(roomId, onMessage) {
  const url = `${WS_BASE}/ws/rooms/${roomId}`;
  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      onMessage(msg);
    } catch {}
  };

  return ws;
}

export default RoomSocket;
