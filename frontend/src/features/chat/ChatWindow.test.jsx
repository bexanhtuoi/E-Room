import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ChatWindow } from './ChatWindow';

function makeChat(items) {
  return {
    items,
    loading: false,
    sending: false,
    error: '',
    send: vi.fn(),
  };
}

const base = { kind: 'ai', userId: null, sender: 'AI', time: Date.now() };

describe('ChatWindow AI thinking visibility', () => {
  it('shows thinking only while streaming', () => {
    const { rerender } = render(
      <ChatWindow
        chat={makeChat([{ ...base, id: 'ai-s1', text: 'Hel', thinkingText: 'Searching', streaming: true }])}
        visible
        onClose={() => {}}
        currentUserId={7}
      />,
    );
    expect(screen.getByText(/Thinking/)).toBeDefined();
    expect(screen.getByText('Hel')).toBeDefined();

    rerender(
      <ChatWindow
        chat={makeChat([{ ...base, id: 'ai-s1', text: 'Hello there', thinkingText: 'Searching', streaming: false }])}
        visible
        onClose={() => {}}
        currentUserId={7}
      />,
    );
    expect(screen.queryByText(/Thinking/)).toBeNull();
    expect(screen.getByText('Hello there')).toBeDefined();
  });

  it('shows quote above thinking while streaming', () => {
    const { container } = render(
      <ChatWindow
        chat={makeChat([
          { id: 101, kind: 'chat', userId: 7, sender: 'You', text: '@ai hi', time: 1 },
          { ...base, id: 'ai-s1', text: 'Hel', thinkingText: 'Searching', sourceId: 101, streaming: true, time: 2 },
        ])}
        visible
        onClose={() => {}}
        currentUserId={7}
      />,
    );
    const quote = screen.getAllByText('@ai hi')[1];
    const thinking = screen.getByText(/Thinking/);
    expect(quote.compareDocumentPosition(thinking) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(container.textContent).toMatch('Hel');
  });

  it('shows the quoted user message on finished AI answers', () => {
    render(
      <ChatWindow
        chat={makeChat([
          { id: 101, kind: 'chat', userId: 7, sender: 'You', text: '@ai hi', time: 1 },
          { ...base, id: 'ai-s1', text: 'Hello!', sourceId: 101, streaming: false, time: 2 },
        ])}
        visible
        onClose={() => {}}
        currentUserId={7}
      />,
    );
    expect(screen.getByText('Hello!')).toBeDefined();
    // Tin goc + quote trong dap an AI = 2 cho
    expect(screen.getAllByText('@ai hi')).toHaveLength(2);
  });
});
