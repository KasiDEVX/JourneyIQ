import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Users,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  ShoppingBag,
  ArrowRight,
  ExternalLink,
  Calendar,
  Sparkles,
} from 'lucide-react';
import { CustomerJourney } from '@/types/analytics';
import { getCustomerJourney } from '@/services/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export const Customers: React.FC = () => {
  const { customerId: routeCustomerId } = useParams<{ customerId?: string }>();
  const navigate = useNavigate();

  const [inputCustomerId, setInputCustomerId] = useState(routeCustomerId || '');
  const [journey, setJourney] = useState<CustomerJourney | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomer = async (cid: string) => {
    if (!cid.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getCustomerJourney(cid.trim());
      setJourney(res);
    } catch (err: any) {
      setJourney(null);
      setError(err.message || `Customer '${cid}' not found or database offline.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (routeCustomerId) {
      setInputCustomerId(routeCustomerId);
      fetchCustomer(routeCustomerId);
    }
  }, [routeCustomerId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputCustomerId.trim()) {
      navigate(`/customers/${inputCustomerId.trim()}`);
      fetchCustomer(inputCustomerId.trim());
    }
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case 'impression': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'click': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'page_view': return 'bg-gray-100 text-gray-700 border-gray-200';
      case 'product_view': return 'bg-cyan-50 text-cyan-700 border-cyan-200';
      case 'add_to_cart': return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'checkout': return 'bg-emerald-50 text-emerald-700 border-emerald-200 font-bold';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h1 className="text-2xl font-bold font-display tracking-tight text-graphite-950">
            Individual Customer Journey Inspector
          </h1>
          <Badge variant="coral">Session Replay</Badge>
        </div>
        <p className="text-sm text-gray-500">
          Trace discrete customer interactions, windowed sessions, and marketing touchpoint trajectories.
        </p>
      </div>

      {/* Lookup Bar */}
      <div className="card-soft p-5">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputCustomerId}
              onChange={(e) => setInputCustomerId(e.target.value)}
              placeholder="Enter customer UUID (e.g. cust-001 or paste UUID)..."
              className="w-full pl-10 pr-4 py-2.5 bg-ivory-50 rounded-xl border border-gray-200 text-xs text-graphite-900 font-mono focus:outline-hidden focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500"
            />
          </div>
          <Button type="submit" variant="primary" size="md" className="w-full sm:w-auto">
            Inspect Journey
          </Button>
        </form>
      </div>

      {/* Result Section */}
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-44 w-full rounded-3xl" />
          <Skeleton className="h-96 w-full rounded-3xl" />
        </div>
      ) : error ? (
        <div className="card-soft p-12 text-center text-xs text-red-500 bg-red-50/40 border-red-200">
          <p className="font-semibold text-sm text-red-600 mb-1">Lookup Error</p>
          <p>{error}</p>
        </div>
      ) : journey ? (
        <div className="space-y-6">
          {/* Journey KPI Header */}
          <div className="card-soft p-6 md:p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-5">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-lg font-bold font-mono text-graphite-950">
                    {journey.customer_id}
                  </h2>
                  <Badge variant={journey.converted ? 'emerald' : 'neutral'}>
                    {journey.converted ? 'Converted Customer' : 'Non-Converted'}
                  </Badge>
                </div>
                <p className="text-xs text-gray-400 mt-1 font-mono">
                  First seen: {new Date(journey.first_seen).toLocaleString()} · Last active:{' '}
                  {new Date(journey.last_activity).toLocaleString()}
                </p>
              </div>

              {journey.converted && journey.conversion_revenue && (
                <div className="text-right">
                  <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                    Order Revenue
                  </div>
                  <div className="text-2xl font-mono font-extrabold text-coral-600">
                    ${journey.conversion_revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                  {journey.conversion_order_id && (
                    <div className="text-[11px] font-mono text-gray-400">
                      ID: {journey.conversion_order_id}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Quick Metrics Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3 rounded-xl bg-ivory-50 border border-gray-100">
                <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">Touchpoints</div>
                <div className="text-lg font-mono font-bold text-graphite-900">{journey.touchpoint_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-ivory-50 border border-gray-100">
                <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">Sessions</div>
                <div className="text-lg font-mono font-bold text-graphite-900">{journey.session_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-ivory-50 border border-gray-100">
                <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">Total Events</div>
                <div className="text-lg font-mono font-bold text-graphite-900">{journey.event_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-ivory-50 border border-gray-100">
                <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">Duration</div>
                <div className="text-lg font-mono font-bold text-graphite-900">
                  {(journey.journey_duration_minutes / 60).toFixed(1)} hrs
                </div>
              </div>
            </div>

            {/* Channel Path Breadcrumb */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-mono mb-2">
                Reconstructed Channel Path
              </div>
              <div className="flex items-center flex-wrap gap-1.5 p-3 rounded-xl bg-ivory-50 border border-gray-100">
                {journey.channels.length === 0 ? (
                  <span className="text-xs font-mono text-gray-400">No marketing touchpoints</span>
                ) : (
                  journey.channels.map((ch, idx) => (
                    <React.Fragment key={idx}>
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-white text-graphite-900 border border-gray-200 shadow-2xs">
                        {ch}
                      </span>
                      {idx < journey.channels.length - 1 && (
                        <ArrowRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                      )}
                    </React.Fragment>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Chronological Event Timeline */}
          <div className="card-soft p-6 md:p-8 space-y-4">
            <div className="border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold font-display text-graphite-950">
                Chronological Event Log
              </h3>
              <p className="text-xs text-gray-400">
                Raw events received by the data layer, sorted ascending by timestamp.
              </p>
            </div>

            <div className="space-y-2 max-h-[480px] overflow-y-auto pr-2">
              {journey.events.map((ev, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-white border border-gray-100 hover:border-gray-200 transition-colors flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-gray-400 text-[11px]">
                      {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getEventBadge(ev.event_type)}`}>
                      {ev.event_type}
                    </span>
                    <span className="font-medium text-graphite-900">{ev.channel}</span>
                  </div>
                  <div className="text-gray-400 font-mono text-[11px] hidden sm:block">
                    {ev.page || ev.product_id || ev.campaign_id || '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="card-soft p-12 text-center text-xs text-gray-400">
          Enter a Customer ID above to inspect their structured journey timeline and touchpoint attributes.
        </div>
      )}
    </div>
  );
};
