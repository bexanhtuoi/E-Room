import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiChatBubbleLeftRight, HiClock, HiPencil, HiSparkles, HiSpeakerWave, HiUsers } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { Face } from '../../components/common/Faces';
import { ReadingScoreCard } from './ReadingScoreCard';
import { VoicePicker } from '../chat/VoicePicker';
import { getStoredVoice, speakToAudioUrl, storeVoice } from '../chat/voiceApi';
import '../../styles/ProfilePage.css';

function parseTranscript(text) {
  return String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, i) => {
      const cut = line.indexOf(':');
      return {
        id: i,
        speaker: cut > 0 ? line.slice(0, cut).trim() : null,
        body: cut > 0 ? line.slice(cut + 1).trim() : line,
      };
    });
}

function formatDuration(seconds) {
  if (seconds == null) return 'ongoing';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function formatShortDateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return `${date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}, ${date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`;
}

// Backend lưu joined_at/left_at dạng naive UTC ("2026-09-26 21:59:07",
// không suffix timezone), còn utterance.created_at là ISO có +00:00.
// Date.parse chuỗi naive theo giờ LOCAL của browser (+07) sẽ lệch 7 tiếng
// và lọc sai (câu 21:59 UTC bị coi là sau left_at) — nên ép naive về UTC
// cho khớp cách backend so sánh (as_naive_utc).
export function parseSessionTime(value) {
  if (!value) return NaN;
  let s = String(value).trim().replace(' ', 'T');
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) s += 'Z';
  return Date.parse(s);
}

export function inWindow(iso, startIso, endIso) {
  const t = Date.parse(iso || '');
  if (Number.isNaN(t)) return false;
  if (startIso) {
    const s = parseSessionTime(startIso);
    if (!Number.isNaN(s) && t < s) return false;
  }
  if (endIso) {
    const e = parseSessionTime(endIso);
    if (!Number.isNaN(e) && t > e) return false;
  }
  return true;
}

// Nhiều utterance cùng 1 attempt được chấm chung 1 bản điểm
// (backend dùng raw.wav + toàn bộ text của attempt). Gộp hiển thị
// còn 1 thẻ cho gọn — giữ utterance đầu tiên của mỗi attempt.
export function dedupeByAttempt(list) {
  const seen = new Set();
  const out = [];
  for (const u of Array.isArray(list) ? list : []) {
    const aid = u?.pronunciation?.attempt_id;
    const key = aid != null ? `attempt:${aid}` : `msg:${u?.message_id ?? u?.created_at}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(u);
  }
  return out;
}

// Cache object URL theo giọng + câu để bấm loa lần 2 không gọi TTS lại.
const ttsCache = new Map();

// Cụm nút icon đồng cỡ cho mỗi dòng transcript (loa + bút chì).
const iconBtn = {
  width: 28, height: 28, padding: 0,
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
};
const rowActions = { display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 };

function SpeakButton({ text, voice }) {
  const [state, setState] = useState('idle'); // idle | loading | playing | error
  async function play() {
    const clean = String(text || '').trim();
    if (!clean || state === 'loading') return;
    setState('loading');
    try {
      const key = `${voice}::${clean}`;
      let url = ttsCache.get(key);
      if (!url) {
        url = await speakToAudioUrl(clean, voice);
        ttsCache.set(key, url);
      }
      const audio = new Audio(url);
      setState('playing');
      audio.onended = () => setState('idle');
      audio.onerror = () => setState('error');
      await audio.play();
    } catch {
      setState('error');
    }
  }
  return (
    <button
      type="button"
      className="portal-topic pf-chipbtn"
      onClick={play}
      disabled={state === 'loading'}
      title={state === 'error' ? 'TTS chưa sẵn sàng (server Kokoro :8002)' : 'Nghe mẫu đọc đúng'}
      aria-label={`Nghe: ${String(text || '').slice(0, 40)}`}
      style={iconBtn}
    >
      <HiSpeakerWave size={14} /> {state === 'loading' ? '…' : state === 'playing' ? '▶' : ''}
    </button>
  );
}

export function SessionScoringView({ sessionId: propSessionId }) {
  const params = useParams();
  const sessionId = propSessionId || params.sessionId;
  const [voice, setVoice] = useState(() => getStoredVoice());

  // AI feedbacks (LLM local cấp session, prompt gọn chỉ mô tả phần sai).
  const [sessionFb, setSessionFb] = useState(null);
  const [sessionFbCount, setSessionFbCount] = useState(null);
  const [fbLoading, setFbLoading] = useState(false);
  const [fbError, setFbError] = useState('');

  // Chấm tuần tự: chỉ 1 lượt chấm chạy tại 1 thời điểm (máy host).
  const [busyScoreKey, setBusyScoreKey] = useState(null);
  const [scoreError, setScoreError] = useState('');
  const [busyFbKey, setBusyFbKey] = useState(null);
  // Tự sửa câu đã nói trong What was said.
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  const detailQuery = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchJson(`/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
    retry: false,
  });
  const messagesQuery = useQuery({
    queryKey: ['session', sessionId, 'messages'],
    queryFn: () => fetchJson(`/sessions/${sessionId}/messages`),
    enabled: Boolean(sessionId),
    retry: false,
  });

  const detail = detailQuery.data ?? null;
  const session = detail?.session ?? null;
  const room = detail?.room ?? null;

  // Cách 1: đọc câu của chính mình từ speech log scope ROOM (đã có điểm thì
  // hiện, chưa chấm thì chấm tại chỗ). Điểm thật nằm trong DB
  // (pronunciation_scores), JSONL chỉ là log raw/audio.
  const speechQuery = useQuery({
    queryKey: ['session', sessionId, 'speech'],
    queryFn: () => fetchJson(`/rooms/${room.id}/speech-logs/me`),
    enabled: Boolean(room?.id),
    retry: false,
  });
  const myUtterances = useMemo(() => {
    const list = Array.isArray(speechQuery.data) ? speechQuery.data : [];
    if (!session) return [];
    const inSession = list.filter((u) => inWindow(u?.created_at, session.joined_at, session?.left_at));
    return dedupeByAttempt(inSession);
  }, [speechQuery.data, session]);

  function changeVoice(next) {
    setVoice(next);
    storeVoice(next);
  }

  async function askSessionFeedback() {
    if (fbLoading) return;
    setFbLoading(true);
    setFbError('');
    try {
      const res = await fetchJson(`/sessions/${sessionId}/feedback`, { method: 'POST' });
      setSessionFb(res?.feedback || null);
      setSessionFbCount({ scored: res?.scored_count ?? 0, total: res?.total_utterances ?? 0 });
    } catch (error) {
      setFbError(error?.message || 'AI could not answer right now');
    } finally {
      setFbLoading(false);
    }
  }

  async function scoreUtterance(entry) {
    const key = entry?.message_id ?? entry?.created_at ?? Math.random();
    if (busyScoreKey !== null || entry?.message_id == null) {
      if (entry?.message_id == null) setScoreError('Câu log cũ không có message_id — không chấm lại được.');
      return;
    }
    setBusyScoreKey(key);
    setScoreError('');
    try {
      await fetchJson(`/rooms/${room.id}/speech-logs/${entry.message_id}/score`, { method: 'POST' });
      await speechQuery.refetch();
    } catch (error) {
      setScoreError(error?.message || 'Chấm điểm thất bại');
    } finally {
      setBusyScoreKey(null);
    }
  }

  async function feedbackUtterance(entry) {
    const key = entry?.message_id ?? entry?.created_at ?? Math.random();
    if (entry?.message_id == null) return;
    setBusyFbKey(key);
    setScoreError('');
    try {
      await fetchJson(`/rooms/${room.id}/speech-logs/${entry.message_id}/feedback`, { method: 'POST', body: JSON.stringify({}) });
      await speechQuery.refetch();
    } catch (error) {
      setScoreError(error?.message || 'Xin nhận xét thất bại');
    } finally {
      setBusyFbKey(null);
    }
  }

  const lines = useMemo(() => {
    const structured = messagesQuery.data?.transcript_lines;
    if (Array.isArray(structured) && structured.length > 0) {
      return structured.map((line, i) => ({
        id: line?.message_id ?? i,
        speaker: line?.speaker || null,
        body: line?.text ?? '',
        message_id: line?.message_id ?? null,
      }));
    }
    return parseTranscript(messagesQuery.data?.transcript);
  }, [messagesQuery.data]);
  // Câu của chính mình (theo message_id) để hiện nút Sửa + bản đã sửa.
  const myUtteranceById = useMemo(() => {
    const map = new Map();
    for (const u of myUtterances) {
      if (u?.message_id != null) map.set(u.message_id, u);
    }
    return map;
  }, [myUtterances]);

  async function saveEdit(line) {
    const clean = editText.trim();
    if (!clean || !line?.message_id || editSaving) return;
    setEditSaving(true);
    setScoreError('');
    try {
      await fetchJson(`/rooms/${room.id}/speech-logs/${line.message_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ corrected_text: clean }),
      });
      setEditingId(null);
      // Sửa sau khi chấm thì backend reset điểm → tải lại cả 2 nguồn.
      await Promise.all([speechQuery.refetch(), messagesQuery.refetch()]);
    } catch (error) {
      setScoreError(error?.message || 'Sửa câu thất bại');
    } finally {
      setEditSaving(false);
    }
  }
  const speakers = useMemo(() => [...new Set(lines.map((l) => l.speaker).filter(Boolean))], [lines]);
  const lineCount = detail?.message_count ?? 0;
  const emptySession = !messagesQuery.isLoading && lineCount === 0;

  if (detailQuery.isLoading || messagesQuery.isLoading) {
    return (
      <div className="portal-app portal-app--page"><main className="portal-main pf-center--wide"><div className="portal-skeleton"><span /><span /><span /></div></main></div>
    );
  }

  if (detailQuery.isError || !session) {
    return (
      <div className="portal-app portal-app--page">
        <main className="portal-main pf-center--wide">
          <div className="er-alert er-alert--err">Session not found or you have no access.</div>
          <Link className="er-btn" style={{ textDecoration: 'none', marginTop: 12 }} to="/assessment"><HiArrowLeft size={14} /> Assessment</Link>
        </main>
      </div>
    );
  }

  const roomName = room?.name || `Room ${session.room_id}`;
  const topics = Array.isArray(room?.topics) ? room.topics : [];

  return (
    <div className="portal-app portal-app--page">
      <main className="portal-main pf-center--wide">
        <div className="portal-pagehead">
          <div>
            <div className="pf-crumb"><Link to="/assessment">Assessment</Link> / #{session.id} · <Link to={`/session/${session.id}`}>View session</Link></div>
          </div>
        </div>

        <section className="portal-panel pf-sesscard">
          <div className="pf-sesscard__top">
            <span className="portal-room__tile pf-room__tile--lg">{roomName.trim().charAt(0).toUpperCase()}</span>
            <div className="pf-sesscard__title">
              <h1>{roomName}</h1>
              {topics.length > 0 && (
                <div className="portal-topics">{topics.slice(0, 5).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
              )}
            </div>
          </div>
          <div className="portal-grid2 pf-sesscard__facts">
            <div className="portal-block">
              <div className="portal-block__label"><HiClock size={12} /> Duration</div>
              <div className="portal-block__value">{formatDuration(session.duration_seconds)}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label"><HiChatBubbleLeftRight size={12} /> Lines said</div>
              <div className="portal-block__value">{lineCount}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label"><HiUsers size={12} /> Speakers</div>
              <div className="portal-block__value">{speakers.length > 0 ? speakers.join(', ') : '—'}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label">When</div>
              <div className="portal-block__value portal-muted">
                {formatShortDateTime(session.joined_at)} - {session.left_at ? formatShortDateTime(session.left_at) : 'now'}
              </div>
            </div>
          </div>
          {room?.description && <p className="portal-muted pf-sesscard__desc">{room.description}</p>}
        </section>

        <div className="portal-stack" style={{ marginTop: 16 }}>
          <section className="portal-panel pf-aichat">
            <div className="portal-panel__head">
              <h2><HiSparkles size={15} /> AI feedbacks</h2>
              {sessionFbCount && <span className="portal-muted">{sessionFbCount.scored} scored lines</span>}
            </div>
            {emptySession ? (
              <div className="portal-empty">No transcript in this session — nothing was said while you were inside, so AI has nothing to read.</div>
            ) : !sessionFb ? (
              <>
                <p className="portal-muted" style={{ fontSize: 13 }}>
                  AI đọc điểm các câu bạn đã chấm trong session này rồi góp ý gọn:
                  chỉ nêu từ sai / mất hơi, cách sửa và 3 bước luyện. Chưa chấm câu nào thì chấm ở mục dưới trước.
                </p>
                <button type="button" className="er-btn" disabled={fbLoading} onClick={askSessionFeedback}>
                  {fbLoading ? 'AI đang đọc điểm…' : 'Get AI feedback'}
                </button>
                {fbError && <div className="er-alert er-alert--err" style={{ marginTop: 8 }}>{fbError}</div>}
              </>
            ) : (
              <>
                <SessionFeedbackBody feedback={sessionFb} />
                <div style={{ marginTop: 10 }}>
                  <button type="button" className="er-btn" disabled={fbLoading} onClick={askSessionFeedback}>
                    {fbLoading ? 'AI đang đọc điểm…' : 'Refresh feedback'}
                  </button>
                </div>
                {fbError && <div className="er-alert er-alert--err" style={{ marginTop: 8 }}>{fbError}</div>}
              </>
            )}
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2>My pronunciation scores</h2>
              <span className="portal-muted">{myUtterances.length} lines</span>
            </div>
            {speechQuery.isError ? (
              <div className="portal-empty">Chưa tải được câu đã nói (speech log). Vào phòng nói vài câu rồi quay lại.</div>
            ) : speechQuery.isLoading ? (
              <div className="portal-skeleton"><span /><span /></div>
            ) : myUtterances.length === 0 ? (
              <div className="portal-empty">Bạn chưa nói câu nào trong session này (hoặc câu nói chưa vào log).</div>
            ) : (
              <div className="portal-stack">
                {myUtterances.map((u, i) => {
                  const key = u?.message_id ?? u?.created_at ?? i;
                  return (
                    <ReadingScoreCard
                      key={key}
                      utterance={{
                        text: u?.text,
                        corrected_text: u?.corrected_text || u?.text,
                        pronunciation: u?.pronunciation || null,
                        feedback: u?.feedback || null,
                      }}
                      scoring={busyScoreKey === key}
                      feedbackLoading={busyFbKey === key}
                      scoreDisabled={busyScoreKey !== null && busyScoreKey !== key}
                      onScore={() => scoreUtterance(u)}
                      onFeedback={() => feedbackUtterance(u)}
                    />
                  );
                })}
              </div>
            )}
            {scoreError && <div className="er-alert er-alert--err" style={{ marginTop: 8 }}>{scoreError}</div>}
            {busyScoreKey !== null && (
              <p className="portal-muted" style={{ fontSize: 12, marginTop: 8 }}>
                Máy host đang chấm 1 câu — các nút chấm khác tạm khóa để không quá tải (chấm tuần tự).
              </p>
            )}
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2>What was said</h2>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="portal-muted">{lines.length} lines</span>
                <VoicePicker value={voice} onChange={changeVoice} />
              </span>
            </div>
            {lines.length === 0 ? (
              <div className="portal-empty">No messages were said while you were inside.</div>
            ) : (
              <div className="portal-list">
                {lines.map((line) => {
                  const mine = line.message_id != null ? myUtteranceById.get(line.message_id) : null;
                  const corrected = mine?.corrected_text || null;
                  const isEdited = corrected && corrected !== line.body;
                  const shown = corrected || line.body;
                  const isEditing = editingId === line.id;
                  return (
                    <div key={line.id} className="portal-row">
                      <Face name={line.speaker || '?'} size={30} />
                      <span className="portal-row__main">
                        {line.speaker && <span className="portal-row__text">{line.speaker}</span>}
                        {isEditing ? (
                          <span style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                            <input
                              className="er-input" value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              aria-label="Sửa câu đã nói"
                              disabled={editSaving}
                              style={{ flex: 1, fontSize: 13 }}
                            />
                            <button type="button" className="er-btn" disabled={editSaving || !editText.trim()} onClick={() => saveEdit(line)}>
                              {editSaving ? '…' : 'Lưu'}
                            </button>
                            <button type="button" className="portal-topic pf-chipbtn" disabled={editSaving} onClick={() => setEditingId(null)}>
                              Hủy
                            </button>
                          </span>
                        ) : (
                          <span className={line.speaker ? 'portal-row__sub pf-chattext' : 'portal-row__text pf-chattext'}>
                            {shown}
                            {isEdited && <span className="portal-badge" style={{ marginLeft: 6 }} title="Bạn đã sửa lại câu này (bản STT gốc đã thay bằng bản sửa)">đã sửa</span>}
                          </span>
                        )}
                        {mine?.pronunciation == null && isEdited && (
                          <span className="portal-muted" style={{ fontSize: 12 }}>Câu đã sửa nên điểm cũ bị xóa — chấm lại ở mục My pronunciation scores.</span>
                        )}
                      </span>
                      {!isEditing && (
                        <span style={rowActions}>
                          {mine && (
                            <button
                              type="button" className="portal-topic pf-chipbtn"
                              title="Tự sửa lại câu này"
                              aria-label={`Sửa: ${line.body.slice(0, 40)}`}
                              onClick={() => { setEditingId(line.id); setEditText(shown); }}
                              style={iconBtn}
                            >
                              <HiPencil size={14} />
                            </button>
                          )}
                          <SpeakButton text={shown} voice={voice} />
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function SessionFeedbackBody({ feedback }) {
  if (!feedback) return null;
  if (feedback.feedback_raw) {
    return <p style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{feedback.feedback_raw}</p>;
  }
  const errors = Array.isArray(feedback.error_words) ? feedback.error_words : [];
  const plan = Array.isArray(feedback.practice_plan) ? feedback.practice_plan : [];
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {feedback.summary && <p style={{ fontSize: 14, margin: 0, lineHeight: 1.55 }}>{feedback.summary}</p>}
      {errors.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Words to fix</div>
          <ul style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {errors.map((e, i) => (
              <li key={i}><b>{e.word}</b> — {e.issue}{e.tip ? ` → ${e.tip}` : ''}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Practice plan</div>
          <ol style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {plan.map((step, i) => <li key={i}>{step}</li>)}
          </ol>
        </div>
      )}
      {!feedback.summary && errors.length === 0 && plan.length === 0 && (
        <p className="portal-muted" style={{ fontSize: 13 }}>AI không trả đúng định dạng — bấm Refresh để thử lại.</p>
      )}
    </div>
  );
}
