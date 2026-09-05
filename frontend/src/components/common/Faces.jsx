// Local flat-style avatars — Vietnamese / Asian faces, square, no network needed.
const VARIANTS = [
  { skin: '#f0c297', hair: '#191919', style: 'longFemale', shirt: '#111111', bg: '#f4f4f4' },
  { skin: '#e9b58a', hair: '#191919', style: 'shortMale', shirt: '#374151', bg: '#efefef' },
  { skin: '#f0c297', hair: '#191919', style: 'bobFemale', shirt: '#0f766e', bg: '#f4f4f4' },
  { skin: '#dfa172', hair: '#232323', style: 'glassesMale', shirt: '#111111', bg: '#efefef' },
  { skin: '#e9b58a', hair: '#191919', style: 'bunFemale', shirt: '#7c3aed', bg: '#f4f4f4' },
  { skin: '#f0c297', hair: '#2b2b2b', style: 'sideMale', shirt: '#b45309', bg: '#efefef' },
];

function hashName(name) {
  let h = 0;
  const s = String(name || '?');
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % VARIANTS.length;
}

function HairBack({ v }) {
  if (v.style === 'longFemale') {
    return <path d="M24 40 Q22 78 30 88 L66 88 Q74 78 72 40 Q72 22 48 22 Q24 22 24 40 Z" fill={v.hair} />;
  }
  if (v.style === 'bobFemale') {
    return <path d="M26 44 Q24 68 32 72 L64 72 Q72 68 70 44 Q70 24 48 24 Q26 24 26 44 Z" fill={v.hair} />;
  }
  if (v.style === 'bunFemale') {
    return (
      <>
        <circle cx="48" cy="18" r="9" fill={v.hair} />
        <path d="M28 44 Q26 66 34 70 L62 70 Q70 66 68 44 Q68 26 48 26 Q28 26 28 44 Z" fill={v.hair} />
      </>
    );
  }
  return null;
}

function HairFront({ v }) {
  if (v.style === 'shortMale' || v.style === 'glassesMale') {
    return <path d="M29 40 Q30 26 48 26 Q66 26 67 40 Q60 32 48 33 Q36 32 29 40 Z" fill={v.hair} />;
  }
  if (v.style === 'sideMale') {
    return <path d="M29 42 Q28 26 48 26 Q67 26 67 42 L62 42 Q62 32 48 31 Q36 32 34 44 Z" fill={v.hair} />;
  }
  // female fringe
  return <path d="M29 42 Q30 28 48 28 Q66 28 67 42 Q60 34 48 35 Q36 34 29 42 Z" fill={v.hair} />;
}

export function Face({ name = '?', size = 40, variant }) {
  const v = VARIANTS[variant ?? hashName(name)];
  const eyes = v.style === 'glassesMale' ? (
    <>
      <rect x="34" y="46" width="11" height="11" fill="none" stroke="#111" strokeWidth="2" />
      <rect x="51" y="46" width="11" height="11" fill="none" stroke="#111" strokeWidth="2" />
      <line x1="45" y1="51" x2="51" y2="51" stroke="#111" strokeWidth="2" />
      <circle cx="39.5" cy="51.5" r="1.8" fill="#111" />
      <circle cx="56.5" cy="51.5" r="1.8" fill="#111" />
    </>
  ) : (
    <>
      <ellipse cx="40" cy="51" rx="2.4" ry="3" fill="#111" />
      <ellipse cx="56" cy="51" rx="2.4" ry="3" fill="#111" />
    </>
  );
  return (
    <svg width={size} height={size} viewBox="0 0 96 96" role="img" aria-label={name} style={{ display: 'block', flexShrink: 0, background: v.bg }}>
      <rect x="0" y="0" width="96" height="96" fill={v.bg} />
      <HairBack v={v} />
      <rect x="40" y="66" width="16" height="12" fill={v.skin} />
      <path d="M28 96 Q30 78 48 78 Q66 78 68 96 Z" fill={v.shirt} />
      {v.style === 'longFemale' && <path d="M44 96 L48 84 L52 96 Z" fill="#ffffff" />}
      <ellipse cx="48" cy="50" rx="19" ry="23" fill={v.skin} />
      <HairFront v={v} />
      {eyes}
      <path d="M41 63 Q48 68 55 63" fill="none" stroke="#111" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function FaceStack({ names = [], size = 30 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      {names.map((n, i) => (
        <span key={`${n}-${i}`} title={n} style={{ marginLeft: i ? -10 : 0, border: '2px solid #fff', display: 'inline-flex' }}>
          <Face name={n} size={size} />
        </span>
      ))}
    </span>
  );
}
