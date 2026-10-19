import { router, useIsFocused } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { FONT } from '@/lib/fonts';
import { locked } from '@/lib/security';
import { tabBarMinimizes } from '@/lib/tabBar';
import { useTheme } from '@/theme';
import { FlowField } from '@/ui/FlowField';
import { TAB_ICONS } from '@/ui/tabIcons';

// System tab bar: on iOS 26+ it's Liquid Glass (lens under the finger,
// minimises on scroll), on Android it's the Material bar.
// Icons are our own PNGs in design colours, drawn "original" so iOS doesn't
// repaint the idle ones black. One flowing canvas lies under all the tabs and
// shows through their see-through screens, so switching tabs only moves its
// colours, smoothly (each tab steers it, see Backdrop).
const SEE_THROUGH = { backgroundColor: 'transparent' } as const;
export default function TabsLayout() {
  const { c, dark } = useTheme();
  const icons = dark ? TAB_ICONS.dark : TAB_ICONS.light;
  const label = { fontFamily: FONT.ui.semiBold, fontSize: 10 };
  const minimizes = tabBarMinimizes.useValue();
  // still while a screen or the lock screen covers the tabs
  const focused = useIsFocused();
  const isLocked = locked.useValue();

  return (
    <View style={[styles.root, { backgroundColor: c.bg }]}>
      <FlowField running={focused && !isLocked} />
      <NativeTabs
        tintColor={c.ink}
        unstable_nativeProps={{ nativeContainerStyle: SEE_THROUGH }}
        labelStyle={{ default: { ...label, color: c.ghost }, selected: { ...label, color: c.ink } }}
        minimizeBehavior={minimizes ? 'onScrollDown' : 'never'}
      >
        <NativeTabs.Trigger contentStyle={SEE_THROUGH} name="(overview)">
          <NativeTabs.Trigger.Label>Огляд</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={icons.index} renderingMode="original" md="home" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger contentStyle={SEE_THROUGH} name="budgets">
          <NativeTabs.Trigger.Label>Бюджети</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={icons.budgets} renderingMode="original" md="speed" />
        </NativeTabs.Trigger>
        {/* not a tab: it opens the new transaction sheet over whatever is open */}
        <NativeTabs.Trigger
          contentStyle={SEE_THROUGH}
          name="add"
          disabled
          listeners={{ tabPress: () => router.push('/new') }}
        >
          <NativeTabs.Trigger.Label>Додати</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={icons.add} renderingMode="original" md="add_circle" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger contentStyle={SEE_THROUGH} name="analytics">
          <NativeTabs.Trigger.Label>Аналітика</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={icons.analytics} renderingMode="original" md="bar_chart" />
        </NativeTabs.Trigger>
        <NativeTabs.Trigger contentStyle={SEE_THROUGH} name="assistant">
          <NativeTabs.Trigger.Label>Асистент</NativeTabs.Trigger.Label>
          <NativeTabs.Trigger.Icon src={icons.assistant} renderingMode="original" md="auto_awesome" />
        </NativeTabs.Trigger>
      </NativeTabs>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
