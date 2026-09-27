import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ReadingScoreCard } from './ReadingScoreCard';

const DEMO_TEXT = 'I think this is the best thing we have done';
const DEMO_PRONUNCIATION = {
  score: 78.4, method: 'local-v2', scored_text: DEMO_TEXT,
  details: { sounds: 74.2, stress: 81.0, fluency: 83.5, completeness: 100.0 },
  report: {
    scores: { sounds: 74.2, stress: 81.0, fluency: 83.5, completeness: 100.0, overall: 78.4 },
    word_details: [
      { word: 'think', score: 58.5, status: 'pronunciation_error', expected_ipa: '/θɪŋk/' },
    ],
    top_errors: [{ pattern: '/θ/ → /s/', count: 1, examples: ['think'] }],
    warnings: [],
  },
};
const DEMO_FEEDBACK = { summary: 'Fix /θ/ in think.', error_words: [], practice_plan: [] };

describe('ReadingScoreCard', () => {
  it('hiện đúng 1 nút chấm khi chưa có điểm', () => {
    render(<ReadingScoreCard utterance={{ text: DEMO_TEXT }} onScore={vi.fn()} onFeedback={vi.fn()} />);
    expect(screen.getByTestId('reading-unscored')).toBeTruthy();
    expect(screen.getAllByText('Chấm điểm AI').length).toBeGreaterThan(0);
    expect(screen.queryByTestId('btn-rescore')).toBeNull();
  });

  it('đã chấm: tổng + 4 tiêu chí hiện, chi tiết ẩn, đủ 3 nút', () => {
    render(
      <ReadingScoreCard
        utterance={{ text: DEMO_TEXT, corrected_text: DEMO_TEXT, pronunciation: DEMO_PRONUNCIATION }}
        onScore={vi.fn()}
        onFeedback={vi.fn()}
      />,
    );
    expect(screen.getByTestId('reading-overall')).toBeTruthy();
    expect(screen.getByTestId('reading-scored-text').textContent).toBe(DEMO_TEXT);
    // Bảng + panel ẩn mặc định (gọn).
    expect(screen.queryByTestId('word-stats-table')).toBeNull();
    expect(screen.queryByTestId('ai-feedback-panel')).toBeNull();
    // 2 nút toggle + 1 nút chấm lại.
    expect(screen.getByTestId('btn-word-stats')).toBeTruthy();
    expect(screen.getByTestId('btn-ai-feedback')).toBeTruthy();
    expect(screen.getByTestId('btn-rescore').textContent).toBe('Chấm lại');
  });

  it('bấm Thống kê điểm số mới mở bảng riêng', () => {
    render(
      <ReadingScoreCard
        utterance={{ text: DEMO_TEXT, corrected_text: DEMO_TEXT, pronunciation: DEMO_PRONUNCIATION }}
        onScore={vi.fn()}
        onFeedback={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-word-stats'));
    const table = screen.getByTestId('word-stats-table');
    expect(table.textContent).toContain('think');
    expect(table.textContent).toContain('58.5');
    expect(table.textContent).toContain('/θ/ → /s/');
  });

  it('nút Nhận xét AI mở panel riêng độc lập với bảng điểm', () => {
    const onFeedback = vi.fn();
    render(
      <ReadingScoreCard
        utterance={{
          text: DEMO_TEXT,
          corrected_text: DEMO_TEXT,
          pronunciation: DEMO_PRONUNCIATION,
          feedback: DEMO_FEEDBACK,
        }}
        onScore={vi.fn()}
        onFeedback={onFeedback}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-ai-feedback'));
    expect(screen.getByTestId('ai-feedback-panel').textContent).toContain('think');
    expect(screen.queryByTestId('word-stats-table')).toBeNull();
  });

  it('nút Chấm lại gọi onScore', () => {
    const onScore = vi.fn();
    render(
      <ReadingScoreCard
        utterance={{ text: DEMO_TEXT, corrected_text: DEMO_TEXT, pronunciation: DEMO_PRONUNCIATION }}
        onScore={onScore}
        onFeedback={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-rescore'));
    expect(onScore).toHaveBeenCalledTimes(1);
  });

  it('bản heuristic hiện hướng dẫn thiếu audio thay vì thanh điểm', () => {
    render(
      <ReadingScoreCard
        utterance={{
          text: DEMO_TEXT,
          corrected_text: DEMO_TEXT,
          pronunciation: { score: 80.8, method: 'heuristic-v1', reason: 'no_audio', scored_text: DEMO_TEXT },
        }}
        onScore={vi.fn()}
        onFeedback={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('reading-overall')).toBeNull();
    expect(screen.getByTestId('reading-heuristic').textContent).toContain('thiếu audio');
  });

  it('chữ khớp lệch vẫn hiện điểm thật thay vì Không nghe rõ', () => {
    render(
      <ReadingScoreCard
        utterance={{
          text: DEMO_TEXT,
          corrected_text: DEMO_TEXT,
          pronunciation: {
            score: 62.3, method: 'local-v2', scored_text: DEMO_TEXT,
            report: {
              scores: { sounds: 60, stress: 70, fluency: 80, completeness: 100, overall: 62.3 },
              word_details: [
                { word: 'Hello', score: 32.2, status: 'misaligned', expected_ipa: '/hʌloʊ/' },
                { word: 'everyone', score: 74.1, status: 'ok', expected_ipa: '/ɛvriwʌn/' },
              ],
              top_errors: [],
              warnings: [],
            },
          },
        }}
        onScore={vi.fn()}
        onFeedback={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-word-stats'));
    const table = screen.getByTestId('word-stats-table');
    expect(table.textContent).toContain('Khớp lệch');
    expect(table.textContent).toContain('32.2');
    expect(table.textContent).not.toContain('Không nghe rõ');
  });
});
