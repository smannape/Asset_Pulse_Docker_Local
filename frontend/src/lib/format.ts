export function fmtUSD(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: digits })}`;
}

export function fmtNum(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return `${(n * 100).toFixed(digits)}%`;
}

export function fmtMonths(n: number | null | undefined): string {
  if (n === null || n === undefined) return "n/a";
  if (n < 12) return `${n.toFixed(1)} mo`;
  return `${(n / 12).toFixed(1)} yr`;
}

export function pad(s: string | number, n = 12): string {
  const str = String(s);
  return str.length >= n ? str : str + " ".repeat(n - str.length);
}

export function rpad(s: string | number, n = 12): string {
  const str = String(s);
  return str.length >= n ? str : " ".repeat(n - str.length) + str;
}
