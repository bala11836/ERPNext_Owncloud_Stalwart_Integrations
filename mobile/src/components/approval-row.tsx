import { Pressable, View } from 'react-native';

import { Icon, type IconName } from '@/components/icon';
import { T } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { type Area, type Item, ageOf } from '@/lib/approvals';
import type { PaletteColor } from '@/theme/colors';
import { useTheme } from '@/theme';

/** Each area's icon and words (status is never colour alone). */
export const AREA_LOOK: Record<Area, { icon: IconName; label: TextKey; tint: PaletteColor; color: PaletteColor }> = {
  payments: { icon: 'rupee', label: 'area.payments', tint: 'warnTint', color: 'warn' },
  purchase: { icon: 'cart', label: 'area.purchase', tint: 'infoTint', color: 'primary' },
  stores: { icon: 'store', label: 'area.stores', tint: 'surface', color: 'text' },
  hr: { icon: 'person', label: 'area.hr', tint: 'okTint', color: 'ok' },
  attendance: { icon: 'approve', label: 'area.attendance', tint: 'infoTint', color: 'primary' },
  other: { icon: 'file', label: 'area.other', tint: 'surface', color: 'muted' },
};

/** One row: the area's icon, what it is, where, how long it has waited (amber 1 day, red 2), the amount. */
export function ApprovalRow({ item, selected, onPress }: { item: Item; selected?: boolean; onPress: () => void }) {
  const t = useTheme();
  const look = AREA_LOOK[item.area];
  const age = ageOf(item.created);
  const ageLook = { new: { tint: t.c.surface, color: t.c.muted }, amber: { tint: t.c.warnTint, color: t.c.warn }, red: { tint: t.c.dangerTint, color: t.c.danger } }[age.level];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={[text(look.label), item.title, item.detail, item.amount, age.label && text('approvals.waited', { age: age.label })].filter(Boolean).join('. ')}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 24,
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 12,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: t.c.divider,
        borderLeftWidth: selected ? 5 : 0,
        borderLeftColor: t.c.primary,
        backgroundColor: selected ? t.c.infoTint : pressed ? t.c.surface : t.c.bg,
      })}>
      <View style={{ width: 44, height: 44, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: t.c[look.tint] }}>
        <Icon name={look.icon} size={t.font(24)} color={t.c[look.color]} />
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <T style={{ fontWeight: '700' }}>{item.title}</T>
        {!!item.detail && (
          <T variant="small" color="muted">
            {item.detail}
          </T>
        )}
        {!!age.label && (
          <View style={{ flexDirection: 'row', alignSelf: 'flex-start', alignItems: 'center', gap: 4, marginTop: 4, paddingHorizontal: 8, paddingVertical: 1, borderRadius: 6, backgroundColor: ageLook.tint }}>
            {age.level !== 'new' && <Icon name="pending" size={t.font(16)} color={ageLook.color} />}
            <T variant="small" style={{ color: ageLook.color, fontWeight: '700' }}>
              {age.label}
            </T>
          </View>
        )}
      </View>
      {!!item.amount && (
        <T style={{ fontWeight: '800', fontVariant: ['tabular-nums'], textAlign: 'right', flexShrink: 1, maxWidth: '40%' }}>{item.amount}</T>
      )}
    </Pressable>
  );
}
