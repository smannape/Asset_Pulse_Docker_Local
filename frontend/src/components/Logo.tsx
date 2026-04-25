// Inline SVG mark — derrick silhouette + bracket frame.
// currentColor lets light/dark themes inherit.

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-label="Asset Pulse logo"
    >
      {/* outer bracket frame */}
      <path d="M2 4 L2 28 L6 28" strokeLinecap="square" />
      <path d="M30 4 L30 28 L26 28" strokeLinecap="square" />
      {/* derrick triangle */}
      <path d="M9 26 L16 6 L23 26 Z" strokeLinejoin="miter" />
      {/* cross brace */}
      <path d="M11 21 L21 21" />
      {/* flame dot */}
      <circle cx="16" cy="14" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}
