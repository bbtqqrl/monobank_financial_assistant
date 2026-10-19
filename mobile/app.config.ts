import type { ConfigContext, ExpoConfig } from 'expo/config';

// The backend still speaks plain HTTP on a bare IP, which iOS refuses unless
// told otherwise. Allowed in development builds only: a release build
// (APP_ENV=production) waits for the backend to get HTTPS.
const allowHttp = process.env.APP_ENV !== 'production';

export default ({ config }: ConfigContext): ExpoConfig =>
  ({
    ...config,
    ios: {
      ...config.ios,
      infoPlist: {
        ...config.ios?.infoPlist,
        ...(allowHttp ? { NSAppTransportSecurity: { NSAllowsArbitraryLoads: true } } : {}),
      },
    },
  }) as ExpoConfig;
