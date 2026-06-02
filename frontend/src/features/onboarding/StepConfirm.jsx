import { HiCheckCircle } from 'react-icons/hi2';
import { TagBadge } from '../../components/tags/TagBadge';

const ENGLISH_LEVELS = {
  A1: 'Beginner', A2: 'Elementary', B1: 'Intermediate',
  B2: 'Upper-Intermediate', C1: 'Advanced', C2: 'Proficient',
};

const GOAL_LABELS = {
  work: '💼 Career', interview: '🎤 Interview', fluency: '🚀 Fluency',
  business: '🌍 Business', academic: '🎓 Academic',
};

export function StepConfirm({ form, updateField, error }) {
  const fields = [
    { label: 'English Level', value: form.english_level ? `${form.english_level} — ${ENGLISH_LEVELS[form.english_level] || form.english_level}` : 'Not set (can be set later)', key: 'level' },
    { label: 'Career Field', value: form.career_field || 'Not set', key: 'career' },
    { label: 'Job Title', value: form.job_title || 'Not set', key: 'job' },
    { label: 'Learning Goal', value: GOAL_LABELS[form.learning_goal] || form.learning_goal || 'Not set', key: 'goal' },
  ];

  return (
    <div>
      <div className="text-center mb-3">
        <HiCheckCircle size={36} style={{ color: 'var(--color-success)' }} />
        <h4 className="fw-bold mt-2 mb-1">Ready to start!</h4>
        <p className="text-muted small mb-0">Review your selections before we finish setting up.</p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px', borderRadius: 12, marginBottom: 16,
          background: 'var(--color-danger-muted)',
          color: 'var(--color-danger)', fontSize: '0.85rem', fontWeight: 600,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Tags */}
      {form.tagIds.length > 0 && (
        <div style={{
          padding: '14px', borderRadius: 12,
          background: 'var(--color-accent-muted)', marginBottom: 16,
        }}>
          <div className="fw-bold small text-muted mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Your Interests ({form.tagIds.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {form.tagIds.map((tag) => (
              <TagBadge key={tag} label={tag} />
            ))}
          </div>
        </div>
      )}

      {/* Other fields */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {fields.map((f) => (
          <div key={f.key} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '10px 14px', borderRadius: 12,
            background: 'var(--color-bg-surface)',
          }}>
            <span className="text-muted small fw-semibold">{f.label}</span>
            <span className="fw-semibold" style={{ fontSize: '0.88rem' }}>{f.value}</span>
          </div>
        ))}
      </div>

      {form.tagIds.length === 0 && (
        <div style={{
          marginTop: 16, padding: '10px 14px', borderRadius: 12,
          background: 'var(--color-warning-muted)',
          color: 'var(--color-warning)', fontSize: '0.82rem',
        }}>
          ⚠️ You haven't selected any tags. Auto-matching will be disabled. You can always add tags later in Settings.
        </div>
      )}
    </div>
  );
}
