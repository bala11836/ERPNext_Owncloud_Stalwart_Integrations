// Android only: the full-page approval alert (a native screen over the locked screen, ringing up to 30 seconds).
// Absent on iPhone and in tests: callers fall back to a normal notification.
import { requireOptionalNativeModule } from 'expo';

/** The texts and place of one alert; every value is plain text chosen by the app (kind, count, site only). */
export type AlertTexts = {
  area: string;
  areaLabel: string;
  title: string;
  body: string;
  url: string;
  channel: string;
  listChannel: string;
  later: string;
  review: string;
};

type Native = {
  schedule(seconds: number, alert: AlertTexts): void;
  canUseFullScreen(): boolean;
  openFullScreenSettings(): void;
};

export const ApprovalAlert = requireOptionalNativeModule<Native>('ApprovalAlert');
