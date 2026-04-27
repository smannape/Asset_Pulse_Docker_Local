// Asset Pulse — "Pulse Drop" mark.
// Inline SVG so the mark recolors with the theme accent and stays crisp at any
// size. The mark is an oil droplet outline with a pulse line that lifts into an
// upward forecast trend; the burnt-orange endpoint is the brand accent.

export function Logo({ height = 28 }: { height?: number }) {
  const w = Math.round(height); // square mark
  return (
    <span className="brand-mark" style={{ height, width: w }} aria-hidden={false}>
      <svg
        role="img"
        aria-labelledby="apMarkTitle apMarkDesc"
        viewBox="0 0 64 64"
        width={w}
        height={height}
        focusable="false"
      >
        <title id="apMarkTitle">Asset Pulse</title>
        <desc id="apMarkDesc">
          Oil droplet outline with a pulse line lifting into an upward forecast trend.
        </desc>
        <g fill="none" strokeLinecap="square" strokeLinejoin="miter">
          <path
            d="M32 6 C 22 22, 14 30, 14 40 A 18 18 0 0 0 50 40 C 50 30, 42 22, 32 6 Z"
            stroke="currentColor"
            strokeOpacity="0.85"
            strokeWidth="2.6"
          />
          <path
            d="M18 41 H24 L26.5 35 L29 47 L31.5 33 L34 43 L37 41 L41 36 L46 30"
            stroke="currentColor"
            strokeOpacity="0.7"
            strokeWidth="2"
          />
          <circle cx="46" cy="30" r="2.6" fill="var(--accent)" />
          <path d="M46 30 L50 26" stroke="var(--accent)" strokeWidth="2" />
        </g>
      </svg>
    </span>
  );
}
