// Shared constants — tránh duplicate khắp codebase

export const ENGLISH_LEVELS = [
  { value: 'A1', label: 'A1', desc: 'Beginner', detail: 'Can understand basic phrases' },
  { value: 'A2', label: 'A2', desc: 'Elementary', detail: 'Can communicate simple tasks' },
  { value: 'B1', label: 'B1', desc: 'Intermediate', detail: 'Can handle everyday situations' },
  { value: 'B2', label: 'B2', desc: 'Upper-Intermediate', detail: 'Can discuss complex topics' },
  { value: 'C1', label: 'C1', desc: 'Advanced', detail: 'Can express ideas fluently' },
  { value: 'C2', label: 'C2', desc: 'Proficient', detail: 'Near-native proficiency' },
];

export const LEVEL_NAMES = {
  A1: 'Beginner', A2: 'Elementary', B1: 'Intermediate',
  B2: 'Upper-Intermediate', C1: 'Advanced', C2: 'Proficient',
};

export const LEARNING_GOALS = [
  { key: 'work', label: 'Career', desc: 'Improve English for work and professional growth', icon: 'HiBriefcase' },
  { key: 'interview', label: 'Interview', desc: 'Prepare for job interviews in English', icon: 'HiMicrophone' },
  { key: 'fluency', label: 'Fluency', desc: 'Speak more naturally and confidently', icon: 'HiRocketLaunch' },
  { key: 'business', label: 'Business', desc: 'Master business English and negotiations', icon: 'HiGlobeAlt' },
  { key: 'academic', label: 'Academic', desc: 'Prepare for studies, exams, or research', icon: 'HiAcademicCap' },
];

export const GOAL_LABELS = {
  work: '💼 Career',
  interview: '🎤 Interview',
  fluency: '🚀 Fluency',
  business: '🌍 Business',
  academic: '🎓 Academic',
};

export const CAREER_FIELDS = [
  'Technology', 'Business', 'Healthcare', 'Education',
  'Finance', 'Marketing', 'Engineering', 'Science',
  'Arts & Design', 'Law', 'Other',
];

export const TAG_COLORS = {
  technology: { bg: '#ffffff20', fg: '#ffffff' },
  business:   { bg: '#ffffff20', fg: '#ffffff' },
  science:    { bg: '#ffffff20', fg: '#ffffff' },
  creative:   { bg: '#f472b620', fg: '#f472b6' },
  lifestyle:  { bg: '#fbbf2420', fg: '#fbbf24' },
  default:    { bg: 'var(--color-accent-muted)', fg: 'var(--color-accent)' },
};

export const TIME_RANGES = ['weekly', 'monthly', 'all'];

export const ROOM_STATUS = {
  ACTIVE: { icon: 'HiPlayCircle', color: 'var(--color-success)', badge: 'success', label: 'Live' },
  IDLE:   { icon: 'HiClock', color: 'var(--color-text-muted)', badge: 'info', label: 'Waiting' },
};
