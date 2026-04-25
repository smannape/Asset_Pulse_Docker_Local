// Brand logo image. The uploaded artwork has a dark background, so it's
// rendered inside a contained brand block (see .brand-logo-frame in global.css)
// to read cleanly in both light and dark themes.

export function Logo({ height = 28 }: { height?: number }) {
  return (
    <span className="brand-logo-frame" style={{ height }}>
      <picture>
        <source srcSet="/asset-pulse-logo.webp" type="image/webp" />
        <img
          src="/asset-pulse-logo.jpg"
          alt="Asset Pulse — Oil & Gas Web Application"
          height={height}
          decoding="async"
          loading="eager"
        />
      </picture>
    </span>
  );
}
