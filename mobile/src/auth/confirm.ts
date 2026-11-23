// Build guide section 5: Face ID (or fingerprint, or the phone passcode) before Approve, Reject, Submit and Pay.
import * as LocalAuthentication from 'expo-local-authentication';

/** Ask the person to confirm with Face ID, fingerprint or passcode; true only when they did. */
export async function confirmIdentity(reason: string): Promise<boolean> {
  try {
    return (await LocalAuthentication.authenticateAsync({ promptMessage: reason })).success;
  } catch {
    return false;
  }
}
