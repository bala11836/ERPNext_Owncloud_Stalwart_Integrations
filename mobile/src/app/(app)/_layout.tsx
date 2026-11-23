import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import { Tabs } from 'expo-router';

import type { IconName } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { useSideRail, useTheme } from '@/theme';

/** Owner decision 2: Today · Inbox · My HR · Menu. Phones: bottom tabs; 600 dp and wider: a side rail. */
export default function AppTabs() {
  const t = useTheme();
  const rail = useSideRail();
  const tab = (label: TextKey, icon: IconName) => ({
    title: text(label),
    tabBarIcon: ({ focused }: { focused: boolean }) => (
      <MaterialCommunityIcons name={icon} size={t.font(28)} color={focused ? t.c.primary : t.c.muted} />
    ),
  });
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: t.c.bg },
        headerTintColor: t.c.text,
        headerTitleStyle: { fontSize: t.font(22), fontWeight: '700' },
        tabBarPosition: rail ? 'left' : 'bottom',
        tabBarVariant: rail ? 'material' : 'uikit',
        tabBarActiveTintColor: t.c.primary,
        tabBarInactiveTintColor: t.c.muted,
        // Selected tab gets a shaded block too, so it is not shown by colour alone.
        tabBarActiveBackgroundColor: t.c.surface,
        tabBarLabelStyle: { fontSize: t.font(15), fontWeight: '700' },
        tabBarItemStyle: { minHeight: t.touch },
        tabBarStyle: rail
          ? { backgroundColor: t.c.bg, borderRightWidth: t.border, borderRightColor: t.c.border }
          : { backgroundColor: t.c.bg, borderTopWidth: t.border, borderTopColor: t.c.border },
        sceneStyle: { backgroundColor: t.c.bg },
      }}>
      <Tabs.Screen name="index" options={tab('tab.today', 'calendar-today')} />
      <Tabs.Screen name="inbox" options={tab('tab.inbox', 'inbox-outline')} />
      <Tabs.Screen name="my-hr" options={tab('tab.myHr', 'account-circle-outline')} />
      <Tabs.Screen name="menu" options={tab('tab.menu', 'menu')} />
    </Tabs>
  );
}
