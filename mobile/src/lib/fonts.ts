// PostScript names. RN ignores fontWeight for custom fonts, so pick the file instead.
export const FONT = {
  ui: {
    regular: 'Manrope-Regular',
    medium: 'Manrope-Medium',
    semiBold: 'Manrope-SemiBold',
    bold: 'Manrope-Bold',
  },
  display: {
    medium: 'Rubik-Medium',
    semiBold: 'Rubik-SemiBold',
  },
} as const;

export const FONT_FILES = {
  'Manrope-Regular': require('../../assets/fonts/Manrope-Regular.ttf'),
  'Manrope-Medium': require('../../assets/fonts/Manrope-Medium.ttf'),
  'Manrope-SemiBold': require('../../assets/fonts/Manrope-SemiBold.ttf'),
  'Manrope-Bold': require('../../assets/fonts/Manrope-Bold.ttf'),
  'Rubik-Medium': require('../../assets/fonts/Rubik-Medium.ttf'),
  'Rubik-SemiBold': require('../../assets/fonts/Rubik-SemiBold.ttf'),
};
