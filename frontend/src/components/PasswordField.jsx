import { useId, useState } from 'react';
import { MIN_PASSWORD_LENGTH } from '../lib/auth';

export default function PasswordField({ label, name, newPassword = false, describedBy, invalid = false }) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const target = name === 'confirmation' ? 'confirmação de senha' : label.toLowerCase();
  return (
    <div className="modal-input-group">
      <label className="modal-label" htmlFor={id}>{label}</label>
      <div className="auth-password">
        <input
          id={id} name={name} required className="modal-input"
          type={visible ? 'text' : 'password'}
          autoComplete={newPassword ? 'new-password' : 'current-password'}
          minLength={newPassword ? MIN_PASSWORD_LENGTH : undefined}
          aria-invalid={invalid || undefined} aria-describedby={describedBy}
        />
        <button
          type="button" className="auth-password-toggle"
          onClick={() => setVisible(value => !value)}
          aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${target}`}
          aria-controls={id}
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            {visible ? 'visibility_off' : 'visibility'}
          </span>
        </button>
      </div>
    </div>
  );
}
