export const SITE = {
  name: 'E-Room',
  tagline: 'Speak English, Connect Globally.',
  email: 'hello@e-room.app',
  supportEmail: 'support@e-room.app',
  hotline: '+84 28 7300 4688',
  hotlineHours: 'Mon–Sat, 8:00–20:00 (GMT+7)',
  address: 'Tầng 8, Tòa nhà Sao Mai, 19 Lê Thánh Tôn, Quận 1, TP. Hồ Chí Minh, Việt Nam',
  socials: [
    { label: 'Facebook', href: 'https://facebook.com/eroom.app' },
    { label: 'YouTube', href: 'https://youtube.com/@eroom-app' },
    { label: 'TikTok', href: 'https://tiktok.com/@eroom.app' },
  ],
};

export const HERO_STATS = [
  { value: '50K+', label: 'Active learners' },
  { value: '120+', label: 'Countries' },
  { value: '15K+', label: 'Rooms hosted' },
  { value: '4.8/5', label: 'Learner rating' },
];

export const MOCK_PARTICIPANTS = [
  { name: 'Linh Nguyen', level: 'B1', speaking: true, mic: true, lang: 'EN • VI' },
  { name: 'Carlos Mendez', level: 'B2', speaking: false, mic: true, lang: 'EN • ES' },
  { name: 'Yuki Tanaka', level: 'A2', speaking: false, mic: false, lang: 'EN • JA' },
  { name: 'AI Coach', level: 'AI', speaking: true, mic: true, lang: 'Feedback live' },
];

export const MOCK_TRANSCRIPTS = [
  { speaker: 'Linh', text: 'I want to practice my job interview next week.' },
  { speaker: 'AI Coach', text: 'Great. Start with a 30-second self introduction.' },
  { speaker: 'Carlos', text: 'I usually freeze in the first minute. Any tips?' },
];

export const FEATURES = [
  { title: 'Topic rooms, not classrooms', desc: 'Video rooms built around hot topics — AI agents, art, startups, cinema. You join to talk, not to study.', points: ['Fresh topics every week', 'Max 4 people per room', 'Host controls and timer'] },
  { title: 'AI meeting companion', desc: 'An AI sits in every room: it transcribes, answers @ai questions and restarts quiet moments.', points: ['Mention @ai for answers', 'Heartbeat questions', 'Examples on demand'] },
  { title: 'Live transcript', desc: 'Every voice becomes readable text in real time, separated per speaker. Never lose the thread again.', points: ['Per-speaker transcript', 'Confidence badge', 'Searchable history'] },
  { title: 'Smart recaps', desc: 'After each room you get a recap: key points, new words and your personal highlights.', points: ['Auto meeting summary', 'Vocabulary you actually used', 'Downloadable notes'] },
  { title: 'Small rooms, real talk time', desc: 'Four seats max means everyone speaks. No silent audiences, no 50-person webinars.', points: ['Live seat counter', 'Turn-taking rules', 'Hand raise + reactions'] },
  { title: 'Open global community', desc: 'Moderated rooms, verified hosts and clear room rules keep every conversation focused.', points: ['Verified hosts', 'Room rules', 'Report and block'] },
];

export const HOW_STEPS = [
  { num: '01', title: 'Pick a topic you care about', desc: 'Browse rooms by topic — AI agents, art, startups, cinema — and see who is already inside before joining.' },
  { num: '02', title: 'Join a 4-seat video room', desc: 'Turn on mic and camera. The room runs warm-up → discussion → wrap-up with a visible timer.' },
  { num: '03', title: 'Talk — AI keeps it flowing', desc: 'Mention @ai for facts, examples or follow-up questions. If the room goes quiet, AI drops a warm-up question.' },
  { num: '04', title: 'Leave with a recap', desc: 'Transcripts, highlights and new words land in your session history. Skim it, then join the next room.' },
];

export const STATUS_LABEL = { active: 'Live now', idle: 'Open', ended: 'Ended' };

export const TESTIMONIALS = [
  { quote: 'We argued about AI agents for 30 minutes straight. I forgot I was even practicing English.', name: 'Linh Nguyen', role: 'Hanoi • AI Agents room', face: 0 },
  { quote: 'The @ai answers are scary fast. Someone asks, AI drops examples, conversation keeps rolling.', name: 'Carlos Mendez', role: 'Mexico City • Startups room', face: 1 },
  { quote: 'I joined for the art talk and stayed for the people. The transcript lets me re-read everything after.', name: 'Yuki Tanaka', role: 'Osaka • Digital Art room', face: 2 },
  { quote: 'As a host, the timer plus transcript keeps the room focused. No one stays silent for long.', name: 'Sarah Johnson', role: 'Host • London', face: 4 },
  { quote: 'Four seats max is the magic. Everyone talks, nobody hides behind a muted mic.', name: 'Minh Tran', role: 'Da Nang • Tech News room', face: 5 },
  { quote: 'My recap after each room is gold — key points plus the words I actually used.', name: 'Anna Le', role: 'Hanoi • Cinema room', face: 3 },
];

export const FAQS = [
  { q: 'What is E-Room exactly?', a: 'Topic-based video meetings for up to 4 people, with an AI companion inside every room. You join to talk about things you care about — AI handles transcripts, answers and recaps.' },
  { q: 'How does a live room work?', a: 'Each room has one topic and a visible timer. You talk, AI transcribes every voice separately into one shared chat. Mention @ai anytime for facts, examples or follow-up questions.' },
  { q: 'Do I need good English to join?', a: 'No. Rooms are conversations, not exams. Speak at your level — the transcript and recap help you follow along and pick up words naturally.' },
  { q: 'What does the AI do in the room?', a: 'Two jobs only: answer @ai mentions with examples, and restart quiet rooms with warm-up questions. Detailed feedback lives in your session history, not in the chat.' },
  { q: 'Is there a free plan?', a: 'Yes. Starter is free forever: join public rooms, get live transcripts and recaps. Pro unlocks unlimited rooms, full history and private rooms.' },
  { q: 'Which devices are supported?', a: 'Any modern Chrome, Edge or Safari on laptop, tablet or phone. We recommend headphones and a quiet room for the best transcript accuracy.' },
];

export const PLANS = [
  { key: 'free', name: 'Starter', price: '$0', period: 'forever', note: 'Join real rooms and feel the format.', cta: 'Start for free', features: ['Join 5 public rooms / week', 'Live transcripts', 'Meeting recaps', 'Community leaderboard'] },
  { key: 'pro', name: 'Pro', price: '$9.99', period: '/month', note: 'For people who meet every week.', badge: 'Most popular', cta: 'Choose Pro', features: ['Unlimited rooms', 'Full recaps + notes history', 'Priority matching', 'Create private rooms', 'Longer room timers'] },
  { key: 'pro_plus', name: 'Pro+', price: '$19.99', period: '/month', note: 'For hosts, clubs and teams.', badge: 'Full access', cta: 'Choose Pro+', features: ['Everything in Pro', 'Voice playback of recaps', 'Smarter @ai answers', 'Up to 4 seats + guest invites', 'Team analytics'] },
];

export const BILLING_FAQS = [
  { q: 'Can I cancel anytime?', a: 'Yes. Monthly plans cancel in one click and stay active until the end of the billing cycle. Your transcripts and history are kept.' },
  { q: 'Is there a yearly discount?', a: 'Yes, yearly billing saves 20% on Pro and Pro+. Contact support@e-room.app to switch.' },
  { q: 'What payment methods are supported?', a: 'Visa, Mastercard, Amex and MoMo for Vietnam. Invoices are emailed after every charge.' },
];

export const BLOG_POSTS = [
  { slug: 'stop-translating-start-speaking', category: 'Method', title: 'Stop translating in your head: a 20-minute room routine', excerpt: 'A warm-up, discussion and wrap-up flow that forces English-first thinking.', author: 'Hana Pham', date: 'Aug 20, 2026', readTime: '8 min read', body: ['Many learners translate from their mother tongue → English before speaking. That adds two seconds of delay to every sentence — enough to lose your turn in a fast room.', 'Try this room routine: 3-minute warm-up (introduce yourself without notes), 12-minute discussion (one opinion + one concrete example each turn), 5-minute wrap-up (repeat your single best sentence slowly).', 'Read your transcript after the room. Circle every pause filler — “uh”, “you know”, long silences — and re-speak those exact sentences once, out loud.', 'Do this routine three times a week. Most learners cut filler words by half within a month, because the transcript makes hesitation visible.', 'Bonus: ask @ai in the room for three follow-up questions on your topic, then answer each in under 45 seconds.'] },
  { slug: 'th-vs-d-pronunciation-drill', category: 'Pronunciation', title: 'Master /θ/ vs /ð/: think, this, through', excerpt: 'Tongue placement, minimal pairs and a 5-minute daily drill.', author: 'David Cole', date: 'Aug 12, 2026', readTime: '6 min read', body: ['Put your tongue lightly between your teeth. Blow air for /θ/ (think), then add voice for /ð/ (this). If your tongue stays behind your teeth, you will produce /s/ or /z/ instead.', 'Drill in minimal pairs: think–sink, three–tree, they–day, those–doze. Say each pair 10 times, exaggerating the tongue position first, then at natural speed.', 'Record yourself and compare with the voice playback in your session recap. Aim for a word score above 85 before moving on.', 'Try it live in any open room — your session recap highlights the exact words that dropped below 70.', 'Common trap: the word “clothes” (/kloʊðz/). Practice it alone: cloth → clothe → clothes, adding one sound at a time.'] },
  { slug: 'answer-tell-me-about-yourself', category: 'Interview', title: 'How to answer “Tell me about yourself” in 60 seconds', excerpt: 'Present–past–future formula with copy-paste examples for engineers and marketers.', author: 'Sarah Johnson', date: 'Aug 02, 2026', readTime: '9 min read', body: ['Formula that never fails: present role + one measurable win, past experience in one line, future goal linked to this exact job. Sixty seconds, no life story.', 'Engineer example: “I am a QA engineer. Last year I cut regression time 40% with automated suites. I want to bring that discipline to your fintech team.”', 'Marketer example: “I run content for a SaaS blog. Organic signups tripled in six months. I want to do the same for your academy.”', 'Avoid: reciting your CV, apologizing for English, or ending with “that is all”. End with a forward line: “Happy to go deeper on any part.”', 'Practice in any open room and ask @ai for brutal follow-up questions: gaps, salary, weaknesses. If you survive the room, the real interview feels easy.'] },
  { slug: 'host-first-room-checklist', category: 'Hosting', title: 'Host your first room without awkward silence', excerpt: 'Timer, rules and 10 warm-up questions that always work.', author: 'E-Room Team', date: 'Jul 25, 2026', readTime: '5 min read', body: ['Set a visible 20-minute timer and state 3 rules up front: one mic at a time, 60 seconds per turn, English only. Rules remove 90% of awkwardness.', 'Warm-ups that always work: What did you eat today? One win this week? Teach us one word from your job. Who had the longest commute?', 'When silence hits 10 seconds, do not lecture — ask the quietest member a yes/no question first, then an open one.', 'End with a wrap-up round: each member repeats their single best sentence of the day. Close on time; rooms that end on time get returning members.', 'Hosts with 4.5+ ratings get priority placement on the Rooms page. Consistency beats charisma.'] },
  { slug: 'shadowing-with-transcripts', category: 'Method', title: 'Shadowing with your own transcripts: the 15-minute fluency loop', excerpt: 'Read, listen, repeat — using yesterday’s room as today’s textbook.', author: 'Hana Pham', date: 'Jul 18, 2026', readTime: '6 min read', body: ['Shadowing means speaking along with a recording, half a second behind it. Most people shadow natives; shadowing your own transcript is more powerful because the mistakes are yours.', 'Open yesterday’s session, pick the 60 seconds with the lowest fluency score, play the TTS version, and shadow it 5 times. Focus on rhythm, not speed.', 'On rep 6, record yourself without the model. Compare the two waveforms and word scores side by side in the session detail page.', 'Fifteen minutes a day beats a 2-hour weekend cram. Streaks are tracked on your profile — protect them.'] },
  { slug: 'small-talk-business-english', category: 'Business', title: 'Small talk that opens business meetings: 12 safe openers', excerpt: 'Weather is boring. These openers start real conversations in 30 seconds.', author: 'Sarah Johnson', date: 'Jul 08, 2026', readTime: '5 min read', body: ['Good small talk is specific, short and hands the mic back. Formula: observation + question. “I saw your team shipped the mobile app — how did launch week go?”', 'Twelve safe openers: weekend project, commute story, lunch spot, industry news, a shared tool, travel plans, hobby, book, sport, office ritual, weather-plus (“this rain — did it flood your street?”), and the agenda itself.', 'Avoid salary, politics and religion. If the other person gives a one-word answer twice, switch to the agenda gracefully.', 'Practice in any open room: open with 30 seconds of small talk before the topic. Warm openers get more replies than perfect grammar.'] },
  { slug: 'fluency-score-explained', category: 'AI feedback', title: 'How your fluency score is computed (and how to raise it)', excerpt: 'Pace, pauses, fillers and repair — the four inputs behind the number.', author: 'E-Room Team', date: 'Jun 30, 2026', readTime: '7 min read', body: ['Your fluency score blends four signals: speech pace (target 130–160 words/min), pause ratio, filler frequency, and self-repair rate (restarting sentences).', 'The fastest win is filler control. One “uh” per 30 seconds costs roughly 6 points. Replace fillers with silent pauses — silence scores better than noise.', 'Second win: finish sentences. Trailing off (“so I went to the… yeah”) hurts more than a grammar slip. Land the sentence, then correct it next turn.', 'Scores below 70 trigger extra practice tips in your recap. Hold above 85 for three rooms straight and hosts will invite you to tougher topics.'] },
  { slug: 'weekend-speaking-plan', category: 'Study plan', title: 'A weekend speaking plan: 3 rooms, 90 minutes, visible progress', excerpt: 'Friday prep, Saturday rooms, Sunday review — a repeatable weekly loop.', author: 'David Cole', date: 'Jun 21, 2026', readTime: '6 min read', body: ['Friday (15 min): pick one topic and write 5 target sentences. Save them in Notes. One topic only — depth beats breadth.', 'Saturday (60 min): join 3 rooms — one easy topic for warmth, one hard topic for pressure, one small room for precision.', 'Sunday (15 min): review transcripts, copy your 3 best moments into Notes, and re-say the weakest 60 seconds five times.', 'Repeat 4 weekends and compare week-1 vs week-4 recaps. Most consistent members gain 8–12 fluency points.'] },
];
