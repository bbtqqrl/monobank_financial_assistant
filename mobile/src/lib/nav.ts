import { router } from 'expo-router';

// a screen opened from a link has nothing to go back to
export function goBack() {
  if (router.canGoBack()) router.back();
  else router.replace('/');
}

// sheets over the transactions list, which may also be opened from a link
export function closeSheet() {
  if (router.canGoBack()) router.back();
  else router.replace('/transactions');
}
