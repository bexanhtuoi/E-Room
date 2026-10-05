import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE = __ENV.BASE || "http://localhost:8000";
const POOL = parseInt(__ENV.POOL || "100", 10);
const AI_RATE = parseFloat(__ENV.AI_RATE || "0.05");

const aiTriggers = new Counter("ai_triggers");

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

const roomFull = new Counter("room_full");
const badStatus = new Counter("bad_status");

function ok(res) {
  const pass = check(res, { status_ok: (r) => [200, 201, 204].includes(r.status) });
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

const VOICE_ROOM = __ENV.VOICE_ROOM ? parseInt(__ENV.VOICE_ROOM, 10) : 0;

function roomOf(data) {
  if (VOICE_ROOM && Math.random() < 0.5) return VOICE_ROOM;
  if (!data.roomIds.length) return VOICE_ROOM || null;
  return data.roomIds[Math.floor(Math.random() * data.roomIds.length)];
}

function lurker(data) {
  const id = roomOf(data);
  if (!id) return;
  ok(http.get(`${BASE}/api/v1/rooms/${id}`, auth(data)));
  sleep(rnd(1, 3));
  ok(http.get(`${BASE}/api/v1/rooms/${id}/participants`, auth(data)));
  sleep(rnd(2, 5));
  ok(http.get(`${BASE}/api/v1/messages/?room_id=${id}&limit=30`, auth(data)));
  sleep(rnd(3, 8));
}

function chatter(data) {
  const id = roomOf(data);
  if (!id) return;
  okJoin(http.post(`${BASE}/api/v1/rooms/${id}/join`, null, auth(data)));
  sleep(rnd(1, 2));
  const n = 1 + Math.floor(Math.random() * 2);
  for (let i = 0; i < n; i++) {
    const ai = Math.random() < AI_RATE;
    const text = ai ? pick(AI_QS) : pick(CHAT);
    if (ai) aiTriggers.add(1);
    ok(
      http.post(`${BASE}/api/v1/messages/`, JSON.stringify({ room_id: id, text }), {
        headers: { "Content-Type": "application/json", ...(auth(data).headers) },
      })
    );
    sleep(rnd(2, 5));
  }
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
  sleep(rnd(3, 8));
}

function reader(data) {
  ok(http.get(`${BASE}/api/v1/users/me`, auth(data)));
  sleep(rnd(1, 2));
  ok(http.get(`${BASE}/api/v1/users/me/stats`, auth(data)));
  sleep(rnd(1, 2));
  const roll = Math.random();
  if (roll < 0.4) ok(http.get(`${BASE}/api/v1/notifications/`, auth(data)));
  else if (roll < 0.7) ok(http.get(`${BASE}/api/v1/documents/`, auth(data)));
  else ok(http.get(`${BASE}/api/v1/rooms/count`, auth(data)));
  sleep(rnd(3, 8));
}

export function apiTraffic(data) {
  const roll = Math.random();
  if (roll < 0.4) lurker(data);
  else if (roll < 0.7) chatter(data);
  else if (roll < 0.85) hopper(data);
  else reader(data);
}

export function voiceAnchor(data) {
  const id = VOICE_ROOM || data.roomIds[0];
  if (!id) return;
  const total = parseInt(__ENV.DURATION_S || "300", 10) || 300;
  const deadline = Date.now() + (total - 15) * 1000;
  let joined = false;
  while (Date.now() < deadline && !joined) {
    const res = http.post(`${BASE}/api/v1/rooms/${id}/join`, null, auth(data));
    joined = [200, 201, 204].includes(res.status);
    if (!joined) sleep(10);
  }
  if (!joined) return;
  sleep(Math.max(10, total - 30));
  http.post(`${BASE}/api/v1/rooms/${id}/leave`, null, auth(data));
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
