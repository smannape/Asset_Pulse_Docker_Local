import { useId, useState, type ReactNode } from "react";

// Lightweight, dependency-free tooltip. Wraps a label and shows a small
// description on hover/focus. Keyboard-accessible: the trigger is a button so
// focus surfacing the tip behaves the same as hover.
export function InfoTip({
  label,
  description,
  className,
  position = "below",
}: {
  label: ReactNode;
  description: ReactNode;
  className?: string;
  position?: "below" | "above";
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span
      className={`infotip-wrap ${className ?? ""}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="infotip-trigger"
        aria-describedby={id}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault();
          setOpen((v) => !v);
        }}
      >
        {label}
        <span className="infotip-mark" aria-hidden="true">?</span>
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className={`infotip-bubble ${position === "above" ? "above" : "below"}`}
        >
          {description}
        </span>
      )}
    </span>
  );
}
