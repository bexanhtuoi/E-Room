import React from 'react';

/**
 * ReadingScoreCard — thẻ kết quả chấm điểm đọc bằng AI.
 *
 * Quy ước UX:
 * 1. Chưa chấm: đúng 1 nút "Chấm điểm AI".
 * 2. Đã chấm: mặc định CHỈ hiện điểm tổng + 4 tiêu chí (gọn, không rườm rà).
 *    Chi tiết (bảng từng chữ, nhận xét AI) ẩn sau 2 nút toggle
 *    "Thống kê điểm số" / "Nhận xét AI" — ai tò mò thì mở.
 * 3. Thêm 1 nút "Chấm lại" để chấm lại điểm (backend reset feedback cũ).
 * 4. Sửa corrected_text sau khi chấm -> backend reset pronunciation + feedback
 *    về None (xem app/ai/speech_log.py::update_corrected_text), UI phải quay
 *    về trạng thái "chưa chấm".
 */

export function scoreColor(score) {
  const s = Number(score);
  if (Number.isNaN(s)) return '#888';
  if (s >= 85) return '#16a34a';
  if (s >= 70) return '#d97706';
  return '#dc2626';
}

export function statusLabel(status) {
  if (status === 'ok') return 'Good';
  if (status === 'pronunciation_error') return 'Needs practice';
  if (status === 'no_evidence') return 'Unclear audio';
  if (status === 'misaligned') return 'Misaligned';
  if (status === 'missing_span') return 'Missing timestamps';
  return status || '—';
}

function ScoreBar({ label, value }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 700 }}>
        <span>{label}</span>
        <span style={{ color: scoreColor(v) }}>{v.toFixed(1)}</span>
      </div>
      <div style={{ height: 8, borderRadius: 99, background: '#eee', overflow: 'hidden', marginTop: 4 }}>
        <div style={{ width: `${v}%`, height: '100%', background: scoreColor(v), transition: 'width .3s' }} />
      </div>
    </div>
  );
}

export function ReadingScoreCard({
  utterance,
  onScore,
  onFeedback,
  scoring = false,
  feedbackLoading = false,
  // scoreDisabled: parent khóa khi đang có 1 lượt chấm khác chạy (chấm tuần tự,
  // tránh dồn tải máy host khi 3-4 người bấm cùng lúc).
  scoreDisabled = false,
}) {
  // utterance: SpeechUtterance-like { text, corrected_text, pronunciation, feedback }
  // pronunciation: { score, method, details:{sounds,stress,fluency,completeness,...}, report:{scores,word_details,phonemes,top_errors,warnings} }
  const pron = utterance?.pronunciation || null;
  const feedback = utterance?.feedback || null;
  const report = pron?.report || null;
  const scoredText = pron?.scored_text || report?.texts?.user_corrected || null;

  const [showStats, setShowStats] = React.useState(false);
  const [showFeedback, setShowFeedback] = React.useState(false);

  // Đóng 2 panel khi chấm lại (điểm mới về) để giữ quy ước gọn mặc định.
  React.useEffect(() => {
    setShowStats(false);
    setShowFeedback(false);
  }, [scoredText, pron?.score]);

  if (!pron) {
    return (
      <div className="portal-panel" data-testid="reading-unscored">
        <div className="portal-panel__head"><h2>AI result</h2></div>
        <p className="portal-muted" style={{ fontSize: 13 }}>
          Not scored yet. Edit the sentence if needed, then press <b>Score with AI</b> — scoring
          uses your full edited text and the audio from start to end of the turn.
        </p>
        <button type="button" className="er-btn" disabled={scoring || scoreDisabled} onClick={onScore} title={scoreDisabled ? 'Another scoring run is in progress — please wait' : ''}>
          {scoring ? 'Scoring…' : 'Score with AI'}
        </button>
      </div>
    );
  }

  const details = pron.details || {};
  const scores = report?.scores || {
    sounds: details.sounds ?? 0,
    stress: details.stress ?? 0,
    fluency: details.fluency ?? 0,
    completeness: details.completeness ?? 0,
    overall: pron.score ?? 0,
  };
  const words = report?.word_details || [];
  const phonemes = report?.phonemes || [];
  const topErrors = report?.top_errors || details.top_errors || [];
  const warnings = report?.warnings || details.warnings || [];

  const isHeuristic = pron.method === 'heuristic-v1';
  // Heuristic = không đủ bằng chứng audio để chấm thật (không có report).
  // Hiện hướng dẫn thay vì thanh điểm gây hiểu lầm; nhận xét AI chỉ tự
  // chạy khi có report (effect ở trên đã chặn khi report null).
  const heuristicReason = pron.reason || 'unknown';

  const canAskFeedback = Boolean(report);

  return (
    <div className="portal-panel" data-testid="reading-scored">
      <div className="portal-panel__head">
        <h2>AI result</h2>
        <span className="portal-badge" title={pron.method || ''}>
          {(pron.score ?? 0).toFixed(1)} pts
        </span>
      </div>

      {/* Câu đã chấm: hiển thị TRƠN, không tô màu từng chữ (quy ước ẩn). */}
      <p style={{ fontSize: 15, lineHeight: 1.6 }} data-testid="reading-scored-text">
        {pron.scored_text || utterance?.corrected_text || utterance?.text}
      </p>

      {/* Heuristic (thiếu audio / scorer lỗi): hiện hướng dẫn thay vì thanh điểm.
          4 tiêu chí + tổng chỉ hiện sau khi chấm thật. */}
      {isHeuristic ? (
        <div className="er-alert er-alert--warn" style={{ marginTop: 12 }} data-testid="reading-heuristic">
          {heuristicReason === 'no_audio'
            ? 'Could not score because this turn has no audio (recording missing or lost). Go back to the room, say the sentence again, then rescore.'
            : heuristicReason === 'quiet_audio'
              ? 'The audio was too quiet for the AI to hear. Speak louder, closer to the mic, then press Rescore.'
              : heuristicReason === 'scorer_failed'
                ? 'The AI scorer hit an error, so this is only a rough estimate. Press Rescore to try the real scorer again.'
                : 'This score is only a rough estimate (missing scoring data). Rescore when audio is available.'}
          <div style={{ marginTop: 8 }}>
            <button type="button" className="er-btn" disabled={scoring || scoreDisabled} onClick={onScore}>
              {scoring ? 'Scoring…' : 'Rescore'}
            </button>
          </div>
        </div>
      ) : (
      <div style={{ marginTop: 12 }} data-testid="reading-overall">
        <ScoreBar label="Sounds" value={scores.sounds} />
        <ScoreBar label="Stress" value={scores.stress} />
        <ScoreBar label="Fluency" value={scores.fluency} />
        <ScoreBar label="Completeness" value={scores.completeness} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 800, marginTop: 6 }}>
          <span>Total</span>
          <span style={{ color: scoreColor(scores.overall ?? pron.score) }}>
            {Number(scores.overall ?? pron.score ?? 0).toFixed(1)}
          </span>
        </div>
      </div>
      )}

      {warnings.length > 0 && (
        <p className="portal-muted" style={{ fontSize: 12, marginTop: 8 }}>
          Note: {warnings[0]}
        </p>
      )}

      {/* 2 nút toggle + 1 nút chấm lại. */}
      <div className="pf-scoreactions" style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="er-btn"
          aria-expanded={showStats}
          onClick={() => setShowStats((v) => !v)}
          data-testid="btn-word-stats"
        >
          {showStats ? 'Hide score breakdown' : 'Score breakdown'}
        </button>
        <button
          type="button"
          className="er-btn"
          aria-expanded={showFeedback}
          disabled={!canAskFeedback || feedbackLoading}
          title={canAskFeedback ? '' : (isHeuristic ? 'This heuristic result has no audio, so feedback is unavailable — please rescore with the real scorer' : 'Score first, then request feedback')}
          onClick={() => {
            if (feedback) {
              setShowFeedback((v) => !v);
            } else if (onFeedback) {
              onFeedback();
              setShowFeedback(true);
            }
          }}
          data-testid="btn-ai-feedback"
        >
          {feedbackLoading ? 'Loading tips…' : feedback ? (showFeedback ? 'Hide tips' : 'Sentence tips') : 'Sentence tips'}
        </button>
        <button
          type="button"
          className="er-btn"
          disabled={scoring || scoreDisabled}
          title={scoreDisabled ? 'Another scoring run is in progress — please wait' : 'Rescore this sentence'}
          onClick={onScore}
          data-testid="btn-rescore"
        >
          {scoring ? 'Scoring…' : 'Rescore'}
        </button>
      </div>

      {/* Bảng điểm từng chữ — panel RIÊNG, chỉ render khi user mở. */}
      {showStats && (
      <div style={{ marginTop: 12 }} data-testid="word-stats-table">
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Word scores ({words.length})</h3>
          {words.length === 0 ? (
            <div className="portal-empty">No per-word details (the heuristic result has no word_details).</div>
          ) : (
            <div className="pf-tablewrap">
              <table className="portal-table" style={{ width: '100%', fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left' }}>Word</th>
                    <th style={{ textAlign: 'right' }}>Score</th>
                    <th style={{ textAlign: 'left' }}>Status</th>
                    <th style={{ textAlign: 'left' }}>IPA</th>
                  </tr>
                </thead>
                <tbody>
                  {words.map((w, i) => (
                    <tr key={`${w.word}-${i}`}>
                      <td style={{ fontWeight: 700 }}>{w.word}</td>
                      <td style={{ textAlign: 'right', color: scoreColor(w.score), fontWeight: 800 }}>
                        {w.status === 'no_evidence' ? '—' : Number(w.score ?? 0).toFixed(1)}
                      </td>
                      <td>{statusLabel(w.status)}</td>
                      <td className="portal-muted">{w.expected_ipa || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {topErrors.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <h4 style={{ fontSize: 13, marginBottom: 6 }}>Top sound errors</h4>
              <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
                {topErrors.map((e, i) => (
                  <li key={i}>
                    <b>{e.pattern}</b> ×{e.count}
                    {Array.isArray(e.examples) && e.examples.length > 0 && (
                      <span className="portal-muted"> — e.g.: {e.examples.join(', ')}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {phonemes.length > 0 && (
            <p className="portal-muted" style={{ fontSize: 12, marginTop: 8 }}>
              {phonemes.length} phonemes compared (the word table is enough for most learners).
            </p>
          )}
        </div>
      )}

      {/* Nhận xét AI — panel RIÊNG, chỉ render khi user mở. */}
      {showFeedback && (
      <div style={{ marginTop: 12 }} data-testid="ai-feedback-panel">
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>Sentence tips</h3>
        {!feedback ? (
          <div className="portal-empty">
            {feedbackLoading ? 'AI is reading your score table…' : 'Press “Sentence tips” to get suggestions — AI only reads the saved scores, it does not rescore.'}
          </div>
        ) : (
          <AIFeedbackBody feedback={feedback} />
        )}
      </div>
      )}
    </div>
  );
}

function AIFeedbackBody({ feedback }) {
  // AI trả JSON: summary, pronunciation_feedback, stress_feedback,
  // intonation_feedback, fluency_feedback, priority_errors, practice_plan
  // — hoặc { feedback_raw } khi model trả text thô.
  if (feedback.feedback_raw) {
    return <p style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{feedback.feedback_raw}</p>;
  }
  const blocks = [
    ['Overview', feedback.summary],
    ['Pronunciation', feedback.pronunciation_feedback],
    ['Stress', feedback.stress_feedback],
    ['Intonation', feedback.intonation_feedback],
    ['Fluency', feedback.fluency_feedback],
  ].filter(([, v]) => v);
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {blocks.map(([title, body]) => (
        <div key={title}>
          <div style={{ fontSize: 13, fontWeight: 800 }}>{title}</div>
          <p style={{ fontSize: 14, margin: '2px 0 0', lineHeight: 1.55 }}>{body}</p>
        </div>
      ))}
      {Array.isArray(feedback.priority_errors) && feedback.priority_errors.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Fix first</div>
          <ul style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {feedback.priority_errors.map((e, i) => (
              <li key={i}>
                <b>{e.word}</b>{e.vi ? ` (“${e.vi}”)` : ''} — {e.issue}
                {(e.advice || e.how_to || e.tip) ? <div style={{ color: '#555' }}>Fix: {e.advice || e.how_to || e.tip}</div> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {Array.isArray(feedback.practice_plan) && feedback.practice_plan.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Practice next</div>
          <ol style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {feedback.practice_plan.map((step, i) => <li key={i}>{step}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}
