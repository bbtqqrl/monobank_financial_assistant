import { ActionSheetIOS, Alert, Platform } from 'react-native';

import { setThemePref, THEME_LABELS, type ThemePref } from './preference';

const ORDER: ThemePref[] = ['system', 'light', 'dark'];

export function pickTheme(current: ThemePref) {
  const labels = ORDER.map((p) => THEME_LABELS[p]);

  if (Platform.OS === 'ios') {
    ActionSheetIOS.showActionSheetWithOptions(
      {
        title: 'Тема',
        options: [...labels, 'Скасувати'],
        cancelButtonIndex: labels.length,
        disabledButtonIndices: [ORDER.indexOf(current)],
      },
      (i) => {
        const pref = ORDER[i];
        if (pref) setThemePref(pref);
      },
    );
    return;
  }

  Alert.alert(
    'Тема',
    undefined,
    ORDER.filter((p) => p !== current).map((p) => ({ text: THEME_LABELS[p], onPress: () => setThemePref(p) })),
    { cancelable: true },
  );
}
