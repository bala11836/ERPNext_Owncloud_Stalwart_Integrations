import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView } from 'react-native';

import { MenuPane } from '@/components/menu-pane';
import { BOOT_PATH, type Boot, useErp } from '@/lib/erp';

export default function MenuScreen() {
  const { name } = useLocalSearchParams<{ name: string }>();
  const { data } = useErp<{ message: Boot }>(BOOT_PATH);
  const label = data?.message.menus.find((m) => m.name === name)?.label ?? name;
  return (
    <ScrollView>
      <Stack.Screen options={{ title: label }} />
      <MenuPane name={name} />
    </ScrollView>
  );
}
