import React, { useState, useEffect } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { OverviewAnalytics } from '@/types/analytics';
import { getOverview } from '@/services/api';
import { KPIGrid } from '@/components/dashboard/KPIGrid';
import { AttributionPanel } from '@/components/dashboard/AttributionPanel';
import { ChannelPerformance } from '@/components/dashboard/ChannelPerformance';
import { JourneyPatterns } from '@/components/dashboard/JourneyPatterns';
import { CustomerJourneyFlow } from '@/components/dashboard/CustomerJourneyFlow';
import { Button } from '@/components/ui/Button';

export const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOverview();
      setOverview(data);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to JourneyIQ analytics service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  useEffect(() => {
    const onRefresh = () => fetchOverviewData();
    window.addEventListener('journeyiq:refresh', onRefresh);
    return () => window.removeEventListener('journeyiq:refresh', onRefresh);
  }, []);

  return (
    <div className="space-y-8">
      {/* Backend Status Notice when database is offline */}
      {error && !overview && (
        <div className="card-soft p-4 border-l-4 border-l-amber-500 bg-amber-50/50 border border-amber-200/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-amber-900">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <div>
              <span className="font-bold">JourneyIQ System Status:</span>{' '}
              {error.includes('500') || error.includes('status')
                ? 'Backend database is offline. The analytics engine will populate live cohort data once PostgreSQL is started.'
                : error}
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchOverviewData}
            icon={<RefreshCw className="w-3 h-3" />}
          >
            Retry
          </Button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <KPIGrid data={overview} loading={loading && !error} />

      {/* Main Attribution Visual Centerpiece */}
      <AttributionPanel />

      {/* Stage 7: Customer Journey Flow (compact preview linking to /journeys) */}
      <CustomerJourneyFlow compact={true} />

      {/* Two Column Section: Channels & Top Journeys */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        <div className="xl:col-span-7">
          <ChannelPerformance />
        </div>
        <div className="xl:col-span-5">
          <JourneyPatterns limit={6} />
        </div>
      </div>
    </div>
  );
};
