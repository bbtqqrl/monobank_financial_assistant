import { Pill, PillRow } from '@/ui/Pill';

type Option<K extends string> = { key: K; label: string };

type Props<K extends string> = {
  options: Option<K>[];
  value: K;
  onChange: (key: K) => void;
};

export function FilterPills<K extends string>({ options, value, onChange }: Props<K>) {
  return (
    <PillRow>
      {options.map((o) => (
        <Pill key={o.key} role="tab" label={o.label} active={o.key === value} onPress={() => onChange(o.key)} />
      ))}
    </PillRow>
  );
}
