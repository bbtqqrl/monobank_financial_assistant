// Hermes has no Intl.PluralRules / Intl.RelativeTimeFormat.
// Order matters, each one depends on the previous.
import '@formatjs/intl-getcanonicallocales/polyfill.js';
import '@formatjs/intl-locale/polyfill.js';

import '@formatjs/intl-pluralrules/polyfill.js';
import '@formatjs/intl-pluralrules/locale-data/uk.js';
import '@formatjs/intl-pluralrules/locale-data/pl.js';
import '@formatjs/intl-pluralrules/locale-data/en.js';

import '@formatjs/intl-relativetimeformat/polyfill.js';
import '@formatjs/intl-relativetimeformat/locale-data/uk.js';
import '@formatjs/intl-relativetimeformat/locale-data/pl.js';
import '@formatjs/intl-relativetimeformat/locale-data/en.js';
