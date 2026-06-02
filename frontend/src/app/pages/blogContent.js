export const blogPosts = [
  {
    slug: '20-minute-speaking-room',
    category: 'Speaking practice',
    title: 'Turn a 20-minute English room into measurable fluency progress',
    excerpt: 'A practical room routine for learners who want every live conversation to produce one visible improvement.',
    author: 'E-Room Learning Team',
    date: 'May 20, 2026',
    readTime: '6 min read',
    hero: 'Room routine',
    content: [
      'Most learners join speaking rooms hoping that more minutes will automatically become more confidence. The better approach is to give each room one measurable job: one pronunciation pattern, one grammar habit, or one conversation behavior to improve.',
      'Before entering a room, write a short target sentence that you expect to use. During the room, use it naturally at least twice. After the room, compare what you said with the correction cards and rewrite the sentence once.',
      'The goal is not to speak perfectly for twenty minutes. The goal is to leave with one phrase you would say better tomorrow. That small loop compounds much faster than unstructured practice.',
    ],
  },
  {
    slug: 'use-ai-corrections-after-class',
    category: 'AI feedback',
    title: 'What strong learners do after receiving AI corrections',
    excerpt: 'Corrections are only useful when they become habits. Here is a simple review flow after every session.',
    author: 'E-Room Coaching Notes',
    date: 'May 18, 2026',
    readTime: '5 min read',
    hero: 'Feedback loop',
    content: [
      'A correction card is not a score. It is a map of what your next speaking attempt should sound like. Strong learners avoid reviewing every correction equally. They choose the repeated pattern first.',
      'Start by grouping corrections into vocabulary, grammar, pronunciation, and clarity. Pick the category that appears twice or more. Then write one corrected sentence and one original sentence side by side.',
      'Bring the corrected sentence into your next room. If you can use it without pausing, the correction has moved from feedback into skill.',
    ],
  },
  {
    slug: 'better-room-topics',
    category: 'Room design',
    title: 'How hosts choose topics that work for mixed English levels',
    excerpt: 'Good topics let beginners answer quickly while giving advanced speakers space to add detail.',
    author: 'E-Room Hosts',
    date: 'May 15, 2026',
    readTime: '7 min read',
    hero: 'Host guide',
    content: [
      'Mixed-level rooms fail when the topic is too abstract or too narrow. A better topic has a simple first question and a deeper second layer.',
      'For example, instead of asking “What is the future of remote work?”, start with “Do you prefer working at home or in an office?” Then invite stronger speakers to compare productivity, teamwork, and career growth.',
      'This structure keeps the room moving. Beginners can answer from personal experience, while advanced learners still get room to build arguments and use richer vocabulary.',
    ],
  },
];

export function getBlogPost(slug) {
  return blogPosts.find((post) => post.slug === slug);
}
