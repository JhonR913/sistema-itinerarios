const PATHS = {
  plane: [
    "M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z",
  ],
  plus: ["M5 12h14", "M12 5v14"],
  trash: ["M3 6h18", "M8 6V4h8v2", "M6 6l1 14h10l1-14", "M10 10v6", "M14 10v6"],
  close: ["M18 6 6 18", "M6 6l12 12"],
  pause: ["M8 5v14", "M16 5v14"],
  play: ["M7 4l13 8-13 8z"],
  calendar: ["M7 3v4", "M17 3v4", "M4 9h16", "M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"],
  clock: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5l3 2"],
  logout: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "M16 17l5-5-5-5", "M21 12H9"],
  refresh: ["M21 12a9 9 0 1 1-3-6.7L21 8", "M21 3v5h-5"],
  alert: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 8v5", "M12 16.5v.5"],
  pin: ["M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z", "M12 7.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z"],
  globe: ["M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0", "M3 12h18", "M12 3a14 14 0 0 1 0 18", "M12 3a14 14 0 0 0 0 18"],
  arrow: ["M5 12h14", "M13 6l6 6-6 6"],
  user: ["M20 21a8 8 0 0 0-16 0", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  size?: number;
}

/** Iconos de línea con un único trazo; decorativos (aria-hidden). */
export function Icon({ name, size = 18 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
