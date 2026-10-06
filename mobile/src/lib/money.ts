// Amounts are signed integers in minor units (kopiyky) + numeric ISO 4217 code,
// same as the backend stores them. No floats anywhere.
// Not using Intl currency style: uk-UA gives "грн" instead of ₴.

export type Locale = 'uk' | 'pl' | 'en';

export const UAH = 980;
export const PLN = 985;

const CURRENCIES: Record<number, { symbol: string; exponent: number }> = {
  980: { symbol: '₴', exponent: 2 },
  985: { symbol: 'zł', exponent: 2 },
  840: { symbol: '$', exponent: 2 },
  978: { symbol: '€', exponent: 2 },
  826: { symbol: '£', exponent: 2 },
  203: { symbol: 'Kč', exponent: 2 },
  348: { symbol: 'Ft', exponent: 2 },
  392: { symbol: '¥', exponent: 0 },
};

const NBSP = ' ';
const MINUS = '−';

// pl doesn't group 4-digit numbers: 5000,00 zł but 12 000,00 zł
const NUMBER_FORMAT: Record<Locale, { group: string; decimal: string; minDigitsToGroup: number }> = {
  uk: { group: NBSP, decimal: ',', minDigitsToGroup: 4 },
  pl: { group: NBSP, decimal: ',', minDigitsToGroup: 5 },
  en: { group: ',', decimal: '.', minDigitsToGroup: 4 },
};

export type MoneyOptions = {
  locale?: Locale;
  // auto: minus only, always: +/−, never: no sign
  sign?: 'auto' | 'always' | 'never';
  // false rounds to whole units: 18 740 ₴
  cents?: boolean;
};

export function formatMoney(minor: number, currency: number = UAH, opts: MoneyOptions = {}): string {
  const { locale = 'uk', sign = 'auto', cents = true } = opts;
  const cur = CURRENCIES[currency] ?? { symbol: '¤', exponent: 2 };
  const fmt = NUMBER_FORMAT[locale];
  const scale = 10 ** cur.exponent;
  const abs = Math.abs(minor);

  let whole: number;
  let fraction = '';
  if (cents && cur.exponent > 0) {
    whole = Math.floor(abs / scale);
    fraction = fmt.decimal + String(abs % scale).padStart(cur.exponent, '0');
  } else {
    whole = Math.round(abs / scale);
  }

  let digits = String(whole);
  if (digits.length >= fmt.minDigitsToGroup) {
    digits = digits.replace(/\B(?=(\d{3})+(?!\d))/g, fmt.group);
  }

  const number = digits + fraction;
  // −30 kopiyky without cents would read "−0 ₴"
  const zero = minor === 0 || (whole === 0 && !fraction);
  const prefix = sign === 'never' || zero ? '' : minor < 0 ? MINUS : sign === 'always' ? '+' : '';

  // en puts one-char symbols in front: −₴526.40, $1,234.00
  if (locale === 'en' && cur.symbol.length === 1) return prefix + cur.symbol + number;
  return prefix + number + NBSP + cur.symbol;
}
