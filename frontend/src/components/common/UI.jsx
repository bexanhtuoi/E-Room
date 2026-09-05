export function Container({ children, style }) {
  return (
    <div className="er-container" style={style}>
      {children}
    </div>
  );
}

export function Section({ id, soft, line, children, style }) {
  const cls = `er-section${soft ? ' er-section--soft' : ''}${line ? ' er-section--line' : ''}`;
  return (
    <section id={id} className={cls} style={style}>
      <Container>{children}</Container>
    </section>
  );
}

export function Eyebrow({ children }) {
  return <span className="er-eyebrow">{children}</span>;
}

export function Button({ to, href, ghost, children, onClick, type = 'button', disabled }) {
  const cls = `er-btn${ghost ? ' er-btn--ghost' : ''}`;
  if (to) return <a className={cls} href={to}>{children}</a>;
  if (href) return <a className={cls} href={href}>{children}</a>;
  return <button className={cls} type={type} onClick={onClick} disabled={disabled}>{children}</button>;
}

export function Card({ ink, children, style }) {
  return (
    <div className={`er-card${ink ? ' er-card--ink' : ''}`} style={style}>
      {children}
    </div>
  );
}

const AVATAR_COLORS = ['#111111', '#444444', '#6b7280', '#1f2937', '#374151', '#0f766e', '#7c3aed', '#b45309'];

function avatarColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

export function Avatar({ name, size = 36 }) {
  const initials = name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
  return (
    <span title={name} style={{ width: size, height: size, background: avatarColor(name), color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: size * 0.38, flexShrink: 0 }}>
      {initials}
    </span>
  );
}

export function AvatarStack({ names, size = 32 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      {names.map((n, i) => (
        <span key={n} style={{ marginLeft: i ? -10 : 0, border: '2px solid #fff', display: 'inline-flex' }}>
          <Avatar name={n} size={size} />
        </span>
      ))}
    </span>
  );
}

export function Photo({ src, name, size = 40 }) {
  return (
    <img
      src={src}
      alt={name}
      title={name}
      loading="lazy"
      width={size}
      height={size}
      style={{ width: size, height: size, objectFit: 'cover', flexShrink: 0, display: 'block', background: '#eee' }}
    />
  );
}

export function PhotoStack({ photos, size = 32 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      {photos.map((p, i) => (
        <span key={p.src} style={{ marginLeft: i ? -10 : 0, border: '2px solid #fff', display: 'inline-flex' }}>
          <Photo src={p.src} name={p.name} size={size} />
        </span>
      ))}
    </span>
  );
}

export function FaqList({ items }) {
  return (
    <div>
      {items.map((f) => (
        <details className="er-faq" key={f.q}>
          <summary>{f.q}</summary>
          <p>{f.a}</p>
        </details>
      ))}
    </div>
  );
}
