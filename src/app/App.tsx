import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type React from 'react';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { AppRouter } from './Router';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppRouter />
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
