import { FACE_VARIANT_COUNT, Face, avatarValue } from '../../components/common/Faces';

export function AvatarPicker({ value, name, onPick }) {
  return (
    <div>
      <div className="er-label">Avatar</div>
      <div className="avatar-grid" role="radiogroup" aria-label="Choose avatar">
        {Array.from({ length: FACE_VARIANT_COUNT }, (_, i) => {
          const selected = value === avatarValue(i);
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={selected}
              title={`Avatar ${i + 1}`}
              onClick={() => onPick(avatarValue(i))}
              className={`avatar-cell${selected ? ' is-selected' : ''}`}
            >
              <Face variant={i} name={name} size={56} />
              {selected && <span className="avatar-check" aria-hidden="true">✓</span>}
            </button>
          );
        })}
      </div>
      <p className="avatar-hint">Pick one of 6 hand-drawn avatars. Leave untouched to keep the face generated from your name.</p>
    </div>
  );
}
