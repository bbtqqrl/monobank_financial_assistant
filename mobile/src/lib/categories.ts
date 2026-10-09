import type { Colors } from '@/theme/colors';
import type { IconName } from '@/ui/icons/Icon';

export type CategoryLook = { icon: IconName; color: keyof Colors['category'] };

// The backend sends only the category slug (see the category_kinds_and_cleanup
// migration), so icon and colour are picked here: a parent and its children
// share a look, a few children get their own where the design has one.
const LOOKS: [CategoryLook, string[]][] = [
  // spending
  [{ icon: 'cart', color: 'green' }, ['produkty', 'alkohol', 'tiutiun']],
  [{ icon: 'food', color: 'copper' }, ['kafe-ta-restorany', 'restorany', 'kafe', 'kavyarni', 'fastfud', 'dostavka-izhi', 'bary-ta-paby']],
  [{ icon: 'taxi', color: 'taxi' }, ['taksi', 'karsherynh']],
  [{ icon: 'bus', color: 'slate' }, ['transport', 'hromadskyi-transport', 'parkuvannia', 'platni-dorohy']],
  [{ icon: 'fuel', color: 'slate' }, ['palne', 'avtomobil', 'remont-avtomobilia', 'avtozapchastyny', 'myika-avtomobilia', 'strakhuvannia-avto']],
  [{ icon: 'home', color: 'brown' }, ['zhytlo', 'orenda-zhytla', 'ipoteka', 'dim-ta-interier', 'mebli', 'dekor-dlia-domu']],
  [{ icon: 'utilities', color: 'blue' }, ['komunalni-posluhy', 'elektroenerhiia', 'haz', 'voda', 'opalennia', 'internet']],
  [{ icon: 'phone', color: 'blue' }, ['mobilnyi-zviazok']],
  [{ icon: 'repair', color: 'brown' }, ['pobutovi-posluhy', 'prybyrannia', 'remont-ta-obsluhovuvannia-zhytla']],
  [{ icon: 'laptop', color: 'neutral' }, ['tekhnika-ta-elektronika']],
  [{ icon: 'repeat', color: 'blue' }, ['onlain-servisy-ta-pidpysky']],
  [{ icon: 'game', color: 'olive' }, ['rozvahy', 'kino', 'kontserty', 'muzei', 'ihry', 'sport', 'sportzal', 'sportyvnyi-odiah-ta-inventar', 'tovary-dlia-ditei', 'ihrashky']],
  [{ icon: 'books', color: 'neutral' }, ['knyhy', 'kantseliariia', 'osvita', 'kursy']],
  [{ icon: 'shirt', color: 'rose' }, ['odiah', 'vzuttia']],
  [{ icon: 'health', color: 'clay' }, ['zdorovia', 'apteka', 'stomatolohiia', 'medychni-posluhy', 'analizy-ta-diahnostyka', 'okuliary-ta-optyka', 'krasa-ta-hihiiena', 'parfumeriia', 'posluhy-krasy', 'perukarnia', 'manikiur-ta-pedykiur', 'spa-ta-masazh']],
  [{ icon: 'pets', color: 'plum' }, ['tovary-dlia-tvaryn', 'veterynariia']],
  [{ icon: 'travel', color: 'teal' }, ['podorozhi', 'aviakvytky', 'zaliznychni-kvytky', 'avtobusni-kvytky', 'hoteli', 'turystychni-posluhy']],
  [{ icon: 'list', color: 'slate' }, ['profesiini-servisy', 'iurydychni-posluhy', 'bukhhalterski-posluhy', 'derzhavni-posluhy', 'poshta-ta-dostavka', 'druk-ta-kopiiuvannia', 'marketynh-ta-reklama']],
  [{ icon: 'card', color: 'dim' }, ['finansy', 'komisii-ta-zbory', 'strakhuvannia', 'podatky']],
  [{ icon: 'sparkle', color: 'rose' }, ['podarunky-ta-blahodiinist', 'podarunky', 'blahodiinist']],
  [{ icon: 'person', color: 'blue' }, ['perekazy-liudiam']],
  [{ icon: 'card', color: 'neutral' }, ['inshi-vytraty', 'nevidome']],
  // income
  [{ icon: 'income', color: 'green' }, ['zarplata', 'inshi-dokhody']],
  [{ icon: 'laptop', color: 'green' }, ['pidpryiemnytstvo']],
  [{ icon: 'list', color: 'green' }, ['derzhavni-vyplaty']],
  [{ icon: 'cart', color: 'teal' }, ['prodazh-rechei']],
  [{ icon: 'person', color: 'green' }, ['perekazy-vid-liudei']],
  [{ icon: 'star', color: 'green' }, ['keshbek']],
  [{ icon: 'chart', color: 'green' }, ['vidsotky-ta-dyvidendy']],
  // the user's own money moving
  [{ icon: 'transfer', color: 'slate' }, ['rukh-koshtiv', 'mizh-svoimy-rakhunkamy', 'popovnennia-rakhunku']],
  [{ icon: 'refresh', color: 'teal' }, ['obmin-valiut']],
  [{ icon: 'jar', color: 'teal' }, ['zaoshchadzhennia', 'investytsii']],
  [{ icon: 'card', color: 'dim' }, ['hroshovi-zniattia', 'kredyty', 'pohashennia-kredytu']],
];

const BY_SLUG = new Map(LOOKS.flatMap(([look, slugs]) => slugs.map((s) => [s, look] as const)));

const UNKNOWN: CategoryLook = { icon: 'card', color: 'neutral' };
const INCOME: CategoryLook = { icon: 'income', color: 'green' };

export function categoryLook(slug: string | undefined, amount: number): CategoryLook {
  const look = slug ? BY_SLUG.get(slug) : undefined;
  if (look) return look;
  return amount > 0 ? INCOME : UNKNOWN;
}
