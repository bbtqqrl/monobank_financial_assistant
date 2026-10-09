import { router } from 'expo-router';
import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { FONT } from '@/lib/fonts';
import { useTheme } from '@/theme';
import { TAB_ICONS } from '@/ui/tabIcons';

// System tab bar: on iOS 26+ it's Liquid Glass (lens under the finger,
// minimises on scroll), on Android it's the Material bar.
// Icons are our own PNGs in design colours, drawn "original" so iOS doesn't
// repaint the idle ones black. The native container isn't transparent, so
// each tab draws its own backdrop.
export default function TabsLayout() {
  const { c, dark } = useTheme();
  const icons = dark ? TAB_ICONS.dark : TAB_ICONS.light;
  const label = { fontFamily: FONT.ui.semiBold, fontSize: 10 };

  return (
    <NativeTabs
      tintColor={c.ink}
      labelStyle={{ default: { ...label, color: c.ghost }, selected: { ...label, color: c.ink } }}
      minimizeBehavior="onScrollDown"
    >
      <NativeTabs.Trigger name="(overview)">
        <NativeTabs.Trigger.Label>Огляд</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon src={icons.index} renderingMode="original" md="home" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="budgets">
        <NativeTabs.Trigger.Label>Бюджети</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon src={icons.budgets} renderingMode="original" md="speed" />
      </NativeTabs.Trigger>
      {/* not a tab: it opens the new transaction sheet over whatever is open */}
      <NativeTabs.Trigger name="add" disabled listeners={{ tabPress: () => router.push('/new') }}>
        <NativeTabs.Trigger.Label>Додати</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon src={icons.add} renderingMode="original" md="add_circle" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="analytics">
        <NativeTabs.Trigger.Label>Аналітика</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon src={icons.analytics} renderingMode="original" md="bar_chart" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="assistant">
        <NativeTabs.Trigger.Label>Асистент</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon src={icons.assistant} renderingMode="original" md="auto_awesome" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
