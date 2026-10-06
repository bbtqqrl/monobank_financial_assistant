import { focusManager, QueryClient } from '@tanstack/react-query';
import { AppState } from 'react-native';

import { ApiError, ContractError } from './client';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status < 500) && !(error instanceof ContractError) && count < 2,
    },
  },
});

// coming back from the background counts as focus, so stale data refreshes on its own
AppState.addEventListener('change', (state) => focusManager.setFocused(state === 'active'));
