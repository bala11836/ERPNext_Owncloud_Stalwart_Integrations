import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import { Tabs } from 'expo-router';

import type { IconName } from '@/components/ui';
import { useTheme } from '@/theme';

export default function AppTabs() {
  const t = useTheme();
  const tab = (title: string, icon: IconName) => ({
    title,
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
        tabBarActiveTintColor: t.c.primary,
        tabBarInactiveTintColor: t.c.muted,
        // Selected tab gets a shaded block too, so it is not shown by colour alone.
        tabBarActiveBackgroundColor: t.c.surface,
        tabBarLabelStyle: { fontSize: t.font(15), fontWeight: '700' },
        tabBarItemStyle: { minHeight: t.touch },
        tabBarStyle: { backgroundColor: t.c.bg, borderTopWidth: t.border, borderTopColor: t.c.border },
        sceneStyle: { backgroundColor: t.c.bg },
      }}>
      <Tabs.Screen name="index" options={tab('Home', 'view-grid-outline')} />
      <Tabs.Screen name="approvals" options={tab('Approvals', 'check-decagram-outline')} />
      <Tabs.Screen name="inbox" options={tab('Inbox', 'bell-outline')} />
      <Tabs.Screen name="settings" options={tab('Settings', 'cog-outline')} />
    </Tabs>
  );
}
