import { useState } from "react";
import { authApi, type SessionResponse } from "../../api/authApi";
import { isValidEmail } from "../../lib/email";
import { isValidCode, passwordProblem } from "../../lib/password";
import { ApiError } from "../../lib/httpClient";
import { Field, FormShell, LinkButton } from "./AuthKit";
import { useCountdown, useSubmit } from "./authHooks";
import { LOGIN_INPUT_ID } from "./constants";

export type Screen = "login" | "register" | "verify" | "forgot" | "reset";

interface CommonProps {
  email: string;
  notice?: string | null;
  go: (screen: Screen, email?: string, notice?: string) => void;
}

const EMAIL_ERROR = "Escribe un correo válido.";

export function LoginForm({ email: initial, notice, go, onSession }: CommonProps & { onSession: (s: SessionResponse) => void }) {
  const [email, setEmail] = useState(initial);
  const [password, setPassword] = useState("");
  const { busy, error, setError, run } = useSubmit();

  const submit = () => {
    if (!isValidEmail(email.trim())) return setError(EMAIL_ERROR);
    if (!password) return setError("Escribe tu contraseña.");
    void run(async () => {
      try {
        onSession(await authApi.login(email.trim(), password));
      } catch (e) {
        if (e instanceof ApiError && e.code === "EMAIL_NOT_VERIFIED") {
          go("verify", email.trim(), "Aún no verificas tu correo. Te enviamos un código nuevo.");
          return;
        }
        throw e;
      }
    });
  };

  return (
    <FormShell
      title="Inicia sesión"
      intro="Entra con tu correo y contraseña para ver y crear tus itinerarios."
      notice={notice}
      error={error}
      busy={busy}
      submitLabel="Entrar"
      busyLabel="Entrando…"
      onSubmit={submit}
      footer={
        <>
          <LinkButton onClick={() => go("register", email)}>Crear una cuenta</LinkButton>
          <LinkButton onClick={() => go("forgot", email)}>Olvidé mi contraseña</LinkButton>
        </>
      }
    >
      <Field id={LOGIN_INPUT_ID} label="Correo" type="email" autoComplete="email" value={email} onChange={setEmail} disabled={busy} />
      <Field id="auth-password" label="Contraseña" type="password" autoComplete="current-password" value={password} onChange={setPassword} disabled={busy} />
    </FormShell>
  );
}

export function RegisterForm({ email: initial, go }: CommonProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState(initial);
  const [password, setPassword] = useState("");
  const { busy, error, setError, run } = useSubmit();

  const submit = () => {
    const mail = email.trim();
    if (!name.trim()) return setError("Escribe tu nombre.");
    if (!isValidEmail(mail)) return setError(EMAIL_ERROR);
    const problem = passwordProblem(password, mail);
    if (problem) return setError(problem);
    void run(async () => {
      await authApi.register(mail, name.trim(), password);
      go("verify", mail, "Te enviamos un código de 6 dígitos. Revisa tu correo (y la carpeta de spam).");
    });
  };

  return (
    <FormShell
      title="Crea tu cuenta"
      intro="Te enviaremos un código para confirmar que el correo es tuyo; ahí llegarán tus recordatorios de vuelo."
      error={error}
      busy={busy}
      submitLabel="Registrarme"
      busyLabel="Enviando código…"
      onSubmit={submit}
      footer={<LinkButton onClick={() => go("login", email)}>Ya tengo cuenta</LinkButton>}
    >
      <Field id={LOGIN_INPUT_ID} label="Nombre" autoComplete="name" value={name} onChange={setName} disabled={busy} />
      <Field id="auth-email" label="Correo" type="email" autoComplete="email" value={email} onChange={setEmail} disabled={busy} />
      <Field
        id="auth-password"
        label="Contraseña"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={setPassword}
        hint="Mínimo 10 caracteres."
        disabled={busy}
      />
    </FormShell>
  );
}

export function VerifyForm({ email, notice, go, onSession }: CommonProps & { onSession: (s: SessionResponse) => void }) {
  const [code, setCode] = useState("");
  const [resent, setResent] = useState<string | null>(null);
  const { busy, error, setError, run } = useSubmit();
  const cooldown = useCountdown(60);

  const submit = () => {
    if (!isValidCode(code)) return setError("El código tiene 6 dígitos.");
    void run(async () => onSession(await authApi.verify(email, code)));
  };
  const resend = () =>
    void run(async () => {
      await authApi.resend(email);
      cooldown.restart();
      setResent("Si el correo es correcto, te enviamos un código nuevo.");
    });

  return (
    <FormShell
      title="Verifica tu correo"
      intro={`Escribe el código de 6 dígitos que enviamos a ${email}. Vence en 10 minutos.`}
      notice={resent ?? notice}
      error={error}
      busy={busy}
      submitLabel="Verificar"
      busyLabel="Verificando…"
      onSubmit={submit}
      footer={
        <>
          <button type="button" className="link-btn" disabled={busy || cooldown.left > 0} onClick={resend}>
            {cooldown.left > 0 ? `Reenviar código (${cooldown.left} s)` : "Reenviar código"}
          </button>
          <LinkButton onClick={() => go("register", email)}>Cambiar correo</LinkButton>
        </>
      }
    >
      <Field
        id={LOGIN_INPUT_ID}
        label="Código"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        placeholder="123456"
        value={code}
        onChange={(v) => setCode(v.replace(/\D/g, ""))}
        disabled={busy}
      />
    </FormShell>
  );
}

export function ForgotForm({ email: initial, go }: CommonProps) {
  const [email, setEmail] = useState(initial);
  const { busy, error, setError, run } = useSubmit();

  const submit = () => {
    if (!isValidEmail(email.trim())) return setError(EMAIL_ERROR);
    void run(async () => {
      await authApi.forgot(email.trim());
      go("reset", email.trim(), "Si el correo tiene una cuenta, te enviamos un código para cambiar la contraseña.");
    });
  };

  return (
    <FormShell
      title="Recupera tu contraseña"
      intro="Escribe tu correo y te enviaremos un código para elegir una contraseña nueva."
      error={error}
      busy={busy}
      submitLabel="Enviar código"
      busyLabel="Enviando…"
      onSubmit={submit}
      footer={<LinkButton onClick={() => go("login", email)}>Volver a iniciar sesión</LinkButton>}
    >
      <Field id={LOGIN_INPUT_ID} label="Correo" type="email" autoComplete="email" value={email} onChange={setEmail} disabled={busy} />
    </FormShell>
  );
}

export function ResetForm({ email, notice, go }: CommonProps) {
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, setError, run } = useSubmit();

  const submit = () => {
    if (!isValidCode(code)) return setError("El código tiene 6 dígitos.");
    const problem = passwordProblem(password, email);
    if (problem) return setError(problem);
    void run(async () => {
      await authApi.reset(email, code, password);
      go("login", email, "Contraseña actualizada. Ya puedes iniciar sesión.");
    });
  };

  return (
    <FormShell
      title="Elige una contraseña nueva"
      intro={`Escribe el código que enviamos a ${email} y tu contraseña nueva.`}
      notice={notice}
      error={error}
      busy={busy}
      submitLabel="Cambiar contraseña"
      busyLabel="Guardando…"
      onSubmit={submit}
      footer={<LinkButton onClick={() => go("login", email)}>Volver a iniciar sesión</LinkButton>}
    >
      <Field
        id={LOGIN_INPUT_ID}
        label="Código"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        value={code}
        onChange={(v) => setCode(v.replace(/\D/g, ""))}
        disabled={busy}
      />
      <Field
        id="auth-password"
        label="Contraseña nueva"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={setPassword}
        hint="Mínimo 10 caracteres."
        disabled={busy}
      />
    </FormShell>
  );
}
