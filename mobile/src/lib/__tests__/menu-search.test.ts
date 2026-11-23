import type { Boot } from '@/lib/erp';
import { searchMenus } from '@/lib/menu-search';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

const menus: Boot['menus'] = [
  {
    name: 'hr',
    label: 'Human Resources',
    app: 'hrms',
    items: [
      { type: 'section', label: 'Leaves' },
      { type: 'doctype', label: 'Leave Application', doctype: 'Leave Application' },
      { type: 'doctype', label: 'Expense Claim', doctype: 'Expense Claim' },
    ],
  },
  {
    name: 'accounts',
    label: 'Accounting',
    app: 'erpnext',
    items: [
      { type: 'doctype', label: 'Sales Invoice', doctype: 'Sales Invoice' },
      { type: 'doctype', label: 'Expense Claim', doctype: 'Expense Claim' },
    ],
  },
];

describe('menu search', () => {
  it('finds lists by every typed word, in any case', () => {
    expect(searchMenus(menus, 'leave APP').map((f) => f.doctype)).toEqual(['Leave Application']);
    expect(searchMenus(menus, 'invoice sales').map((f) => f.doctype)).toEqual(['Sales Invoice']);
    // every word must match: "human" alone would also find Leave Application
    expect(searchMenus(menus, 'claim human').map((f) => f.doctype)).toEqual(['Expense Claim']);
  });

  it("finds a menu's lists by the menu's name and lists each DocType once", () => {
    expect(searchMenus(menus, 'human').map((f) => f.doctype)).toEqual(['Leave Application', 'Expense Claim']);
    expect(searchMenus(menus, 'expense')).toEqual([{ doctype: 'Expense Claim', label: 'Expense Claim', menu: 'Human Resources' }]);
  });

  it('never returns headings, and nothing for an empty search or no match', () => {
    expect(searchMenus(menus, 'leaves').map((f) => f.doctype)).toEqual([]);
    expect(searchMenus(menus, '   ')).toEqual([]);
    expect(searchMenus(menus, 'payroll')).toEqual([]);
  });
});
