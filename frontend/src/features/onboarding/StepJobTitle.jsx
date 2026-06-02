import Form from 'react-bootstrap/Form';
import { HiBriefcase } from 'react-icons/hi2';

const CAREER_FIELDS = [
  'Technology', 'Business', 'Healthcare', 'Education',
  'Finance', 'Marketing', 'Engineering', 'Science',
  'Arts & Design', 'Law', 'Other',
];

export function StepJobTitle({ form, updateField }) {
  return (
    <div>
      <div className="text-center mb-3">
        <HiBriefcase size={36} style={{ color: 'var(--color-accent)' }} />
        <h4 className="fw-bold mt-2 mb-1">Tell us about your work</h4>
        <p className="text-muted small mb-0">Helps us suggest relevant conversation topics. Optional — you can skip.</p>
      </div>

      <div style={{ marginTop: 20 }}>
        <Form.Label className="fw-semibold small text-muted">Career Field</Form.Label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
          {CAREER_FIELDS.map((field) => (
            <button
              key={field}
              type="button"
              onClick={() => updateField('career_field', form.career_field === field ? '' : field)}
              style={{
                padding: '8px 16px', borderRadius: 99,
                background: form.career_field === field
                  ? 'var(--color-accent-gradient)'
                  : 'var(--color-bg-surface)',
                color: form.career_field === field ? '#fff' : 'var(--color-text-secondary)',
                border: form.career_field === field ? 'none' : '1px solid var(--color-border)',
                cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem',
                fontFamily: 'inherit', transition: 'all 0.12s',
              }}
            >
              {field}
            </button>
          ))}
        </div>

        <Form.Label className="fw-semibold small text-muted">Job Title (optional)</Form.Label>
        <Form.Control
          type="text"
          value={form.job_title}
          onChange={(e) => updateField('job_title', e.target.value)}
          placeholder="e.g. Software Engineer, Teacher..."
          className="rounded-3"
        />
      </div>
    </div>
  );
}
