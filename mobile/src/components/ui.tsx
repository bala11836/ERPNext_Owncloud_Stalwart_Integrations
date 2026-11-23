import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import type { ComponentProps, ReactNode } from 'react';
import { Pressable, ScrollView, Text, TextInput, View, type TextProps } from 'react-native';

import { t as text } from '@/i18n';
import type { PaletteColor } from '@/theme/colors';
import { useTheme } from '@/theme';

export type IconName = ComponentProps<typeof MaterialCommunityIcons>['name'];

const SIZES = { small: 16, body: 18, title: 24 } as const;

/** Text. Minimum 16 pt so it stays readable in sunlight; bolder in Outdoor mode. */
export function T({
  variant = 'body',
  color = 'text',
  style,
  ...rest
}: TextProps & { variant?: keyof typeof SIZES; color?: PaletteColor }) {
  const t = useTheme();
  return (
    <Text
      {...rest}
      style={[
        {
          color: t.c[color],
          fontSize: t.font(SIZES[variant]),
          fontWeight: variant === 'title' || t.outdoor ? '700' : '500',
        },
        style,
      ]}
    />
  );
}

/** A labelled text box (several lines), large text and a visible border. */
export function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (text: string) => void }) {
  const t = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <T style={{ fontWeight: '700' }}>{label}</T>
      <TextInput
        value={value}
        onChangeText={onChange}
        accessibilityLabel={label}
        multiline
        style={{
          minHeight: t.touch * 2,
          padding: 12,
          borderWidth: t.border,
          borderColor: t.c.border,
          borderRadius: 10,
          color: t.c.text,
          fontSize: t.font(18),
          textAlignVertical: 'top',
        }}
      />
    </View>
  );
}

/** One choice of several (Present / Absent, Operating / Standby): selected is shown by a tick and a thick border. */
export function Choice({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={{
        minHeight: t.touch,
        justifyContent: 'center',
        paddingHorizontal: 16,
        borderRadius: 10,
        borderWidth: selected ? 4 : t.border,
        borderColor: selected ? t.c.primary : t.c.border,
      }}>
      <T style={{ fontWeight: selected ? '700' : '500' }}>{`${selected ? '✓ ' : ''}${label}`}</T>
    </Pressable>
  );
}

/** A search box: large text, a 48 dp+ target, a visible border (not colour alone) and a clear button. */
export function SearchField({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (text: string) => void;
  label: string;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        minHeight: t.touch,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        margin: 16,
        paddingHorizontal: 12,
        borderWidth: t.border,
        borderColor: t.c.border,
        borderRadius: 10,
        backgroundColor: t.c.bg,
      }}>
      <MaterialCommunityIcons name="magnify" size={t.font(24)} color={t.c.text} />
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={label}
        placeholderTextColor={t.c.muted}
        accessibilityLabel={label}
        autoCorrect={false}
        autoCapitalize="none"
        returnKeyType="search"
        style={{ flex: 1, minHeight: t.touch, color: t.c.text, fontSize: t.font(18) }}
      />
      {value ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={text('search.clear')}
          onPress={() => onChange('')}
          hitSlop={12}
          style={{ minWidth: t.touch, minHeight: t.touch, alignItems: 'center', justifyContent: 'center' }}>
          <MaterialCommunityIcons name="close-circle" size={t.font(24)} color={t.c.text} />
        </Pressable>
      ) : null}
    </View>
  );
}

export function Button({
  label,
  onPress,
  icon,
  secondary,
  disabled,
}: {
  label: string;
  onPress: () => void;
  icon?: IconName;
  secondary?: boolean;
  /** While an action is being sent: the button cannot be pressed again. */
  disabled?: boolean;
}) {
  const t = useTheme();
  const fg = secondary ? t.c.primary : t.c.onPrimary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => ({
        minHeight: t.touch + 8,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        paddingHorizontal: 20,
        borderRadius: 10,
        borderWidth: t.border,
        borderColor: t.c.primary,
        backgroundColor: secondary ? t.c.bg : t.c.primary,
        opacity: pressed && !disabled ? 0.75 : 1, // no dimming: text keeps its 7:1 contrast
      })}>
      {icon && <MaterialCommunityIcons name={icon} size={t.font(24)} color={fg} />}
      <Text style={{ color: fg, fontSize: t.font(18), fontWeight: '700' }}>{label}</Text>
    </Pressable>
  );
}

// Status is always icon + text, never colour alone (rule 13).
const STATUS = {
  ok: { icon: 'check-circle', color: 'ok' },
  warn: { icon: 'alert', color: 'warn' },
  danger: { icon: 'close-octagon', color: 'danger' },
  info: { icon: 'information', color: 'primary' },
  pending: { icon: 'cloud-upload-outline', color: 'primary' },
  offline: { icon: 'cloud-off-outline', color: 'muted' },
} as const satisfies Record<string, { icon: IconName; color: PaletteColor }>;

export type StatusKind = keyof typeof STATUS;

export function Status({ kind, label }: { kind: StatusKind; label: string }) {
  const t = useTheme();
  const s = STATUS[kind];
  return (
    <View
      accessible
      accessibilityLabel={label}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        alignSelf: 'flex-start',
        paddingVertical: 6,
        paddingHorizontal: 12,
        borderRadius: 999,
        borderWidth: t.border,
        borderColor: t.c[s.color],
        backgroundColor: t.c.bg,
      }}>
      <MaterialCommunityIcons name={s.icon} size={t.font(20)} color={t.c[s.color]} />
      <T variant="small" color={s.color} style={{ fontWeight: '700' }}>
        {label}
      </T>
    </View>
  );
}

/** A progress bar (always shown with its numbers in words next to it; never the only information). */
export function Progress({ done, total, label }: { done: number; total: number; label: string }) {
  const t = useTheme();
  const share = total > 0 ? Math.min(1, done / total) : 0;
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: total, now: done }}
      style={{ height: 14, borderRadius: 7, borderWidth: t.border, borderColor: t.c.border, overflow: 'hidden' }}>
      <View style={{ width: `${share * 100}%`, height: '100%', backgroundColor: t.c.primary }} />
    </View>
  );
}

/** A Today card: icon, title and detail in words, an optional count, tappable when it leads somewhere. */
export function Card({
  icon,
  title,
  detail,
  count,
  onPress,
}: {
  icon: IconName;
  title: string;
  detail?: string;
  count?: number;
  onPress?: () => void;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole={onPress ? 'button' : undefined}
      accessibilityLabel={[title, detail].filter(Boolean).join('. ')}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 24,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
        padding: 16,
        borderWidth: t.border,
        borderColor: t.c.border,
        borderRadius: 12,
        backgroundColor: pressed ? t.c.surface : t.c.bg,
      })}>
      <MaterialCommunityIcons name={icon} size={t.font(30)} color={t.c.primary} />
      <View style={{ flex: 1, gap: 4 }}>
        <T style={{ fontWeight: '700' }}>{title}</T>
        {detail ? (
          <T variant="small" color="muted">
            {detail}
          </T>
        ) : null}
      </View>
      {count !== undefined && (
        <T variant="title" style={{ minWidth: 32, textAlign: 'right' }}>
          {count}
        </T>
      )}
      {onPress && <MaterialCommunityIcons name="chevron-right" size={t.font(28)} color={t.c.text} />}
    </Pressable>
  );
}

/** A tappable list row; `selected` (tablet split view) adds a thick left bar, not just a colour change. */
export function Row({
  title,
  subtitle,
  onPress,
  selected,
}: {
  title: string;
  subtitle?: string;
  onPress?: () => void;
  selected?: boolean;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 16,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderBottomWidth: 1,
        borderBottomColor: t.c.border,
        borderLeftWidth: selected ? 6 : 0,
        borderLeftColor: t.c.primary,
        backgroundColor: selected || pressed ? t.c.surface : t.c.bg,
      })}>
      <View style={{ flex: 1, gap: 2 }}>
        <T style={{ fontWeight: '700' }}>{title}</T>
        {subtitle && (
          <T variant="small" color="muted">
            {subtitle}
          </T>
        )}
      </View>
      {onPress && <MaterialCommunityIcons name="chevron-right" size={t.font(28)} color={t.c.text} />}
    </Pressable>
  );
}

export function Screen({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 16 }}>
      {children}
    </ScrollView>
  );
}
