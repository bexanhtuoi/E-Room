import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { HiCloudArrowUp } from 'react-icons/hi2';
import { API_BASE_URL } from '../../lib/api';
import { AvatarPicker } from './AvatarPicker';

const ACCEPT = '.jpg,.jpeg,.png,.webp';
const MAX_BYTES = 2 * 1024 * 1024;

export function AvatarPopup({ name, value, onPick, onClose }) {
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState(null);

  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch(`${API_BASE_URL}/users/me/avatar`, {
        method: 'POST', credentials: 'include', body: form,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Upload failed (${response.status})`);
      }
      return response.json();
    },
    onSuccess: (updated) => {
      onPick(updated.avatar_url);
      onClose();
    },
    onError: (err) => setError(err?.message || 'Upload failed.'),
  });

  function handleFile(file) {
    setError(null);
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError('Photo must be at most 2MB.');
      return;
    }
    setUploading(true);
    uploadMutation.mutate(file, { onSettled: () => setUploading(false) });
  }

  return (
    <div className="pf-modal" onClick={onClose}>
      <div className="pf-modal__box" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Choose avatar">
        <div className="pf-modal__head">
          <div>
            <h3>Avatar</h3>
            <p className="portal-muted">Pick a preset or drop your own photo.</p>
          </div>
          <button type="button" className="pf-modal__close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <AvatarPicker value={value} name={name} onPick={(picked) => { onPick(picked); onClose(); }} />

        <div
          className={`pf-drop${dragging ? ' is-drag' : ''}`}
          style={{ marginTop: 16 }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]); }}
          onClick={() => document.getElementById('pf-avatar-file').click()}
          role="button" tabIndex={0} aria-label="Upload avatar photo"
          onKeyDown={(e) => { if (e.key === 'Enter') document.getElementById('pf-avatar-file').click(); }}
        >
          <HiCloudArrowUp size={24} />
          <strong>{uploading ? 'Uploading…' : 'Drop a photo here or click to browse'}</strong>
          <span className="portal-muted">jpg, png or webp up to 2MB</span>
          <input
            id="pf-avatar-file" type="file" accept={ACCEPT} hidden disabled={uploading}
            onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ''; }}
          />
        </div>
        {error && <div className="er-alert er-alert--err" style={{ marginTop: 12 }}>{error}</div>}
      </div>
    </div>
  );
}
