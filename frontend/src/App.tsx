import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Dashboard } from '@/pages/Dashboard';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

const Journeys = lazy(() => import('@/pages/Journeys').then((m) => ({ default: m.Journeys })));
const Attribution = lazy(() => import('@/pages/Attribution').then((m) => ({ default: m.Attribution })));
const Channels = lazy(() => import('@/pages/Channels').then((m) => ({ default: m.Channels })));
const Customers = lazy(() => import('@/pages/Customers').then((m) => ({ default: m.Customers })));

const PageFallback = () => (
  <div className="space-y-6 p-6 animate-pulse" aria-busy="true">
    <Skeleton className="h-8 w-64 rounded-xl" />
    <Skeleton className="h-4 w-96 rounded-lg" />
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
      <Skeleton className="h-28 rounded-2xl" />
      <Skeleton className="h-28 rounded-2xl" />
      <Skeleton className="h-28 rounded-2xl" />
      <Skeleton className="h-28 rounded-2xl" />
    </div>
    <Skeleton className="h-72 w-full rounded-2xl mt-6" />
  </div>
);

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route
            path="/journeys"
            element={
              <Suspense fallback={<PageFallback />}>
                <Journeys />
              </Suspense>
            }
          />
          <Route
            path="/attribution"
            element={
              <Suspense fallback={<PageFallback />}>
                <Attribution />
              </Suspense>
            }
          />
          <Route
            path="/channels"
            element={
              <Suspense fallback={<PageFallback />}>
                <Channels />
              </Suspense>
            }
          />
          <Route
            path="/customers"
            element={
              <Suspense fallback={<PageFallback />}>
                <Customers />
              </Suspense>
            }
          />
          <Route
            path="/customers/:customerId"
            element={
              <Suspense fallback={<PageFallback />}>
                <Customers />
              </Suspense>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </ErrorBoundary>
);
};

export default App;
