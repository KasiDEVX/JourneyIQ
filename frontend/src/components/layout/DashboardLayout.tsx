import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { checkHealth } from '@/services/api';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

export const DashboardLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(new Date());

  const verifyHealth = async () => {
    try {
      await checkHealth();
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  };

  useEffect(() => {
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await verifyHealth();
    // Dispatch custom refresh event for child page views to reload their data
    window.dispatchEvent(new CustomEvent('journeyiq:refresh'));
    setTimeout(() => {
      setIsRefreshing(false);
      setLastUpdated(new Date());
    }, 600);
  };

  return (
    <div className="min-h-screen bg-[#F6F7F9] flex text-graphite-900 font-sans">
      {/* Sidebar */}
      <Sidebar
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        apiOnline={apiOnline}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        <Header
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          apiOnline={apiOnline}
          lastUpdated={lastUpdated}
        />

        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto space-y-8">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};
