// This phone's push address (Google FCM) is kept in the encrypted store; sign-out tells ERPNext to forget it
// (server part mobile_push). Shared by the session and lib/push without importing each other.
export const PUSH_ADDRESS = 'push-address';
export const PUSH_API = 'erpnext_drive_integrations.mobile_push.api';
