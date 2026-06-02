import '../../styles/EmptyState.css';
export function EmptyState({ icon, title, description, action }) {
  return (
    <>
      <div className="empty-state fade-in" role="status">
        {icon && <div className="empty-state-icon">{icon}</div>}
        {title && <h3 className="empty-state-title">{title}</h3>}
        {description && <p className="empty-state-desc">{description}</p>}
        {action && <div className="empty-state-action">{action}</div>}
      </div>
      
    </>
  );
}
