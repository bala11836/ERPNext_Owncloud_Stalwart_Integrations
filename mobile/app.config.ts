// app.json holds neutral defaults. A deployment's name, app ID and link scheme come from the
// private mobile/.env (see .env.example), which Expo loads before reading this file; never from Git.
import type { ConfigContext, ExpoConfig } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => {
  const id = process.env.APP_ID;
  return {
    ...config,
    name: process.env.APP_NAME || config.name || 'ERP',
    slug: process.env.APP_SLUG || config.slug || 'erp-mobile',
    scheme: process.env.APP_SCHEME || config.scheme,
    ios: { ...config.ios, bundleIdentifier: id || config.ios?.bundleIdentifier },
    android: { ...config.android, package: id || config.android?.package },
  };
};
