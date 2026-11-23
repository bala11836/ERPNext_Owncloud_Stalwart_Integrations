import {
  disableAppSwitcherProtectionAsync,
  enableAppSwitcherProtectionAsync,
  usePreventScreenCapture,
} from 'expo-screen-capture';
import { useEffect, useId } from 'react';
import { Platform } from 'react-native';

let protectedScreens = 0;

/** Keep capture and app-switcher snapshots protected while sensitive screens are mounted. */
export function NoScreenshots() {
  usePreventScreenCapture(useId());

  useEffect(() => {
    if (Platform.OS !== 'ios') return;
    protectedScreens += 1;
    if (protectedScreens === 1) {
      void enableAppSwitcherProtectionAsync(1).catch(() => {});
    }
    return () => {
      protectedScreens -= 1;
      if (protectedScreens === 0) {
        void disableAppSwitcherProtectionAsync().catch(() => {});
      }
    };
  }, []);

  return null;
}
