import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJson } from '../../lib/api';
import { TagBadge } from './TagBadge';

const CAREER_TAGS = {
  Technology: ['Vibe Coding', 'AI/ML', 'LLM', 'Prompt Engineering', 'DevOps', 'Web Dev', 'Python', 'JavaScript', 'Kubernetes', 'Cloud', 'Blockchain', 'Cybersecurity', 'Machine Learning', 'AI Ethics', 'Computer Vision', 'NLP'],
  Business: ['Startup', 'Management', 'Leadership', 'Remote Work', 'Sales', 'Negotiation', 'E-commerce'],
  Finance: ['Investing', 'Crypto', 'Personal Finance', 'Accounting', 'Trading'],
  Marketing: ['SEO', 'Content', 'Social Media', 'Branding', 'Analytics'],
  Healthcare: ['Medical', 'Nursing', 'Pharma', 'Wellness', 'Mental Health'],
  Education: ['Teaching', 'AI/ML', 'Prompt Engineering', 'LLM', 'Academic Writing', 'Research'],
};

const FALLBACK_TAGS = Object.values(CAREER_TAGS).flat();

export function TagSuggestions({ careerField, jobTitle, selected = [], onToggle }) {
  const [showAll, setShowAll] = useState(false);

  const suggestedTags = CAREER_TAGS[careerField] || [];
  const displayTags = showAll ? FALLBACK_TAGS : suggestedTags.slice(0, 12);

  if (suggestedTags.length === 0 && !showAll) return null;

  return (
    <div>
      <div className="text-muted fw-semibold small mb-2" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {suggestedTags.length > 0 ? `Suggested for ${careerField || 'you'}` : 'Popular tags'}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {displayTags.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => onToggle?.(tag)}
            style={{
              padding: '5px 10px', borderRadius: 99,
              background: selected.includes(tag) ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
              color: selected.includes(tag) ? '#fff' : 'var(--color-text-secondary)',
              border: selected.includes(tag) ? 'none' : '1px solid var(--color-border)',
              cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem',
              fontFamily: 'inherit', transition: 'all 0.12s',
            }}
          >
            {tag}
          </button>
        ))}
        {!showAll && suggestedTags.length > 12 && (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            style={{
              padding: '5px 10px', borderRadius: 99,
              background: 'transparent',
              color: 'var(--color-accent)',
              border: '1px dashed var(--color-accent)',
              cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem',
              fontFamily: 'inherit',
            }}
          >
            +{suggestedTags.length - 12} more
          </button>
        )}
      </div>
    </div>
  );
}
