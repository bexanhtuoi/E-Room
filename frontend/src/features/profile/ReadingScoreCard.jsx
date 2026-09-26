import React from 'react';

/**
 * ReadingScoreCard — thẻ kết quả chấm điểm đọc bằng AI.
 *
 * Quy ước UX (đã khóa):
 * 1. Sau khi chấm xong, mặc định CHỈ hiện điểm tổng + 4 tiêu chí
 *    (Sounds / Stress / Fluency / Completeness). Điểm từng chữ (word_details)
 *    BỊ ẨN hoàn toàn — không tô màu chữ, không badge số trên câu.
 * 2. Muốn xem điểm từng chữ: bấm nút "Thống kê điểm số" -> mở BẢNG RIÊNG
 *    liệt kê word | điểm | trạng thái | IPA (collapsible, đóng mặc định).
 * 3. Nút "Nhận xét AI" là nút ĐỘC LẬP: gọi POST .../feedback (chỉ chạy khi
 *    đã có pronunciation.report, backend trả 409 nếu chưa chấm).
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
  if (status === 'ok') return 'Ổn';
  if (status === 'pronunciation_error') return 'Cần luyện';
  if (status === 'no_evidence') return 'Không nghe rõ';
  if (status === 'missing_span') return 'Thiếu mốc giờ';
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

  const [showStats, setShowStats] = React.useState(false);
  const [showFeedback, setShowFeedback] = React.useState(false);

  // Reset 2 panel khi chấm lại (điểm mới về) để giữ quy ước "ẩn mặc định".
  const scoredText = pron?.scored_text || report?.texts?.user_corrected || null;
  React.useEffect(() => {
    setShowStats(false);
    setShowFeedback(false);
  }, [scoredText, pron?.score]);

  if (!pron) {
    return (
      <div className="portal-panel" data-testid="reading-unscored">
        <div className="portal-panel__head"><h2>Kết quả AI</h2></div>
        <p className="portal-muted" style={{ fontSize: 13 }}>
          Chưa chấm. Sửa câu đúng ý bạn rồi bấm <b>Chấm điểm AI</b> — điểm chấm trên toàn bộ
          bản bạn đã sửa, dùng audio ĐẦU–CUỐI của lượt nói.
        </p>
        <button type="button" className="er-btn" disabled={scoring || scoreDisabled} onClick={onScore} title={scoreDisabled ? 'Đang có 1 lượt chấm chạy — đợi xong rồi chấm tiếp' : ''}>
          {scoring ? 'Đang chấm…' : 'Chấm điểm AI'}
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

  const canAskFeedback = Boolean(report);

  return (
    <div className="portal-panel" data-testid="reading-scored">
      <div className="portal-panel__head">
        <h2>Kết quả AI</h2>
        <span className="portal-badge" title={pron.method || ''}>
          {(pron.score ?? 0).toFixed(1)} điểm
        </span>
      </div>

      {/* Câu đã chấm: hiển thị TRƠN, không tô màu từng chữ (quy ước ẩn). */}
      <p style={{ fontSize: 15, lineHeight: 1.6 }} data-testid="reading-scored-text">
        {pron.scored_text || utterance?.corrected_text || utterance?.text}
      </p>

      {/* 4 tiêu chí + tổng — luôn hiện sau khi chấm. */}
      <div style={{ marginTop: 12 }} data-testid="reading-overall">
        <ScoreBar label="Sounds (âm)" value={scores.sounds} />
        <ScoreBar label="Stress (nhấn)" value={scores.stress} />
        <ScoreBar label="Fluency (trôi chảy)" value={scores.fluency} />
        <ScoreBar label="Completeness (đủ chữ)" value={scores.completeness} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 800, marginTop: 6 }}>
          <span>Tổng</span>
          <span style={{ color: scoreColor(scores.overall ?? pron.score) }}>
            {Number(scores.overall ?? pron.score ?? 0).toFixed(1)}
          </span>
        </div>
      </div>

      {warnings.length > 0 && (
        <p className="portal-muted" style={{ fontSize: 12, marginTop: 8 }}>
          Lưu ý: {warnings[0]}
        </p>
      )}

      {/* 2 nút độc lập — không gộp chung. */}
      <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="er-btn"
          aria-expanded={showStats}
          onClick={() => setShowStats((v) => !v)}
          data-testid="btn-word-stats"
        >
          {showStats ? 'Ẩn thống kê điểm số' : 'Thống kê điểm số'}
        </button>
        <button
          type="button"
          className="er-btn"
          aria-expanded={showFeedback}
          disabled={!canAskFeedback || feedbackLoading}
          title={canAskFeedback ? '' : 'Chấm điểm trước rồi mới xin nhận xét'}
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
          {feedbackLoading ? 'AI đang nhận xét…' : feedback ? (showFeedback ? 'Ẩn nhận xét AI' : 'Nhận xét AI') : 'Nhận xét AI'}
        </button>
      </div>

      {/* Bảng điểm từng chữ — panel RIÊNG, chỉ render khi user mở. */}
      {showStats && (
        <div style={{ marginTop: 12 }} data-testid="word-stats-table">
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Điểm từng chữ ({words.length})</h3>
          {words.length === 0 ? (
            <div className="portal-empty">Chưa có chi tiết từng chữ (bản heuristic không có word_details).</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="portal-table" style={{ width: '100%', fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left' }}>Chữ</th>
                    <th style={{ textAlign: 'right' }}>Điểm</th>
                    <th style={{ textAlign: 'left' }}>Trạng thái</th>
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
              <h4 style={{ fontSize: 13, marginBottom: 6 }}>Lỗi âm nổi bật</h4>
              <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
                {topErrors.map((e, i) => (
                  <li key={i}>
                    <b>{e.pattern}</b> ×{e.count}
                    {Array.isArray(e.examples) && e.examples.length > 0 && (
                      <span className="portal-muted"> — vd: {e.examples.join(', ')}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {phonemes.length > 0 && (
            <p className="portal-muted" style={{ fontSize: 12, marginTop: 8 }}>
              {phonemes.length} phoneme đã đối chiếu (xem bảng điểm từng chữ là đủ cho đa số người học).
            </p>
          )}
        </div>
      )}

      {/* Nhận xét AI — panel RIÊNG, độc lập với bảng điểm. */}
      {showFeedback && (
        <div style={{ marginTop: 12 }} data-testid="ai-feedback-panel">
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Nhận xét AI</h3>
          {!feedback ? (
            <div className="portal-empty">
              {feedbackLoading ? 'AI đang đọc bảng điểm của bạn…' : 'Bấm “Nhận xét AI” để xin góp ý — AI chỉ đọc bảng điểm đã lưu, không chấm lại.'}
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
    ['Tổng quan', feedback.summary],
    ['Phát âm', feedback.pronunciation_feedback],
    ['Nhấn âm', feedback.stress_feedback],
    ['Ngữ điệu', feedback.intonation_feedback],
    ['Trôi chảy', feedback.fluency_feedback],
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
          <div style={{ fontSize: 13, fontWeight: 800 }}>Ưu tiên sửa</div>
          <ul style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {feedback.priority_errors.map((e, i) => (
              <li key={i}><b>{e.word}</b> — {e.issue}{e.advice ? ` (${e.advice})` : ''}</li>
            ))}
          </ul>
        </div>
      )}
      {Array.isArray(feedback.practice_plan) && feedback.practice_plan.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Luyện tiếp</div>
          <ol style={{ fontSize: 14, paddingLeft: 18, margin: '4px 0 0' }}>
            {feedback.practice_plan.map((step, i) => <li key={i}>{step}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}
