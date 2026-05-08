export function Avatar({ name = '', size = 36, src }) {
  const initials = name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  if (src) {
    return (
      <>
        <img src={src} alt={name} className="avatar-img" width={size} height={size} />
        <style>{`
          .avatar-img { border-radius: var(--radius-full); object-fit: cover; }
        `}</style>
      </>
    );
  }

  return (
    <>
      <span className="avatar-initials" style={{ width: size, height: size, fontSize: size * 0.38 }}>
        {initials || '?'}
      </span>
      <style>{`
        .avatar-initials {
          display: inline-flex; align-items: center; justify-content: center;
          border-radius: var(--radius-full);
          background: var(--color-accent-muted);
          color: var(--color-accent);
          font-weight: 600;
          user-select: none;
        }
      `}</style>
    </>
  );
}
