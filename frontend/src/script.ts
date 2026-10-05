/* 台本 (script) text: one `[说话人] 文本` per line. Blank lines and lines starting with
   ( or （ are comments. Diffing against the session keeps line identities (index, takes). */
import type { Line } from "./api";

export interface Entry {
  number: number; // 1-based line in the text
  speaker: string;
  text: string;
}

export function parseScript(source: string) {
  const entries: Entry[] = [];
  const invalid: { number: number; raw: string }[] = [];
  source.split("\n").forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("(") || line.startsWith("（")) return;
    const match = /^\[([^\]]+)\]\s*(.+)$/.exec(line);
    const speaker = match?.[1].trim();
    const text = match?.[2].trim();
    if (speaker && text) entries.push({ number: i + 1, speaker, text });
    else invalid.push({ number: i + 1, raw });
  });
  return { entries, invalid };
}

export const toScript = (lines: Line[]) => lines.map((l) => `[${l.speaker}] ${l.text}`).join("\n");

export type Row =
  | { kind: "same"; line: Line; entry: Entry }
  | { kind: "modified"; line: Line; entry: Entry }
  | { kind: "added"; entry: Entry }
  | { kind: "deleted"; line: Line };

const key = (speaker: string, text: string) => `${speaker}\u0000${text}`;

/* Character-bigram Dice similarity, with a bonus for the same speaker. */
function similarity(line: Line, entry: Entry) {
  const grams = (s: string) => {
    const set = new Map<string, number>();
    for (let i = 0; i < s.length - 1; i++) set.set(s.slice(i, i + 2), (set.get(s.slice(i, i + 2)) ?? 0) + 1);
    return set;
  };
  const a = grams(line.text);
  const b = grams(entry.text);
  let shared = 0;
  for (const [g, n] of a) shared += Math.min(n, b.get(g) ?? 0);
  const total = Math.max(1, line.text.length - 1 + entry.text.length - 1);
  const dice = line.text === entry.text ? 1 : (2 * shared) / total;
  return Math.min(1, dice + (line.speaker === entry.speaker ? 0.2 : 0));
}
const SIMILAR = 0.4;

/* Git-like diff: exact matches (LCS) are anchors; between anchors, similar lines pair up as
   modified (keeping their takes) and the rest are deleted / added. */
export function diffScript(lines: Line[], entries: Entry[]): Row[] {
  const n = lines.length;
  const m = entries.length;
  const lcs = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      lcs[i][j] = key(lines[i].speaker, lines[i].text) === key(entries[j].speaker, entries[j].text) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);

  const rows: Row[] = [];
  let gapLines: Line[] = [];
  let gapEntries: Entry[] = [];
  const flush = () => {
    rows.push(...alignGap(gapLines, gapEntries));
    gapLines = [];
    gapEntries = [];
  };
  let i = 0;
  let j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && key(lines[i].speaker, lines[i].text) === key(entries[j].speaker, entries[j].text)) {
      flush();
      rows.push({ kind: "same", line: lines[i++], entry: entries[j++] });
    } else if (j >= m || (i < n && lcs[i + 1][j] >= lcs[i][j + 1])) gapLines.push(lines[i++]);
    else gapEntries.push(entries[j++]);
  }
  flush();
  return rows;
}

/* Within a gap: edit-distance alignment where pairing similar lines is cheaper than
   deleting one and adding the other. Deletions are listed before additions. */
function alignGap(lines: Line[], entries: Entry[]): Row[] {
  if (!lines.length || !entries.length) return [...lines.map((line): Row => ({ kind: "deleted", line })), ...entries.map((entry): Row => ({ kind: "added", entry }))];
  const n = lines.length;
  const m = entries.length;
  const cost = Array.from({ length: n + 1 }, (_, i) => Float64Array.from({ length: m + 1 }, (_, j) => i + j));
  const sim = lines.map((l) => entries.map((e) => similarity(l, e)));
  for (let i = 1; i <= n; i++)
    for (let j = 1; j <= m; j++) {
      const pair = sim[i - 1][j - 1] >= SIMILAR ? cost[i - 1][j - 1] + (1 - sim[i - 1][j - 1]) : Infinity;
      cost[i][j] = Math.min(pair, cost[i - 1][j] + 1, cost[i][j - 1] + 1);
    }
  const rows: Row[] = [];
  let i = n;
  let j = m;
  while (i > 0 || j > 0) {
    const s = i > 0 && j > 0 ? sim[i - 1][j - 1] : 0;
    if (i > 0 && j > 0 && s >= SIMILAR && cost[i][j] === cost[i - 1][j - 1] + (1 - s)) rows.push({ kind: "modified", line: lines[--i], entry: entries[--j] });
    else if (j > 0 && (i === 0 || cost[i][j] === cost[i][j - 1] + 1)) rows.push({ kind: "added", entry: entries[--j] });
    else rows.push({ kind: "deleted", line: lines[--i] });
  }
  return rows.reverse();
}

/* Request body for PUT /sessions/{id}/script. */
export const scriptBody = (rows: Row[]) => ({
  lines: rows.flatMap((r) => (r.kind === "deleted" ? [] : [{ line_id: r.kind === "added" ? null : r.line.id, speaker: r.entry.speaker, text: r.entry.text }])),
});
