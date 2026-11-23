import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { APP_NAME } from '@/auth/session';
import { Icon } from '@/components/icon';
import { Sheet, SheetOption } from '@/components/sheet';
import { T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type Place, type Shift, choosePlace, projectsOf } from '@/lib/places';
import { useTheme } from '@/theme';

/** The role badge from what the person is at the chosen site (server role cards replace it in step H2). */
export function roleBadge(place: Place | null): string {
  if (!place) return '';
  return [place.approver && text('role.approver'), place.supervisor && text('role.supervisor'), place.staff && text('role.staff')]
    .filter(Boolean)
    .join(' · ')
    .toUpperCase();
}

const shiftText = (s: Shift) => text('checkIn.shift', { shift: s.label ?? s.name, start: s.start, end: s.end });
const isNight = (s: Shift) => s.start > s.end || /night/i.test(s.label ?? s.name);

/**
 * Today's header (owner's reference design): app name and role badge, one-tap Outdoor mode, the Inbox bell with
 * its count; below, the project, its site (Field Site) and the shift. Sizes follow the design brief (16 pt text,
 * 48 dp targets).
 */
export function HomeHeader({
  unread,
  places,
  place,
  shift,
}: {
  unread: number;
  places: Place[];
  place: Place | null;
  shift: Shift | null;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const [picker, setPicker] = useState<'project' | 'site' | null>(null);
  const appName = APP_NAME || 'ERP';
  const badge = roleBadge(place);
  const sitesHere = place ? places.filter((p) => p.project === place.project) : [];
  const round = {
    minWidth: t.touch,
    minHeight: t.touch,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    borderRadius: t.touch / 2,
    backgroundColor: t.c.surface,
  };

  return (
    <View
      style={{
        backgroundColor: t.c.bg,
        borderBottomWidth: 1,
        borderBottomColor: t.c.line,
        paddingHorizontal: 16,
        paddingTop: insets.top + 10,
        paddingBottom: 10,
        gap: 8,
      }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <View style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: t.c.primary, alignItems: 'center', justifyContent: 'center' }}>
          <T style={{ color: t.c.onPrimary, fontWeight: '800' }}>{appName.slice(0, 3).toUpperCase()}</T>
        </View>
        <View style={{ flex: 1 }}>
          <T style={{ fontWeight: '800' }} numberOfLines={1}>
            {appName}
          </T>
          {badge ? (
            <T variant="small" color="muted" style={{ fontWeight: '700' }} numberOfLines={1}>
              {badge}
            </T>
          ) : null}
        </View>
        <Pressable
          accessibilityRole="switch"
          accessibilityState={{ checked: t.outdoor }}
          accessibilityLabel={text('today.outdoor', { state: t.outdoor ? 'ON' : 'OFF' })}
          onPress={() => t.setOutdoor(!t.outdoor)}
          style={[round, t.outdoor && { borderWidth: 3, borderColor: t.c.primary }]}>
          <Icon name="sun" size={t.font(24)} color={t.c.warn} />
        </Pressable>
        <Pressable accessibilityRole="button" accessibilityLabel={text('header.inbox', { count: unread })} onPress={() => router.push('/inbox')} style={round}>
          <Icon name="bell" size={t.font(24)} color={t.c.primary} />
          {unread > 0 && (
            <View
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                minWidth: 24,
                height: 24,
                paddingHorizontal: 5,
                borderRadius: 12,
                backgroundColor: t.c.danger,
                alignItems: 'center',
                justifyContent: 'center',
              }}>
              <T variant="small" style={{ color: t.c.onPrimary, fontWeight: '800' }}>
                {unread > 99 ? '99+' : String(unread)}
              </T>
            </View>
          )}
        </Pressable>
      </View>

      {place && (
        <>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={text('header.projectA11y', { project: place.projectLabel })}
            onPress={() => setPicker('project')}
            style={{
              minHeight: t.touch,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
              paddingHorizontal: 12,
              borderRadius: 10,
              backgroundColor: t.c.surface,
              borderWidth: 1,
              borderColor: t.c.line,
            }}>
            <Icon name="map-pin" size={t.font(22)} color={t.c.primary} />
            <T style={{ flex: 1, fontWeight: '700' }} numberOfLines={1}>
              {place.projectLabel || text('header.noProject')}
            </T>
            <T variant="small" color="muted" style={{ fontWeight: '700' }}>
              {text('header.project')}
            </T>
            <Icon name="chevron-down" size={t.font(22)} color={t.c.text} />
          </Pressable>

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={text('header.siteA11y', { site: place.siteLabel })}
              onPress={() => setPicker('site')}
              style={{ minHeight: t.touch, flexDirection: 'row', alignItems: 'center', gap: 6, flexShrink: 1 }}>
              <Icon name="site" size={t.font(22)} color={t.c.primary} />
              <T color="primary" style={{ fontWeight: '700', textDecorationLine: 'underline', flexShrink: 1 }} numberOfLines={1}>
                {place.siteLabel}
              </T>
              <Icon name="chevron-down" size={t.font(20)} color={t.c.primary} />
            </Pressable>
            {shift && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={text('header.shiftA11y', { shift: shiftText(shift) })}
                onPress={() => {
                  const i = place.shifts.findIndex((s) => s.name === shift.name);
                  const next = place.shifts[(i + 1) % place.shifts.length];
                  if (next) choosePlace(place.site, next.name);
                }}
                style={{
                  minHeight: t.touch,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 6,
                  marginLeft: 'auto',
                  paddingHorizontal: 12,
                  borderRadius: t.touch / 2,
                  backgroundColor: isNight(shift) ? t.c.infoTint : t.c.warnTint,
                }}>
                <Icon name={isNight(shift) ? 'night' : 'sun'} size={t.font(20)} color={isNight(shift) ? t.c.primary : t.c.warn} />
                <T variant="small" style={{ fontWeight: '700' }} color={isNight(shift) ? 'primary' : 'warn'}>
                  {shiftText(shift)}
                </T>
              </Pressable>
            )}
          </View>
        </>
      )}

      <Sheet open={picker === 'project'} title={text('header.chooseProject')} onClose={() => setPicker(null)}>
        {projectsOf(places).map((p) => (
          <SheetOption
            key={p.project}
            icon="map-pin"
            label={p.label || text('header.noProject')}
            selected={p.project === place?.project}
            onPress={() => {
              const first = places.find((x) => x.project === p.project);
              if (first) choosePlace(first.site, null);
              setPicker(null);
            }}
          />
        ))}
      </Sheet>
      <Sheet open={picker === 'site'} title={text('header.chooseSite')} onClose={() => setPicker(null)}>
        {sitesHere.map((p) => (
          <SheetOption
            key={p.site}
            icon="site"
            label={p.siteLabel}
            detail={roleBadge(p)}
            selected={p.site === place?.site}
            onPress={() => {
              choosePlace(p.site, null);
              setPicker(null);
            }}
          />
        ))}
      </Sheet>
    </View>
  );
}
