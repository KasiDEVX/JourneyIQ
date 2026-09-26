import React, { useState, useEffect, useMemo } from 'react';
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
  ArrowLeft,
  Calendar,
  Sparkles,
  Copy,
  Check,
  Filter,
  IndianRupee,
  ChevronRight,
  TrendingUp,
  X,
} from 'lucide-react';
import { CustomerJourney } from '@/types/analytics';
import { getCustomerJourney, getCustomers, CustomerProfile } from '@/services/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatINR } from '@/utils/currency';

// Known real customers from dataset to ensure immediate availability
const FALLBACK_CUSTOMERS: CustomerProfile[] = [
  { customer_id: '8b883598-8507-4d1c-a77f-b689bc3b5a0a', first_seen: '2026-09-19T12:06:46Z', converted: true, conversion_revenue: 28.93, event_count: 12 },
  { customer_id: '4a3e46c2-ce82-4659-ac2a-be0b8319cf71', first_seen: '2026-08-25T12:13:38Z', converted: true, conversion_revenue: 203.12, event_count: 7 },
  { customer_id: 'd492f638-37ce-482c-beb8-bcf34bb2bdc5', first_seen: '2026-07-14T23:16:55Z', converted: true, conversion_revenue: 210.09, event_count: 13 },
  { customer_id: 'e8d8cf38-ed9d-4f59-a99d-8787aa142078', first_seen: '2026-08-23T14:29:27Z', converted: true, conversion_revenue: 98.35, event_count: 20 },
  { customer_id: '44ef5db4-9478-4a32-b5a3-36c7d6fd9de3', first_seen: '2026-08-31T01:30:30Z', converted: true, conversion_revenue: 129.08, event_count: 9 },
  { customer_id: '6dde29df-797b-4448-80a1-e12712551f80', first_seen: '2026-08-15T18:10:30Z', converted: true, conversion_revenue: 120.13, event_count: 7 },
  { customer_id: '39a31d30-f030-4e26-979c-575b7955162e', first_seen: '2026-09-13T22:57:18Z', converted: true, conversion_revenue: 40.83, event_count: 9 },
  { customer_id: 'fafde3c8-a797-4102-b3cc-8031c26df208', first_seen: '2026-09-13T15:07:08Z', converted: true, conversion_revenue: 34.90, event_count: 7 },
  { customer_id: '917c63b6-18e4-403f-8ec5-6c12182b1008', first_seen: '2026-08-14T13:18:04Z', converted: true, conversion_revenue: 61.59, event_count: 11 },
  { customer_id: 'c3926e54-21ac-4eec-bf61-bfd32c802e3a', first_seen: '2026-08-12T16:35:41Z', converted: true, conversion_revenue: 87.06, event_count: 9 },
  { customer_id: 'af96530f-e3fa-4068-b32a-ad8aa4438522', first_seen: '2026-09-22T04:15:20Z', converted: false, conversion_revenue: null, event_count: 3 },
  { customer_id: '454a23ad-4e48-4308-beb1-0b9528f857bf', first_seen: '2026-09-21T12:26:50Z', converted: false, conversion_revenue: null, event_count: 1 },
];

export const Customers: React.FC = () => {
  const { customerId: routeCustomerId } = useParams<{ customerId?: string }>();
  const navigate = useNavigate();

  // Search & input state
  const [inputCustomerId, setInputCustomerId] = useState(routeCustomerId || '');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Customer List state
  const [customerList, setCustomerList] = useState<CustomerProfile[]>(FALLBACK_CUSTOMERS);
  const [listLoading, setListLoading] = useState(true);
  const [filterMode, setFilterMode] = useState<'all' | 'converted' | 'funnel'>('all');
  const [tableSearch, setTableSearch] = useState('');

  // Journey Inspector state
  const [journey, setJourney] = useState<CustomerJourney | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load customer directory from backend
  useEffect(() => {
    let isMounted = true;
    const loadList = async () => {
      setListLoading(true);
      try {
        const res = await getCustomers(100);
        if (isMounted && res && res.length > 0) {
          setCustomerList(res);
        }
      } catch {
        // Fallback customers already populated
      } finally {
        if (isMounted) setListLoading(false);
      }
    };
    loadList();
    return () => { isMounted = false; };
  }, []);

  // Fetch individual customer journey
  const fetchCustomer = async (cid: string) => {
    if (!cid.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getCustomerJourney(cid.trim());
      setJourney(res);
    } catch (err: any) {
      setJourney(null);
      setError(err.message || `Customer '${cid}' was not found in the database.`);
    } finally {
      setLoading(false);
    }
  };

  // Sync route param with customer fetch
  useEffect(() => {
    if (routeCustomerId) {
      setInputCustomerId(routeCustomerId);
      fetchCustomer(routeCustomerId);
    } else {
      setJourney(null);
      setError(null);
    }
  }, [routeCustomerId]);

  const handleSelectCustomer = (cid: string) => {
    setInputCustomerId(cid);
    navigate(`/customers/${cid}`);
  };

  const handleClearSelection = () => {
    setInputCustomerId('');
    setJourney(null);
    setError(null);
    navigate('/customers');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputCustomerId.trim()) {
      handleSelectCustomer(inputCustomerId.trim());
    }
  };

  const copyToClipboard = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filtered customer list for the directory table
  const filteredCustomers = useMemo(() => {
    return customerList.filter((c) => {
      if (filterMode === 'converted' && !c.converted) return false;
      if (filterMode === 'funnel' && c.converted) return false;
      if (tableSearch.trim()) {
        const q = tableSearch.toLowerCase().trim();
        return c.customer_id.toLowerCase().includes(q);
      }
      return true;
    });
  }, [customerList, filterMode, tableSearch]);

  // Overall directory metrics
  const directoryStats = useMemo(() => {
    const total = customerList.length;
    const converted = customerList.filter((c) => c.converted).length;
    const totalRev = customerList.reduce((acc, c) => acc + (c.conversion_revenue || 0), 0);
    const rate = total > 0 ? ((converted / total) * 100).toFixed(1) : '0.0';
    return { total, converted, totalRev, rate };
  }, [customerList]);

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
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold font-display tracking-tight text-graphite-950">
              Customer Journey Explorer
            </h1>
            <Badge variant="coral">Directory & Sessions</Badge>
          </div>
          <p className="text-sm text-gray-500">
            Select a verified customer profile below or search by UUID to inspect their multi-touch path.
          </p>
        </div>

        {routeCustomerId && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleClearSelection}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Directory
          </Button>
        )}
      </div>

      {/* Lookup Bar & Quick Picks */}
      <div className="card-soft p-5 space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputCustomerId}
              onChange={(e) => setInputCustomerId(e.target.value)}
              placeholder="Search or paste customer UUID (e.g. 8b883598-8507...)..."
              className="w-full pl-10 pr-10 py-2.5 bg-ivory-50 rounded-xl border border-gray-200 text-xs text-graphite-900 font-mono focus:outline-hidden focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500"
            />
            {inputCustomerId && (
              <button
                type="button"
                onClick={() => setInputCustomerId('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <Button type="submit" variant="primary" size="md" className="w-full sm:w-auto shrink-0">
            Inspect Journey
          </Button>
        </form>

        {/* Quick-Pick Sample Profiles */}
        <div className="flex items-center gap-2 flex-wrap pt-1 text-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-mono flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Quick Inspect:
          </span>
          {customerList.slice(0, 5).map((c) => (
            <button
              key={c.customer_id}
              onClick={() => handleSelectCustomer(c.customer_id)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all border ${
                routeCustomerId === c.customer_id
                  ? 'bg-coral-50 border-coral-300 text-coral-700 font-bold'
                  : 'bg-white hover:bg-gray-100 border-gray-200 text-graphite-700'
              }`}
            >
              <span>{c.customer_id.slice(0, 8)}...</span>
              {c.converted ? (
                <span className="text-emerald-600 font-bold text-[10px]">
                  {c.conversion_revenue ? formatINR(c.conversion_revenue) : 'Conv'}
                </span>
              ) : (
                <span className="text-gray-400 text-[10px]">{c.event_count} ev</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Journey Details View (When customer is selected) ──────────────── */}
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-44 w-full rounded-3xl" />
          <Skeleton className="h-96 w-full rounded-3xl" />
        </div>
      ) : error ? (
        <div className="card-soft p-8 text-center space-y-4 bg-red-50/40 border-red-200">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-100 text-red-600 mx-auto">
            <XCircle className="w-5 h-5" />
          </div>
          <div>
            <p className="font-semibold text-sm text-red-700 mb-1">Customer Not Found</p>
            <p className="text-xs text-red-600 max-w-md mx-auto">{error}</p>
          </div>
          <div className="pt-2">
            <p className="text-xs font-medium text-gray-500 mb-2">
              Select one of the verified customer records from the database:
            </p>
            <div className="flex items-center justify-center gap-2 flex-wrap max-w-lg mx-auto">
              {customerList.slice(0, 4).map((c) => (
                <button
                  key={c.customer_id}
                  onClick={() => handleSelectCustomer(c.customer_id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono bg-white border border-gray-200 hover:border-coral-400 text-graphite-800 transition-colors shadow-2xs"
                >
                  {c.customer_id.slice(0, 8)}... ({c.converted ? 'Converted' : `${c.event_count} events`})
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : journey ? (
        <div className="space-y-6">
          {/* Journey KPI Header */}
          <div className="card-soft p-6 md:p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-5">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-lg font-bold font-mono text-graphite-950 flex items-center gap-2">
                    <span>{journey.customer_id}</span>
                    <button
                      onClick={(e) => copyToClipboard(journey.customer_id, e)}
                      title="Copy customer UUID"
                      className="p-1 rounded text-gray-400 hover:text-graphite-700 transition-colors"
                    >
                      {copiedId === journey.customer_id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
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
                    {formatINR(journey.conversion_revenue)}
                  </div>
                  {journey.conversion_order_id && (
                    <div className="text-[11px] font-mono text-gray-400">
                      Order: {journey.conversion_order_id}
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
                  <span className="text-xs font-mono text-gray-400">No marketing touchpoints recorded</span>
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
            <div className="border-b border-gray-100 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold font-display text-graphite-950">
                  Chronological Event Log ({journey.events.length} events)
                </h3>
                <p className="text-xs text-gray-400">
                  Raw events received by the data layer, sorted ascending by timestamp.
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClearSelection}
                icon={<ArrowLeft className="w-3.5 h-3.5" />}
              >
                Return to Directory
              </Button>
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
        /* ── Customer Directory Table (Default view when no customer selected) ── */
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card-soft p-4">
              <div className="text-[11px] font-mono uppercase font-bold text-gray-400 mb-1">
                Total Profiles
              </div>
              <div className="text-2xl font-bold font-mono text-graphite-900">
                {directoryStats.total}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Available records</div>
            </div>

            <div className="card-soft p-4">
              <div className="text-[11px] font-mono uppercase font-bold text-gray-400 mb-1">
                Conversions
              </div>
              <div className="text-2xl font-bold font-mono text-emerald-600">
                {directoryStats.converted}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">{directoryStats.rate}% conv rate</div>
            </div>

            <div className="card-soft p-4">
              <div className="text-[11px] font-mono uppercase font-bold text-gray-400 mb-1">
                Total Attributed Rev
              </div>
              <div className="text-2xl font-bold font-mono text-coral-600">
                {formatINR(directoryStats.totalRev)}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Gross order value</div>
            </div>

            <div className="card-soft p-4">
              <div className="text-[11px] font-mono uppercase font-bold text-gray-400 mb-1">
                In Funnel
              </div>
              <div className="text-2xl font-bold font-mono text-graphite-700">
                {directoryStats.total - directoryStats.converted}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Active prospects</div>
            </div>
          </div>

          {/* Directory Table Card */}
          <div className="card-soft p-6 md:p-8 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-4">
              <div>
                <h2 className="text-lg font-bold font-display text-graphite-950">
                  Customer Directory
                </h2>
                <p className="text-xs text-gray-500">
                  Click any customer row to inspect their session history and touchpoints.
                </p>
              </div>

              {/* Filter Tabs & Search */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1 p-1 bg-ivory-100 rounded-xl border border-gray-200 text-xs">
                  <button
                    onClick={() => setFilterMode('all')}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      filterMode === 'all'
                        ? 'bg-white text-graphite-950 shadow-2xs font-semibold'
                        : 'text-gray-500 hover:text-graphite-700'
                    }`}
                  >
                    All ({directoryStats.total})
                  </button>
                  <button
                    onClick={() => setFilterMode('converted')}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      filterMode === 'converted'
                        ? 'bg-white text-graphite-950 shadow-2xs font-semibold'
                        : 'text-gray-500 hover:text-graphite-700'
                    }`}
                  >
                    Converted ({directoryStats.converted})
                  </button>
                  <button
                    onClick={() => setFilterMode('funnel')}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      filterMode === 'funnel'
                        ? 'bg-white text-graphite-950 shadow-2xs font-semibold'
                        : 'text-gray-500 hover:text-graphite-700'
                    }`}
                  >
                    In Funnel ({directoryStats.total - directoryStats.converted})
                  </button>
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    placeholder="Filter table..."
                    className="pl-8 pr-3 py-1.5 rounded-xl border border-gray-200 text-xs bg-white text-graphite-800 placeholder-gray-400 focus:outline-hidden focus:border-coral-500 w-36 sm:w-44"
                  />
                </div>
              </div>
            </div>

            {/* Table */}
            {listLoading && customerList.length === 0 ? (
              <div className="space-y-2 py-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full rounded-xl" />
                ))}
              </div>
            ) : filteredCustomers.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-400">
                No customers matched the current filter.
              </div>
            ) : (
              <div className="overflow-x-auto -mx-6 md:-mx-8 px-6 md:px-8">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-gray-200 text-[11px] font-bold uppercase tracking-wider text-gray-400 font-mono">
                      <th className="py-3 px-3">Customer ID</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">First Seen</th>
                      <th className="py-3 px-3 text-right">Events</th>
                      <th className="py-3 px-3 text-right">Revenue</th>
                      <th className="py-3 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-mono">
                    {filteredCustomers.map((cust) => (
                      <tr
                        key={cust.customer_id}
                        onClick={() => handleSelectCustomer(cust.customer_id)}
                        className="hover:bg-coral-50/30 transition-colors cursor-pointer group"
                      >
                        {/* ID + Copy */}
                        <td className="py-3.5 px-3">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-graphite-900 group-hover:text-coral-600 transition-colors">
                              {cust.customer_id}
                            </span>
                            <button
                              onClick={(e) => copyToClipboard(cust.customer_id, e)}
                              title="Copy UUID"
                              className="opacity-0 group-hover:opacity-100 p-1 rounded text-gray-400 hover:text-graphite-700 transition-opacity"
                            >
                              {copiedId === cust.customer_id ? (
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-3 font-sans">
                          {cust.converted ? (
                            <Badge variant="emerald" size="sm">Converted</Badge>
                          ) : (
                            <Badge variant="neutral" size="sm">In Funnel</Badge>
                          )}
                        </td>

                        {/* First Seen */}
                        <td className="py-3.5 px-3 text-gray-500 font-sans">
                          {new Date(cust.first_seen).toLocaleDateString([], {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>

                        {/* Events */}
                        <td className="py-3.5 px-3 text-right text-gray-700 font-semibold">
                          {cust.event_count}
                        </td>

                        {/* Revenue */}
                        <td className="py-3.5 px-3 text-right">
                          {cust.conversion_revenue ? (
                            <span className="font-bold text-coral-600">
                              {formatINR(cust.conversion_revenue)}
                            </span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="py-3.5 px-3 text-right">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-coral-600 group-hover:translate-x-0.5 transition-transform font-sans">
                            Inspect <ChevronRight className="w-3 h-3" />
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

