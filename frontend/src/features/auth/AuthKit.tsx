import type { FormEvent, ReactNode } from "react";
import { Icon } from "../../components/ui/Icon";

interface FieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
  placeholder?: string;
  hint?: string;
  inputMode?: "numeric" | "email" | "text";
  maxLength?: number;
  disabled?: boolean;
}

export function Field({ id, label, value, onChange, type = "text", hint, disabled, ...rest }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        className="input"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        {...rest}
      />
      {hint && <p className="muted">{hint}</p>}
    </div>
  );
}

interface ShellProps {
  title: string;
  intro: string;
  notice?: string | null;
  error: string | null;
  busy: boolean;
  submitLabel: string;
  busyLabel: string;
  onSubmit: () => void;
  children: ReactNode;
  footer?: ReactNode;
}

/** Marco común de todos los formularios de acceso. */
export function FormShell({ title, intro, notice, error, busy, submitLabel, busyLabel, onSubmit, children, footer }: ShellProps) {
  const handle = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };
  return (
    <form onSubmit={handle} className="card login" noValidate aria-labelledby="auth-title">
      <span className="login__badge" aria-hidden="true">
        <Icon name="plane" size={22} />
      </span>
      <h2 id="auth-title">{title}</h2>
      <p className="muted">{intro}</p>
      {notice && (
        <p className="alert alert--ok" role="status">
          <Icon name="clock" size={16} /> <span>{notice}</span>
        </p>
      )}
      {children}
      {error && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> {error}
        </p>
      )}
      <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
        {busy ? (
          <>
            <span className="spinner spinner--sm" aria-hidden="true" /> {busyLabel}
          </>
        ) : (
          submitLabel
        )}
      </button>
      {footer && <div className="auth__links">{footer}</div>}
    </form>
  );
}

export function LinkButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button type="button" className="link-btn" onClick={onClick}>
      {children}
    </button>
  );
}
