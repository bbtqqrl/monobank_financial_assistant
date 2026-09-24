# Mobile

## Run on your phone (Expo Go)

1. Install **Expo Go** from the App Store / Google Play.
2. Put the phone and the computer on the same Wi-Fi.
3. Start the dev server:

   ```bash
   cd mobile
   npm install
   npx expo start --go
   ```

4. Scan the QR code from the terminal:
   - iPhone — with the Camera app
   - Android — from inside Expo Go

Saving a file reloads the app on the phone. Shake the phone to open the dev menu.

If the phone can't reach the computer (different network, VPN, office Wi-Fi):

```bash
npx expo start --go --tunnel
```

## Run in the iOS simulator

Needs Xcode and CocoaPods.

```bash
npx expo run:ios
```

If `pod install` fails with an encoding error, run `export LANG=en_US.UTF-8` first.
