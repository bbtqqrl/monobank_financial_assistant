import { router } from 'expo-router';
import { Alert, Pressable, StyleSheet, View } from 'react-native';

import { signOutEverywhere } from '@/api/auth';
import { balanceHidden, setBalanceHidden } from '@/lib/cardOrder';
import { failure, success } from '@/lib/haptics';
import { goBack } from '@/lib/nav';
import {
  authenticate,
  biometricEnabled,
  lockAfter,
  lockEnabled,
  setBiometricEnabled,
  setLockAfter,
  useBiometry,
  type LockAfter,
} from '@/lib/security';
import { useTheme, withAlpha } from '@/theme';
import { Glass } from '@/ui/Glass';
import { Header } from '@/ui/Header';
import { Icon } from '@/ui/icons/Icon';
import { Screen } from '@/ui/Screen';
import { Segmented } from '@/ui/Segmented';
import { SettingRow } from '@/ui/SettingRow';
import { SwitchRow } from '@/ui/SwitchRow';
import { Text } from '@/ui/Text';

const AFTER: { key: LockAfter; label: string }[] = [
  { key: 'now', label: 'Одразу' },
  { key: '1m', label: 'Через 1 хв' },
  { key: '5m', label: 'Через 5 хв' },
];

// Profile › Безпека: the app's own code (and Face ID for it) before the app
// opens, hidden amounts and ending sessions on other phones
export default function SecurityScreen() {
  const { c } = useTheme();
  const biometry = useBiometry();
  const lock = lockEnabled.useValue();
  const face = biometricEnabled.useValue();
  const after = lockAfter.useValue();
  const hidden = balanceHidden.useValue();
  const name = biometry?.name ?? 'Face ID';

  // the switch follows the code: it flips once the sheet has set or removed it
  const switchLock = (on: boolean) => router.push({ pathname: '/pin', params: { mode: on ? 'new' : 'off' } });

  // turned on only after Face ID has worked once
  const switchFace = async (on: boolean) => {
    if (!on) {
      setBiometricEnabled(false);
      return;
    }
    if (await authenticate(`Відкривати Фінтрекер через ${name}`)) {
      setBiometricEnabled(true);
      success();
    }
  };

  const confirmSignOutEverywhere = () =>
    Alert.alert('Вийти на всіх пристроях?', 'На кожному телефоні, і на цьому теж, треба буде увійти знову', [
      { text: 'Скасувати', style: 'cancel' },
      {
        text: 'Вийти',
        style: 'destructive',
        onPress: () =>
          signOutEverywhere().catch(() => {
            failure();
            Alert.alert('Не вдалося вийти', 'Перевір інтернет і спробуй ще раз');
          }),
      },
    ]);

  return (
    <Screen background="accent">
      <Header title="Безпека" left={{ icon: 'chevronLeft', label: 'Назад', weight: 1.9, onPress: goBack }} />

      <Glass contentStyle={styles.card}>
        <Text variant="labelCaps" tone="ghost" style={styles.cardTitle}>
          Вхід
        </Text>
        <SwitchRow
          icon="lock"
          label="Код-пароль"
          caption={lock ? undefined : 'Застосунок відкриватиметься після коду'}
          value={lock}
          onChange={switchLock}
        />
        {lock ? (
          <SwitchRow
            icon="faceid"
            label={`Відкривати через ${name}`}
            caption={biometry && !biometry.available ? `На телефоні не налаштовано ${name}` : undefined}
            value={face}
            onChange={switchFace}
            disabled={!biometry?.available && !face}
          />
        ) : null}
        {lock ? (
          <SettingRow icon="pencil" label="Змінити код" onPress={() => router.push({ pathname: '/pin', params: { mode: 'change' } })} />
        ) : null}
        {lock ? (
          <View style={styles.after}>
            <Text variant="rowCaption" tone="muted" style={styles.afterLabel}>
              Просити знову, коли застосунок був у фоні
            </Text>
            <Segmented options={AFTER} value={after} onChange={setLockAfter} />
          </View>
        ) : null}
      </Glass>

      <Glass contentStyle={styles.card}>
        <Text variant="labelCaps" tone="ghost" style={styles.cardTitle}>
          Приватність
        </Text>
        <SwitchRow
          icon="eye"
          label="Приховувати суми"
          caption="Або тапом по балансу на Огляді"
          value={hidden}
          onChange={setBalanceHidden}
        />
      </Glass>

      <Pressable
        accessibilityRole="button"
        onPress={confirmSignOutEverywhere}
        style={({ pressed }) => pressed && styles.pressed}
      >
        {/* plain glass with a red label, like «Вийти з акаунта» */}
        <Glass radius={17} contentStyle={styles.everywhere}>
          <Icon name="phone" size={17} color={c.danger} weight={1.9} />
          <Text variant="bodyStrong" tone="danger" style={styles.everywhereLabel}>
            Вийти на всіх пристроях
          </Text>
        </Glass>
      </Pressable>
      <Text variant="rowCaption" tone="faint" style={[styles.note, { color: withAlpha(c.ink, 0.5) }]}>
        Якщо телефон загубився або хтось інший знає твій пароль
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  // Figma: 12 16 4 16, like the other settings cards
  card: { paddingTop: 12, paddingHorizontal: 16, paddingBottom: 6 },
  cardTitle: { marginBottom: 2 },
  after: { gap: 10, paddingTop: 4, paddingBottom: 10 },
  afterLabel: { fontSize: 12.5 },
  pressed: { opacity: 0.6 },
  everywhere: { height: 48, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center' },
  everywhereLabel: { fontSize: 14 },
  note: { textAlign: 'center', paddingHorizontal: 24, marginTop: -4 },
});
