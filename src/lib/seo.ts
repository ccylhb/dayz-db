// Shared meta-description helpers.
// Goal: every detail page's <meta name="description"> carries concrete values,
// never a zero-information boilerplate like "<title>: stats and details."

/** Strip HTML tags, wiki-link syntax ([Target|Label] / [[Target|Label]]) and stray brackets. */
export const cl = (v: unknown): string => {
  const raw = String(v ?? "");
  // Values like "109-?" / "?-181" mark a partially-unknown range: drop the
  // placeholder plus any separator it leaves dangling ("109-? " -> "109").
  const partial = raw.includes("?");
  let s = raw
    .replace(/<[^>]*>/g, "")
    .replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1")
    .replace(/\[[^\]|]*\|([^\]]*)\]/g, "$1")
    .replace(/\[\[([^\]]*)\]\]/g, "$1")
    .replace(/[[\]]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (partial) {
    s = s.replace(/\?+/g, "").replace(/^[-–—\s,]+|[-–—\s,]+$/g, "").trim();
  }
  return s.replace(/^(?:none|n\/a|-|unknown)$/i, "");
};

/** First non-empty cleaned value among candidates. */
export const pick = (...vals: unknown[]): string => {
  for (const v of vals) {
    const s = cl(v);
    if (s) return s;
  }
  return "";
};

const isText = (p: unknown): p is string => typeof p === "string" && p.trim().length > 0;

/** Hard-clip to Google's ~158-char snippet budget, never cutting mid-word. */
export const clip = (s: string, n = 158): string => {
  const t = String(s ?? "")
    .replace(/\s+/g, " ")
    .replace(/\s+([.,;:!?])/g, "$1")
    .trim();
  if (t.length <= n) return t;
  return t.slice(0, n - 1).replace(/[\s,;:—–-]+$/, "") + "\u2026";
};

/**
 * Join description fragments. Only string fragments are kept, so callers can
 * write `cond && "…"` inline — a falsy condition simply contributes nothing.
 */
export const desc = (...parts: unknown[]): string =>
  clip(
    parts
      .filter(isText)
      .join(" ")
      .replace(/\s+/g, " ")
      .replace(/\s+\./g, ".")
  );

/**
 * Render a comma-separated stat run that always ends with a period, so the
 * trailing topic sentence starts a clean new sentence:
 *   stats("HP 54", "weight 1.2") -> "HP 54, weight 1.2."
 */
export const stats = (...parts: unknown[]): string => {
  const kept = parts.filter(isText) as string[];
  if (!kept.length) return "";
  return kept.join(", ").replace(/[\s,;:]+$/, "") + ".";
};

/** A short natural sentence from the scraped intro, used as description text. */
export const introSentence = (intro: unknown, n = 150): string => {
  const s = cl(intro);
  if (!s) return "";
  const m = s.match(/^.{40,}?[.!?](?=\s|$)/);
  return clip(m ? m[0] : s, n);
};

/**
 * Use the scraped intro sentence when it is substantial enough to stand as a
 * snippet; otherwise fall back to the given topic sentence (which at least
 * names the item and its category, unlike a 12-character fragment).
 */
export const best = (intro: unknown, fallback: string, minLen = 30, n = 155): string => {
  const s = introSentence(intro, n);
  return s.length >= minLen ? s : fallback;
};
