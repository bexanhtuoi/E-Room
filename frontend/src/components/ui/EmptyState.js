export function EmptyState({ icon, title, description, action }) {
  return (
    <>
      <div className="empty-state fade-in" role="status">
        {icon && <div className="empty-state-icon">{icon}</div>}
        {title && <h3 className="empty-state-title">{title}</h3>}
        {description && <p className="empty-state-desc">{description}</p>}
        {action && <div className="empty-state-action">{action}</div>}
      </div>
      <style>{`
        .empty-state {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; text-align: center;
          padding: 48px 20px; min-height: 260px;
        }
        .empty-state-icon {
          margin-bottom: 16px; opacity: 0.4;
          color: var(--color-text-muted);
        }
        .empty-state-icon svg { width: 48px; height: 48px; }
        .empty-state-title {
          font-family: var(--font-display);
          font-size: 18px; font-weight: 600;
          color: var(--color-text-primary); margin-bottom: 4px;
        }
        .empty-state-desc {
          font-size: 14px; color: var(--color-text-secondary);
          max-width: 320px; line-height: 1.5; margin-bottom: 16px;
        }
      `}</style>
    </>
  );
}
