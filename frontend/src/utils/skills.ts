/** All unique skill strings from categories + flat items (sorted). */
export function flattenSkillPool(categories: Record<string, string[]>, items: string[]): string[] {
  const s = new Set<string>();
  for (const x of items || []) {
    const t = String(x).trim();
    if (t) s.add(t);
  }
  for (const arr of Object.values(categories || {})) {
    if (!Array.isArray(arr)) continue;
    for (const x of arr) {
      const t = String(x).trim();
      if (t) s.add(t);
    }
  }
  return [...s].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}
