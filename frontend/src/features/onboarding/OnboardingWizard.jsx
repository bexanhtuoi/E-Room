import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchJson } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';
import { StepEnglishLevel } from './StepEnglishLevel';
import { StepTagPicker } from './StepTagPicker';
import { StepJobTitle } from './StepJobTitle';
import { StepLearningGoal } from './StepLearningGoal';
import { StepConfirm } from './StepConfirm';
import '../../styles/OnboardingWizard.css';

const STEPS = [
  { key: 'level', title: 'What is your English level?' },
  { key: 'tags', title: 'What topics interest you?' },
  { key: 'job', title: 'Tell us about your work' },
  { key: 'goal', title: 'What is your learning goal?' },
  { key: 'confirm', title: 'Ready to start!' },
];

const STEP_COMPONENTS = [StepEnglishLevel, StepTagPicker, StepJobTitle, StepLearningGoal, StepConfirm];

const STORAGE_KEY = 'eroom-onboarding-progress';

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveProgress(data) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch {}
}

export function OnboardingWizard() {
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState(() => ({
    english_level: user?.english_level || loadProgress().english_level || '',
    tagIds: loadProgress().tagIds || [],
    career_field: loadProgress().career_field || '',
    job_title: loadProgress().job_title || '',
    learning_goal: loadProgress().learning_goal || '',
  }));

  function updateField(field, value) {
    const updated = { ...form, [field]: value };
    setForm(updated);
    saveProgress(updated);
  }

  async function handleSkip() {
    // Skip chi bo qua step hien tai — van o lai onboarding cho den buoc cuoi
    if (isLast) {
      await handleFinish();
      return;
    }
    setError('');
    setStep((s) => s + 1);
  }

  async function handleFinish() {
    setSaving(true);
    setError('');
    try {
      // Luu onboarding that vao backend — AuthGuard doc field nay de cho qua
      if (user?.id) {
        const payload = { profile_completed: true };
        if (form.english_level) payload.english_level = form.english_level;
        await fetchJson(`/users/${user.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      }

      // Tags API co the chua ton tai — bo qua loi de khong chan onboarding
      if (form.tagIds.length > 0) {
        try {
          await fetchJson('/tags/bulk-add', {
            method: 'POST',
            body: JSON.stringify({ tag_ids: form.tagIds }),
          });
        } catch {}
      }

      localStorage.removeItem(STORAGE_KEY);
      setUser({ ...user, profile_completed: true, english_level: form.english_level || user?.english_level });
      navigate('/rooms', { replace: true });
    } catch (err) {
      setError(err?.message || 'Failed to save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  const CurrentStep = STEP_COMPONENTS[step];
  const isLast = step === STEPS.length - 1;
  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="er onboarding-wizard">
      <div className="onboarding-wizard__progress">
        <div className="onboarding-wizard__progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="er-container" style={{ maxWidth: 560, paddingTop: 72, paddingBottom: 72 }}>
        <div style={{ background: '#fff', border: '2px solid #111', padding: 'clamp(24px,4vw,40px)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.12em' }}>SETUP</span>
            <span style={{ fontSize: 13, color: '#666' }}>Step {step + 1} of {STEPS.length}</span>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
            {STEPS.map((s, i) => (
              <span key={s.key} style={{ flex: 1, height: 4, background: i <= step ? '#111' : '#e8e8e8' }} />
            ))}
          </div>

          <h1 style={{ fontSize: 'clamp(24px,3.4vw,32px)', letterSpacing: '-0.02em', margin: '20px 0 20px', color: '#000' }}>{STEPS[step].title}</h1>

          <CurrentStep form={form} updateField={updateField} error={error} />

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 28 }}>
            <button className="er-btn er-btn--ghost" onClick={handleSkip} disabled={saving}>Skip</button>
            {isLast ? (
              <button className="er-btn" onClick={handleFinish} disabled={saving}>
                {saving ? 'Saving…' : 'Next →'}
              </button>
            ) : (
              <button className="er-btn" onClick={() => { setError(''); setStep((s) => s + 1); }}>Next →</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
