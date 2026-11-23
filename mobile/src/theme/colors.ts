// Sunlight-first palette (CLAUDE.md rule 13). Every text colour must reach 7:1 contrast on `bg` and
// `surface`; `pnpm test` (scripts/check-contrast.ts) fails if a change breaks that.
// Pure data, no React Native imports, so the check can run in plain Node.
export const palette = {
  bg: '#FFFFFF',
  surface: '#F1F1F1',
  /** Owner's reference design: grey page under white cards, card edges, light tinted strips. */
  page: '#F4F5F7',
  line: '#7A7A84', // card edges: 4.25:1 on white, visible in sunlight (UI boundaries need 3:1)
  infoTint: '#E8F0FC',
  okTint: '#E6F3EA',
  warnTint: '#FCF1DE',
  dangerTint: '#FBE8EA',
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

/** Colours used for text or icons; each is checked against every background below. */
export const foregrounds: PaletteColor[] = ['text', 'muted', 'primary', 'ok', 'warn', 'danger'];

/** Backgrounds text may sit on. */
export const backgrounds: PaletteColor[] = ['bg', 'surface', 'page', 'infoTint', 'okTint', 'warnTint', 'dangerTint'];
