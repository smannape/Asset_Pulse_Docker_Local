import type { ReactNode } from "react";
import { InfoTip } from "./InfoTip";

export function Panel({
  title,
  meta,
  info,
  children,
}: {
  title: string;
  meta?: ReactNode;
  info?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <header>
        <h2>
          {info ? (
            <InfoTip label={title} description={info} />
          ) : (
            title
          )}
        </h2>
        {meta && <span className="meta">{meta}</span>}
      </header>
      <div className="body">{children}</div>
    </section>
  );
}
