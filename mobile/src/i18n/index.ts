// Every new screen text comes from here (owner: English only for now; other languages are added as files).
import en from './en.json';

export type TextKey = keyof typeof en;

/** The text for `key`, with `{name}` placeholders filled from `vars`. */
export function t(key: TextKey, vars?: Record<string, string | number>): string {
  return en[key].replace(/\{(\w+)\}/g, (all, name: string) => (vars && name in vars ? String(vars[name]) : all));
}
