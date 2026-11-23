import type { Boot } from '@/lib/erp';

export type Found = { doctype: string; label: string; menu: string };

/**
 * Menu search: the lists (DocTypes) in the person's own role menus whose name, or whose menu's name, contains
 * every word typed. Each DocType once, in menu order. Display only: ERPNext decided which menus the person has.
 */
export function searchMenus(menus: Boot['menus'], query: string): Found[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const seen = new Set<string>();
  const found: Found[] = [];
  for (const menu of menus) {
    for (const item of menu.items) {
      if (item.type !== 'doctype' || seen.has(item.doctype)) continue;
      const text = `${item.label} ${item.doctype} ${menu.label}`.toLowerCase();
      if (words.every((w) => text.includes(w))) {
        seen.add(item.doctype);
        found.push({ doctype: item.doctype, label: item.label, menu: menu.label });
      }
    }
  }
  return found;
}
