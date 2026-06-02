import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';
import { StepEnglishLevel } from './StepEnglishLevel';
import { StepTagPicker } from './StepTagPicker';
import { StepJobTitle } from './StepJobTitle';
import { StepLearningGoal } from './StepLearningGoal';
import { StepConfirm } from './StepConfirm';

const STEPS = [
  { key: 'level', title: 'English Level', component: StepEnglishLevel },
  { key: 'tags', title: 'Interests', component: StepTagPicker },
  { key: 'job', title: 'Job Info', component: StepJobTitle },
  { key: 'goal', title: 'Learning Goal', component: StepLearningGoal },
  { key: 'confirm', title: 'Confirm', component: StepConfirm },
];

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

  const canProceed = () => {
    if (step === 0) return true; // level is skippable
    if (step === 1) return true; // tags are skippable (but auto-match disabled)
    if (step === 2) return true; // job is skippable
    if (step === 3) return true; // goal is skippable
    return true;
  };

  async function handleFinish() {
    setSaving(true);
    setError('');
    try {
      await fetchJson('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          english_level: form.english_level || null,
          career_field: form.career_field || null,
          job_title: form.job_title || null,
          learning_goal: form.learning_goal || null,
          profile_completed: true,
        }),
      });

      if (form.tagIds.length > 0) {
        await fetchJson('/tags/bulk-add', {
          method: 'POST',
          body: JSON.stringify({ tag_ids: form.tagIds }),
        });
      }

      localStorage.removeItem(STORAGE_KEY);
      setUser({ ...user, profile_completed: true, english_level: form.english_level });
      navigate('/', { replace: true });
    } catch (err) {
      setError(err?.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }

  const CurrentStep = STEPS[step].component;
  const isLast = step === STEPS.length - 1;
  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--color-bg)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Progress bar */}
      <div style={{
        position: 'fixed', top: 0, left: 0, right: 0, height: 3, zIndex: 100,
        background: 'var(--color-border)',
      }}>
        <div style={{
          height: '100%', width: `${progress}%`,
          background: 'var(--color-accent-gradient)',
          transition: 'width 0.4s ease',
        }} />
      </div>

      <Container className="py-5" style={{ maxWidth: 600, flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="text-center mb-4">
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            background: 'var(--color-accent-gradient)',
            color: '#fff', display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 12px',
            fontWeight: 800, fontFamily: 'Nunito, sans-serif',
            fontSize: '1.2rem', boxShadow: 'var(--shadow-glow)',
          }}>E</div>
          <h2 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
            {step === 0 ? 'Welcome to E-Room!' : STEPS[step].title}
          </h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.9rem' }}>
            Step {step + 1} of {STEPS.length}
          </p>
        </div>

        {/* Step content */}
        <div style={{
          flex: 1,
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 20, padding: '32px 24px',
          boxShadow: 'var(--shadow-card)',
        }}>
          <CurrentStep
            form={form}
            updateField={updateField}
            error={error}
          />
        </div>

        {/* Navigation buttons */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', marginTop: 20, gap: 12,
        }}>
          <Button
            variant="outline-secondary"
            className="rounded-pill px-4"
            onClick={() => step > 0 ? setStep(s => s - 1) : navigate('/')}
          >
            {step === 0 ? 'Skip Setup' : 'Back'}
          </Button>

          {isLast ? (
            <Button
              variant="primary"
              className="rounded-pill px-4 fw-semibold"
              onClick={handleFinish}
              disabled={saving}
              style={{ minWidth: 140 }}
            >
              {saving ? (
                <><Spinner animation="border" size="sm" className="me-2" /> Saving...</>
              ) : 'Complete Setup'}
            </Button>
          ) : (
            <Button
              variant="primary"
              className="rounded-pill px-4 fw-semibold"
              onClick={() => canProceed() && setStep(s => s + 1)}
              disabled={!canProceed()}
            >
              Continue
            </Button>
          )}
        </div>
      </Container>
    </div>
  );
}
