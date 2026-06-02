import { HiRocketLaunch, HiBriefcase, HiMicrophone, HiAcademicCap, HiGlobeAlt } from 'react-icons/hi2';

const GOALS = [
  { key: 'work', label: 'Career', desc: 'Improve English for work and professional growth', icon: HiBriefcase },
  { key: 'interview', label: 'Interview', desc: 'Prepare for job interviews in English', icon: HiMicrophone },
  { key: 'fluency', label: 'Fluency', desc: 'Speak more naturally and confidently', icon: HiRocketLaunch },
  { key: 'business', label: 'Business', desc: 'Master business English and negotiations', icon: HiGlobeAlt },
  { key: 'academic', label: 'Academic', desc: 'Prepare for studies, exams, or research', icon: HiAcademicCap },
];

export function StepLearningGoal({ form, updateField }) {
  return (
    <div>
      <div className="text-center mb-3">
        <HiRocketLaunch size={36} style={{ color: 'var(--color-accent)' }} />
        <h4 className="fw-bold mt-2 mb-1">What's your learning goal?</h4>
        <p className="text-muted small mb-0">Choose your primary reason for practicing English.</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
        {GOALS.map((goal) => {
          const Icon = goal.icon;
          const active = form.learning_goal === goal.key;
          return (
            <button
              key={goal.key}
              type="button"
              onClick={() => updateField('learning_goal', active ? '' : goal.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '14px 16px', borderRadius: 14,
                border: `2px solid ${active ? 'var(--color-accent)' : 'var(--color-border)'}`,
                background: active ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
                cursor: 'pointer', transition: 'all 0.15s',
                textAlign: 'left', width: '100%', fontFamily: 'inherit',
              }}
            >
              <div style={{
                width: 40, height: 40, borderRadius: 12,
                background: active ? 'var(--color-accent-gradient)' : 'var(--color-bg-hover)',
                color: active ? '#fff' : 'var(--color-text-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Icon size={20} />
              </div>
              <div>
                <div className="fw-bold" style={{ fontSize: '0.92rem' }}>{goal.label}</div>
                <div className="text-muted" style={{ fontSize: '0.78rem' }}>{goal.desc}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
