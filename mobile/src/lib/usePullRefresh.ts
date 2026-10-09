import { useState } from 'react';

// The pull-to-refresh spinner runs only for the user's own pull. Tying it to
// isRefetching would also show it for background refetches (app focus, lists
// invalidated after a save) and push the whole screen down.
export function usePullRefresh(run: () => Promise<unknown>) {
  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = () => {
    setRefreshing(true);
    run().finally(() => setRefreshing(false));
  };
  return { refreshing, onRefresh };
}
