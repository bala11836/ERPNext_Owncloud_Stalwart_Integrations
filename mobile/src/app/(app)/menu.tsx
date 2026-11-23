import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';

import { MenuPane } from '@/components/menu-pane';
import { Button, Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { BOOT_PATH, type Boot, useErp } from '@/lib/erp';
import { useIsTablet, useTheme } from '@/theme';

// Home groups ERPNext's menus by the app they come from, so business work comes first.
// Display only: ERPNext has already decided which menus this user may see.
const GROUPS = ['Work', 'Office & chat', 'System & settings'] as const;
const WORK_APPS = new Set(['erpnext', 'hrms', 'india_compliance', 'erpnext_drive_integrations', 'razorpayx_integration', 'insights']);
const OFFICE_APPS = new Set(['raven']);
const groupOf = (app?: string) => (app && WORK_APPS.has(app) ? 'Work' : app && OFFICE_APPS.has(app) ? 'Office & chat' : 'System & settings');

/** Menu: settings, then the same role-filtered menus the signed-in user gets on the ERPNext web desk. */
export default function Menu() {
  const t = useTheme();
  const tablet = useIsTablet();
  const { data, error, loading, reload } = useErp<{ message: Boot }>(BOOT_PATH);
  const menus = data?.message.menus ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const current = selected ?? GROUPS.flatMap((g) => menus.filter((m) => groupOf(m.app) === g))[0]?.name;

  if (!data) {
    return (
      <View style={{ flex: 1, backgroundColor: t.c.bg, padding: 16, gap: 12 }}>
        {error ? (
          <>
            <Status kind="danger" label={`Couldn't load your menus. ${error}`} />
            <Button label="Try again" icon="refresh" secondary onPress={reload} />
          </>
        ) : (
          loading && <ActivityIndicator style={{ margin: 32 }} size="large" color={t.c.primary} />
        )}
      </View>
    );
  }

  const list = (
    <ScrollView style={{ backgroundColor: t.c.bg }}>
      <Row title={text('menu.settings')} subtitle={text('menu.settingsHint')} onPress={() => router.push('/settings')} />
      {menus.length === 0 && (
        <View style={{ padding: 16 }}>
          <Status kind="info" label="Your ERPNext roles don't include any menus yet. Ask the MD or CFO for access." />
        </View>
      )}
      {GROUPS.map((g) => {
        const inGroup = menus.filter((m) => groupOf(m.app) === g);
        if (!inGroup.length) return null;
        return (
          <View key={g}>
            <T variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 6, fontWeight: '700' }}>
              {g.toUpperCase()}
            </T>
            {inGroup.map((m) => {
              const count = m.items.filter((i) => i.type === 'doctype').length;
              return (
                <Row
                  key={m.name}
                  title={m.label}
                  subtitle={`${count} ${count === 1 ? 'list' : 'lists'}`}
                  selected={tablet && current === m.name}
                  onPress={() => (tablet ? setSelected(m.name) : router.push({ pathname: '/menu/[name]', params: { name: m.name } }))}
                />
              );
            })}
          </View>
        );
      })}
    </ScrollView>
  );

  if (!tablet || !current) return list;
  return (
    <View style={{ flex: 1, flexDirection: 'row', backgroundColor: t.c.bg }}>
      <View style={{ width: 360, borderRightWidth: t.border, borderRightColor: t.c.border }}>{list}</View>
      <ScrollView style={{ flex: 1 }}>
        <MenuPane name={current} />
      </ScrollView>
    </View>
  );
}
