import { Redirect } from 'expo-router';

// The «+» tab never opens itself, it only shows the sheet (see the tabs
// layout). This is for a link that lands here.
export default function AddScreen() {
  return <Redirect href="/new" />;
}
