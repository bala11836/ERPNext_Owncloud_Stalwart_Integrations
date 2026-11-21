import { Redirect } from 'expo-router';

// Android delivers the sign-in return address (…/oauth/callback) to the app as a link; the sign-in code
// itself is read by expo-auth-session, so this screen only sends the user on.
export default function OAuthCallback() {
  return <Redirect href="/" />;
}
