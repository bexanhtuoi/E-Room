import Form from 'react-bootstrap/Form';
import { HiAcademicCap } from 'react-icons/hi2';

const LEVELS = [
  { value: 'A1', label: 'A1', desc: 'Beginner', detail: 'Can understand basic phrases' },
  { value: 'A2', label: 'A2', desc: 'Elementary', detail: 'Can communicate simple tasks' },
  { value: 'B1', label: 'B1', desc: 'Intermediate', detail: 'Can handle everyday situations' },
  { value: 'B2', label: 'B2', desc: 'Upper-Intermediate', detail: 'Can discuss complex topics' },
  { value: 'C1', label: 'C1', desc: 'Advanced', detail: 'Can express ideas fluently' },
  { value: 'C2', label: 'C2', desc: 'Proficient', detail: 'Near-native proficiency' },
];

export function StepEnglishLevel({ form, updateField }) {
  return (
    <div>
      <div className="text-center mb-3">
        <HiAcademicCap size={36} style={{ color: 'var(--color-accent)' }} />
        <h4 className="fw-bold mt-2 mb-1">What's your English level?</h4>
        <p className="text-muted small mb-0">This helps us match you with the right partners. You can skip and set it later.</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
        {LEVELS.map((lvl) => (
          <button
            key={lvl.value}
            type="button"
            onClick={() => updateField('english_level', form.english_level === lvl.value ? '' : lvl.value)}
            style={{
              display: 'flex', alignItems: 'center', gap: 14,
              padding: '14px 16px',
              borderRadius: 14,
              border: `2px solid ${form.english_level === lvl.value ? 'var(--color-accent)' : 'var(--color-border)'}`,
              background: form.english_level === lvl.value ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
              cursor: 'pointer', transition: 'all 0.15s',
              textAlign: 'left', width: '100%', fontFamily: 'inherit',
            }}
          >
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: form.english_level === lvl.value ? 'var(--color-accent-gradient)' : 'var(--color-bg-hover)',
              color: form.english_level === lvl.value ? '#fff' : 'var(--color-text-muted)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 800, fontSize: '0.85rem', flexShrink: 0,
            }}>
              {lvl.label}
            </div>
            <div style={{ flex: 1 }}>
              <div className="fw-bold" style={{ fontSize: '0.92rem' }}>{lvl.desc}</div>
              <div className="text-muted" style={{ fontSize: '0.78rem' }}>{lvl.detail}</div>
            </div>
            <input
              type="radio"
              checked={form.english_level === lvl.value}
              onChange={() => updateField('english_level', lvl.value)}
              style={{ accentColor: 'var(--color-accent)' }}
            />
          </button>
        ))}
      </div>
    </div>
  );
}
