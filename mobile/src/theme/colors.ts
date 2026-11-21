// Sunlight-first palette (CLAUDE.md rule 13). Every text colour must reach 7:1 contrast on `bg` and
// `surface`; `pnpm test` (scripts/check-contrast.ts) fails if a change breaks that.
// Pure data, no React Native imports, so the check can run in plain Node.
export const palette = {
  bg: '#FFFFFF',
  surface: '#F1F1F1',
  border: '#1F1F1F',
  text: '#000000',
  muted: '#3A3A3A',
  primary: '#0A3D91',
  onPrimary: '#FFFFFF',
  ok: '#08551C',
  warn: '#6B3A00',
  danger: '#8F0010',
} as const;

export type PaletteColor = keyof typeof palette;

/** Colours used for text or icons; each is checked against both backgrounds. */
export const foregrounds: PaletteColor[] = ['text', 'muted', 'primary', 'ok', 'warn', 'danger'];
