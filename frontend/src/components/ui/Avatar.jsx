import '../../styles/Avatar.css';
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
        
      </>
    );
  }

  return (
    <>
      <span className="avatar-initials" style={{ width: size, height: size, fontSize: size * 0.38 }}>
        {initials || '?'}
      </span>
      
    </>
  );
}
