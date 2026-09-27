import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { useTheme } from '@/theme';

import { ICONS, type IconName } from './paths';

type Props = {
  name: IconName;
  size?: number;
  color?: string;
  // stroke width in the 24×24 grid, scales with size
  weight?: number;
};

export function Icon({ name, size = 24, color, weight = 1.7 }: Props) {
  const { c } = useTheme();

  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color ?? c.inkSoft}
      strokeWidth={weight}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICONS[name].map((shape, i) => {
        switch (shape[0]) {
          case 'path':
            return <Path key={i} {...shape[1]} />;
          case 'circle':
            return <Circle key={i} {...shape[1]} />;
          case 'rect':
            return <Rect key={i} {...shape[1]} />;
        }
      })}
    </Svg>
  );
}

export type { IconName };
