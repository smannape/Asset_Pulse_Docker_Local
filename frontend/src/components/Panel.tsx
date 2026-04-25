import type { ReactNode } from "react";

export function Panel({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <header>
        <h2>{title}</h2>
        {meta && <span className="meta">{meta}</span>}
      </header>
      <div className="body">{children}</div>
    </section>
  );
}
