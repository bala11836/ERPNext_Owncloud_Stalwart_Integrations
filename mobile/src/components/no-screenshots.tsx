import { usePreventScreenCapture } from 'expo-screen-capture';

/**
 * Build guide section 9: screenshots and the app-switcher preview are blocked while this is on screen
 * (payslips, approvals, My HR). Rendered as a component so screens can switch it on conditionally.
 */
export function NoScreenshots() {
  usePreventScreenCapture();
  return null;
}
