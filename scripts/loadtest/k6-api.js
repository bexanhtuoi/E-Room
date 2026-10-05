import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE = __ENV.BASE || "http://localhost:8000";
const POOL = parseInt(__ENV.POOL || "100", 10);
const AI_RATE = parseFloat(__ENV.AI_RATE || "0.0");
const CHAT_ON = (__ENV.SESSION_CHAT || "0") === "1";
const TTS_RATE = parseFloat(__ENV.TTS_RATE || "0.05");

const aiTriggers = new Counter("ai_triggers");
const roomFull = new Counter("room_full");
const badStatus = new Counter("bad_status");

const CHAT = [
  "Hello everyone, nice to meet you",
  "How do you practice speaking every day?",
  "I went to the market yesterday",
  "Travel is fun, what about you?",
  "Let's practice introducing ourselves",
  "My favorite hobby is reading books",
  "The weather is nice today, isn't it?",
  "I think English movies help a lot",
];

const AI_QS = ["@ai fix my pronunciation: hello world", "@ai give me a topic to discuss"];

function rnd(a, b) {
  return a + Math.random() * (b - a);
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function ok(res) {
  const pass = check(res, { status_ok: (r) => [200, 201, 204].includes(r.status) });
  if (!pass) badStatus.add(1);
  return pass;
}

function ok404(res) {
  const pass = check(res, { status_ok: (r) => [200, 201, 204, 404].includes(r.status) });
  if (!pass) badStatus.add(1);
  return pass;
}

function okJoin(res) {
  if (res.status === 403) {
    try {
      if (res.json().code === "ROOM_FULL") {
        roomFull.add(1);
        return true;
      }
    } catch (e) {}
  }
  return ok(res);
}

const SAVED = JSON.parse(open("./.tokens.json"));

export function setup() {
  const tokens = [];
  for (let i = 1; i <= POOL; i++) {
    const t = SAVED[`k6_${i}@gmail.com`];
    if (t) tokens.push(t);
  }
  if (!tokens.length) throw new Error("pool rong: chay ensure_pool.py truoc");
  const rooms = http.get(`${BASE}/api/v1/rooms/?public_only=true`, {
    headers: { Cookie: `access_token=${tokens[0] || ""}` },
  });
  let roomIds = [];
  try {
    roomIds = (rooms.json() || []).map((r) => r.id);
  } catch (e) {}
  return { tokens, roomIds };
}

function auth(data) {
  const t = data.tokens[(__VU - 1) % data.tokens.length];
  return { headers: { Cookie: `access_token=${t}` } };
}

function myEmail(data) {
  const i = ((__VU - 1) % data.tokens.length) + 1;
  return `k6_${i}@gmail.com`;
}

const VOICE_ROOMS = (__ENV.VOICE_ROOMS || "")
  .split(",")
  .map((s) => parseInt(s.trim(), 10))
  .filter((n) => n > 0);

function roomOf(data) {
  const pool = data.roomIds.filter((id) => !VOICE_ROOMS.includes(id));
  if (!pool.length) return VOICE_ROOMS[0] || null;
  return pool[Math.floor(Math.random() * pool.length)];
}

function J(data, method, path, body) {
  const p = {
    headers: { "Content-Type": "application/json", ...auth(data).headers },
  };
  if (method === "post") return http.post(`${BASE}${path}`, JSON.stringify(body || {}), p);
  return http.patch(`${BASE}${path}`, JSON.stringify(body || {}), p);
}

function lurker(data) {
  const id = roomOf(data);
  if (!id) return;
  ok(http.get(`${BASE}/api/v1/rooms/${id}`, auth(data)));
  sleep(rnd(1, 3));
  ok(http.get(`${BASE}/api/v1/rooms/${id}/participants`, auth(data)));
  sleep(rnd(2, 5));
  ok(http.get(`${BASE}/api/v1/messages/?room_id=${id}&limit=30`, auth(data)));
  sleep(rnd(1, 3));
  ok(http.get(`${BASE}/api/v1/rooms/${id}/speech-logs/summary`, auth(data)));
  sleep(rnd(3, 8));
}

function chatter(data) {
  const id = roomOf(data);
  if (!id) return;
  okJoin(http.post(`${BASE}/api/v1/rooms/${id}/join`, null, auth(data)));
  sleep(rnd(1, 2));
  let lastId = 0;
  const n = 1 + Math.floor(Math.random() * 2);
  for (let i = 0; i < n; i++) {
    const ai = Math.random() < AI_RATE;
    const text = ai ? pick(AI_QS) : pick(CHAT);
    if (ai) aiTriggers.add(1);
    const res = J(data, "post", "/api/v1/messages/", { room_id: id, text });
    if (ok(res)) {
      try {
        lastId = res.json().id || 0;
      } catch (e) {}
    }
    sleep(rnd(2, 5));
  }
  if (lastId) ok(http.get(`${BASE}/api/v1/messages/${lastId}`, auth(data)));
  ok(http.get(`${BASE}/api/v1/rooms/${id}/speech-logs/me`, auth(data)));
  sleep(rnd(2, 4));
  ok(http.post(`${BASE}/api/v1/rooms/${id}/leave`, null, auth(data)));
  sleep(rnd(3, 8));
}

function hopper(data) {
  for (let i = 0; i < 2; i++) {
    const id = roomOf(data);
    if (!id) return;
    okJoin(http.post(`${BASE}/api/v1/rooms/${id}/join`, null, auth(data)));
    sleep(rnd(1, 2));
    ok(http.post(`${BASE}/api/v1/rooms/${id}/leave`, null, auth(data)));
    sleep(rnd(1, 3));
  }
  ok(http.get(`${BASE}/api/v1/sessions/mine`, auth(data)));
  sleep(rnd(1, 2));
  ok(http.get(`${BASE}/api/v1/sessions/count`, auth(data)));
  const mine = http.get(`${BASE}/api/v1/sessions/mine`, auth(data));
  try {
    const s = (mine.json().sessions || [])[0];
    if (s) {
      ok(http.get(`${BASE}/api/v1/sessions/${s.session.id}`, auth(data)));
      ok(http.get(`${BASE}/api/v1/sessions/${s.session.id}/messages`, auth(data)));
      if (CHAT_ON) {
        J(data, "post", `/api/v1/sessions/${s.session.id}/chat`, { message: "hello" });
      }
    }
  } catch (e) {}
  sleep(rnd(3, 8));
}

function reader(data) {
  ok(http.get(`${BASE}/api/v1/users/me`, auth(data)));
  sleep(rnd(1, 2));
  ok(http.get(`${BASE}/api/v1/users/me/stats`, auth(data)));
  sleep(rnd(1, 2));
  const me = http.get(`${BASE}/api/v1/users/me`, auth(data));
  try {
    const uid = me.json().id;
    if (uid) {
      ok(http.get(`${BASE}/api/v1/users/${uid}`, auth(data)));
      ok404(http.get(`${BASE}/api/v1/users/${uid}/avatar/file`, auth(data)));
    }
  } catch (e) {}
  const roll = Math.random();
  if (roll < 0.25) ok(http.get(`${BASE}/api/v1/notifications/`, auth(data)));
  else if (roll < 0.45) ok(http.get(`${BASE}/api/v1/documents/`, auth(data)));
  else if (roll < 0.6) ok(http.get(`${BASE}/api/v1/rooms/count`, auth(data)));
  else if (roll < 0.72) ok(http.get(`${BASE}/api/v1/users/?limit=5`, auth(data)));
  else if (roll < 0.82) ok(http.get(`${BASE}/api/v1/tts/voices`, auth(data)));
  else if (roll < 0.9) ok(http.get(`${BASE}/api/v1/rooms/prompt-default`, auth(data)));
  else ok(http.get(`${BASE}/api/v1/documents/count`, auth(data)));
  sleep(rnd(3, 8));
}

function creator(data) {
  const name = `K6R-${__VU}-${Date.now() % 100000}`;
  const res = J(data, "post", "/api/v1/rooms/", { name });
  let id = 0;
  if (ok(res)) {
    try {
      id = res.json().id || 0;
    } catch (e) {}
  }
  sleep(rnd(1, 2));
  if (id) {
    ok(http.post(`${BASE}/api/v1/rooms/match`, JSON.stringify({}), {
      headers: { "Content-Type": "application/json", ...auth(data).headers },
    }));
    ok(http.get(`${BASE}/api/v1/rooms/${id}/token`, auth(data)));
    ok(http.get(`${BASE}/api/v1/rooms/${id}/documents`, auth(data)));
    J(data, "patch", `/api/v1/rooms/${id}`, { description: "k6 room" });
    sleep(rnd(1, 2));
    ok(http.del(`${BASE}/api/v1/rooms/${id}`, null, auth(data)));
  }
  sleep(rnd(3, 8));
}

function manager(data) {
  const res = J(data, "post", "/api/v1/notifications/", { title: "k6", body: "hi" });
  let id = 0;
  if (ok(res)) {
    try {
      id = res.json().id || 0;
    } catch (e) {}
  }
  sleep(rnd(1, 2));
  if (id) {
    ok(http.get(`${BASE}/api/v1/notifications/count`, auth(data)));
    J(data, "patch", `/api/v1/notifications/${id}`, { is_read: true });
    ok(http.del(`${BASE}/api/v1/notifications/${id}`, null, auth(data)));
  }
  sleep(rnd(3, 8));
}

function writer(data) {
  const id = roomOf(data);
  if (!id) return;
  const res = J(data, "post", "/api/v1/messages/", { room_id: id, text: pick(CHAT) });
  let mid = 0;
  if (ok(res)) {
    try {
      mid = res.json().id || 0;
    } catch (e) {}
  }
  sleep(rnd(1, 2));
  if (mid) {
    ok(http.get(`${BASE}/api/v1/messages/count?room_id=${id}`, auth(data)));
    if (Math.random() < 0.5) {
      J(data, "post", `/api/v1/rooms/${id}/speech-logs/${mid}/score`, {});
    }
    ok(http.del(`${BASE}/api/v1/messages/${mid}`, null, auth(data)));
  }
  if (Math.random() < TTS_RATE) {
    J(data, "post", "/api/v1/tts/speak", { text: "hello test" });
  }
  sleep(rnd(3, 8));
}

function account(data) {
  const me = http.get(`${BASE}/api/v1/users/me`, auth(data));
  if (ok(me)) {
    try {
      const uid = me.json().id;
      if (uid) J(data, "patch", `/api/v1/users/${uid}`, { headline: "k6" });
    } catch (e) {}
  }
  sleep(rnd(1, 2));
  const res = http.get(`${BASE}/api/v1/users/email/${myEmail(data)}`, auth(data));
  ok(res);
  sleep(rnd(1, 2));
  ok(http.get(`${BASE}/api/v1/users/role/user`, auth(data)));
  sleep(rnd(3, 8));
}

export function apiTraffic(data) {
  const roll = Math.random();
  if (roll < 0.3) chatter(data);
  else if (roll < 0.52) lurker(data);
  else if (roll < 0.62) hopper(data);
  else if (roll < 0.74) reader(data);
  else if (roll < 0.82) creator(data);
  else if (roll < 0.88) manager(data);
  else if (roll < 0.94) writer(data);
  else if (roll < 0.97) account(data);
  else reader(data);
}

export function voiceAnchor(data) {
  const ids = VOICE_ROOMS.length ? VOICE_ROOMS : [data.roomIds[0]].filter(Boolean);
  if (!ids.length) return;
  const total = parseInt(__ENV.DURATION_S || "300", 10) || 300;
  const perRoom = Math.max(20, Math.floor((total - 15) / ids.length));
  for (const id of ids) {
    const deadline = Date.now() + perRoom * 1000;
    let joined = false;
    while (Date.now() < deadline && !joined) {
      const res = http.post(`${BASE}/api/v1/rooms/${id}/join`, null, auth(data));
      joined = [200, 201, 204].includes(res.status);
      if (!joined) sleep(10);
    }
    if (joined) sleep(Math.max(5, perRoom - 15));
    http.post(`${BASE}/api/v1/rooms/${id}/leave`, null, auth(data));
  }
}

export const options = {
  scenarios: {
    api: {
      executor: "constant-vus",
      vus: parseInt(__ENV.USERS || "50", 10),
      exec: "apiTraffic",
      duration: __ENV.DURATION || "5m",
    },
    anchor: {
      executor: "constant-vus",
      vus: 1,
      exec: "voiceAnchor",
      duration: __ENV.DURATION || "5m",
    },
  },
  thresholds: {
    checks: ["rate>0.98"],
    bad_status: ["count<5"],
    http_req_duration: ["p(95)<500"],
  },
};
