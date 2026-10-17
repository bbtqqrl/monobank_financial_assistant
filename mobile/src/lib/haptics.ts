import * as Haptics from 'expo-haptics';

const { ImpactFeedbackStyle: Impact, NotificationFeedbackType: Notice } = Haptics;

const impact = (style: Haptics.ImpactFeedbackStyle) => () => {
  Haptics.impactAsync(style).catch(() => {});
};
const notice = (type: Haptics.NotificationFeedbackType) => () => {
  Haptics.notificationAsync(type).catch(() => {});
};

// Taptic Engine has a feel for each kind of moment, from a faint tick to a
// firm knock; the lighter the moment, the lighter the feel.

// picking one of several: a segment, a category, a day, a month
export const tap = () => {
  Haptics.selectionAsync().catch(() => {});
};
// something switched on or off: amounts hidden, a card shown on Overview
export const toggle = impact(Impact.Light);
// a pull let go far enough to refresh, a dragged row put down
export const settle = impact(Impact.Soft);
// a press held long enough to open more: card settings, a budget's limit
export const hold = impact(Impact.Rigid);
// a row lifted to drag, something deleted
export const thud = impact(Impact.Medium);

export const success = notice(Notice.Success);
export const warning = notice(Notice.Warning);
export const failure = notice(Notice.Error);
