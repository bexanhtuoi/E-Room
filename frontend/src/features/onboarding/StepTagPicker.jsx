import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { TagBadge } from '../../components/tags/TagBadge';
import { HiTag } from 'react-icons/hi2';
import '../../styles/OnboardingWizard.css';

const FALLBACK_TAGS = [
  'Business', 'Technology', 'Travel', 'Education', 'IELTS',
  'Daily Life', 'Pronunciation', 'Interview', 'Culture', 'Science',
  'Food', 'Music', 'Gaming', 'Sports', 'Movies', 'Fashion',
  'Health', 'Startup', 'Marketing', 'Finance',
];

export function StepTagPicker({ form, updateField }) {
  const [search, setSearch] = useState('');
  const [customTag, setCustomTag] = useState('');

  const { data: popularTags = [], isLoading } = useQuery({
    queryKey: ['popularTags'],
    queryFn: () => fetchJson('/tags/popular').catch(() => []),
    retry: false,
  });

  const { data: searchResults = [] } = useQuery({
    queryKey: ['tagSearch', search],
    queryFn: () => fetchJson(`/tags/search?q=${search}&limit=8`).catch(() => []),
    enabled: search.length > 1,
    retry: false,
  });

  const tags = popularTags.length > 0 ? popularTags : FALLBACK_TAGS;
  const selected = form.tagIds || [];

  function toggleTag(tag) {
    const id = typeof tag === 'string' ? tag : tag.id || tag.name || tag;
    const updated = selected.includes(id)
      ? selected.filter((t) => t !== id)
      : [...selected, id];
    updateField('tagIds', updated);
  }

  function addCustomTag() {
    const tag = customTag.trim();
    if (tag && !selected.includes(tag)) {
      updateField('tagIds', [...selected, tag]);
      setCustomTag('');
    }
  }

  return (
    <div>
      <div className="text-center mb-3">
        <HiTag size={36} className="onboarding-wizard__step-icon" />
        <h4 className="fw-bold mt-2 mb-1">What topics interest you?</h4>
        <p className="text-muted small mb-0">
          Pick at least one tag so we can match you with learners who share your interests.
        </p>
        {selected.length === 0 && (
          <p className="small mt-1 onboarding-wizard__step-warning">
            ⚠️ You can skip, but auto-matching will be unavailable until you add tags.
          </p>
        )}
      </div>

      {selected.length > 0 && (
        <div className="onboarding-wizard__selected-tags">
          {selected.map((tag) => (
            <TagBadge
              key={tag}
              label={tag}
              removable
              onRemove={() => toggleTag(tag)}
            />
          ))}
        </div>
      )}

      <div className="onboarding-wizard__search">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tags..."
          className="onboarding-wizard__search-input"
        />
        {search.length > 1 && searchResults.length > 0 && (
          <div className="onboarding-wizard__search-dropdown">
            {searchResults.map((tag) => (
              <button
                key={tag.id || tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className="onboarding-wizard__search-result"
              >
                {tag.name || tag}
                {tag.category && (
                  <span className="text-muted onboarding-wizard__tag-category">
                    {tag.category}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-4"><Spinner animation="border" size="sm" /></div>
      ) : (
        <div className="onboarding-wizard__tag-cloud">
          {tags.map((tag) => {
            const id = typeof tag === 'string' ? tag : tag.id || tag.name || tag;
            const name = typeof tag === 'string' ? tag : tag.name || tag;
            const active = selected.includes(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleTag(id)}
                className={`onboarding-wizard__tag-pill${active ? ' onboarding-wizard__tag-pill--active' : ''}`}
              >
                {name}
              </button>
            );
          })}
        </div>
      )}

      <div className="onboarding-wizard__custom-tag">
        <input
          type="text"
          value={customTag}
          onChange={(e) => setCustomTag(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustomTag(); } }}
          placeholder="Or type a custom tag..."
          className="onboarding-wizard__custom-input"
        />
        <button
          type="button"
          onClick={addCustomTag}
          disabled={!customTag.trim()}
          className={`onboarding-wizard__custom-btn${customTag.trim() ? ' onboarding-wizard__custom-btn--active' : ''}`}
        >
          + Add
        </button>
      </div>
    </div>
  );
}
