import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

interface StateMessageProps {
  variant: "empty" | "error" | "loading";
  title: string;
  children?: ReactNode;
  icon?: IconName;
  action?: ReactNode;
}

/** Bloque único para estados de carga, vacío y error, con el mismo lenguaje visual. */
export function StateMessage({ variant, title, children, icon, action }: StateMessageProps) {
  const role = variant === "error" ? "alert" : variant === "loading" ? "status" : undefined;
  return (
    <div className={`state state--${variant}`} role={role}>
      <span className="state__icon">
        {variant === "loading" ? <span className="spinner" aria-hidden="true" /> : <Icon name={icon ?? "plane"} size={22} />}
      </span>
      <p className="state__title">{title}</p>
      {children && <p className="state__text">{children}</p>}
      {action}
    </div>
  );
}
