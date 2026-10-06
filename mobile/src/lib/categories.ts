import type { Colors } from '@/theme/colors';
import type { IconName } from '@/ui/icons/Icon';

export type CategoryLook = { icon: IconName; color: keyof Colors['category'] };

// The backend sends only the category slug (see alembic seed_categories), so
// icon and colour are picked here: a parent and its children share a look,
// a few children get their own where the design has one (taxi, fuel...).
const LOOKS: [CategoryLook, string[]][] = [
  [{ icon: 'cart', color: 'green' }, ['produkty', 'supermarkety', 'frukty-ta-ovochi', 'miaso-ta-ptytsia', 'ryba-ta-moreprodukty', 'khlib-ta-vypichka', 'molochni-produkty', 'solodoshchi', 'napoi', 'alkohol', 'tiutiun', 'kava-ta-chai']],
  [{ icon: 'food', color: 'copper' }, ['kafe-ta-restorany', 'dostavka-izhi', 'restorany', 'kafe', 'fastfud', 'bary-ta-paby', 'izha-na-vynis']],
  [{ icon: 'taxi', color: 'taxi' }, ['taksi', 'karsherynh']],
  [{ icon: 'bus', color: 'slate' }, ['transport', 'hromadskyi-transport', 'metro', 'avtobus', 'tramvai', 'troleibus', 'parkuvannia', 'platni-dorohy']],
  [{ icon: 'fuel', color: 'slate' }, ['palne', 'avtomobil', 'remont-avtomobilia', 'avtozapchastyny', 'myika-avtomobilia', 'strakhuvannia-avto']],
  [{ icon: 'home', color: 'brown' }, ['zhytlo', 'orenda-zhytla', 'ipoteka', 'dim-ta-interier', 'mebli', 'dekor-dlia-domu', 'pobutova-tekhnika', 'tovary-dlia-domu', 'pobutovi-vytraty']],
  [{ icon: 'utilities', color: 'blue' }, ['komunalni-posluhy', 'elektroenerhiia', 'haz', 'voda', 'opalennia', 'internet']],
  [{ icon: 'phone', color: 'blue' }, ['mobilnyi-zviazok', 'telefony']],
  [{ icon: 'repair', color: 'brown' }, ['pobutovi-posluhy', 'prybyrannia', 'remont-ta-obsluhovuvannia-zhytla']],
  [{ icon: 'laptop', color: 'neutral' }, ['tekhnika-ta-elektronika', 'kompiutery-ta-komplektuiuchi', 'aksesuary-dlia-tekhniky', 'prohramne-zabezpechennia']],
  [{ icon: 'repeat', color: 'blue' }, ['onlain-servisy-ta-pidpysky']],
  [{ icon: 'game', color: 'olive' }, ['ihry', 'tovary-dlia-ditei', 'ihrashky', 'sport', 'sportzal', 'sportyvnyi-odiah-ta-inventar', 'khobi', 'muzyka', 'kontserty', 'kino', 'teatr', 'muzei', 'rozvahy']],
  [{ icon: 'books', color: 'neutral' }, ['knyhy', 'kantseliariia', 'osvita', 'kursy', 'knyhy-ta-navchalni-materialy', 'repetytory']],
  [{ icon: 'shirt', color: 'rose' }, ['odiah', 'vzuttia', 'aksesuary']],
  [{ icon: 'health', color: 'clay' }, ['krasa-ta-hihiiena', 'kosmetyka', 'parfumeriia', 'pobutova-khimiia', 'zdorovia', 'apteka', 'stomatolohiia', 'medychni-posluhy', 'analizy-ta-diahnostyka', 'okuliary-ta-optyka', 'posluhy-krasy', 'perukarnia', 'manikiur-ta-pedykiur', 'spa-ta-masazh', 'fitnes-ta-ioha']],
  [{ icon: 'pets', color: 'plum' }, ['tovary-dlia-tvaryn', 'veterynariia']],
  [{ icon: 'travel', color: 'teal' }, ['podorozhi', 'aviakvytky', 'zaliznychni-kvytky', 'avtobusni-kvytky', 'hoteli', 'khostely', 'orenda-zhytla-u-podorozhi', 'turystychni-posluhy', 'vidriadzhennia']],
  [{ icon: 'jar', color: 'teal' }, ['zaoshchadzhennia', 'investytsii']],
  [{ icon: 'income', color: 'green' }, ['popovnennia-rakhunku']],
  [{ icon: 'card', color: 'dim' }, ['finansy', 'bankivski-komisii', 'komisii-ta-zbory', 'kredyty', 'pohashennia-kredytu', 'strakhuvannia', 'podatky', 'perekazy', 'hroshovi-zniattia']],
  [{ icon: 'sparkle', color: 'rose' }, ['podarunky-ta-blahodiinist', 'podarunky', 'blahodiinist']],
  [{ icon: 'card', color: 'neutral' }, ['inshi-vytraty', 'nevidome']],
  [{ icon: 'list', color: 'slate' }, ['profesiini-servisy', 'iurydychni-posluhy', 'bukhhalterski-posluhy', 'derzhavni-posluhy', 'poshta-ta-dostavka', 'druk-ta-kopiiuvannia', 'orenda-obladnannia', 'robochi-vytraty', 'marketynh-ta-reklama']],
];

const BY_SLUG = new Map(LOOKS.flatMap(([look, slugs]) => slugs.map((s) => [s, look] as const)));

const UNKNOWN: CategoryLook = { icon: 'card', color: 'neutral' };
const INCOME: CategoryLook = { icon: 'income', color: 'green' };

export function categoryLook(slug: string | undefined, amount: number): CategoryLook {
  const look = slug ? BY_SLUG.get(slug) : undefined;
  if (look) return look;
  return amount > 0 ? INCOME : UNKNOWN;
}
