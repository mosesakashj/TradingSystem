// Main Dashboard Page
import React, { useEffect, useState } from 'react';
import { MetricCard } from '../components/MetricCard';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import {
  CurrencyDollarIcon,
  ChartBarIcon,
  FireIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface DashboardStats {
  total_signals: number;
  total_trades: number;
  open_trades: number;
  total_pnl: number;
  win_rate: number;
  closed_trades: number;
  winning_trades: number;
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const { lastMessage: tradeMessage, isConnected: tradesConnected } = useWebSocket('trades');
  const { lastMessage: healthMessage } = useWebSocket('system_health');

  useEffect(() => {
    loadStats();
    loadEquityCurve();
  }, []);

  useEffect(() => {
    if (tradeMessage) {
      // Refresh stats when new trade comes in
      loadStats();
    }
  }, [tradeMessage]);

  const loadStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load stats:', error);
      setLoading(false);
    }
  };

  const loadEquityCurve = async () => {
    try {
      // This would be a dedicated endpoint in production
      const trades = await api.getTrades({ limit: 50 });
      
      // Generate cumulative P&L curve
      let cumulative = 0;
      const curve = trades.trades.map((trade: any, idx: number) => {
        cumulative += trade.net_pnl || 0;
        return {
          index: idx + 1,
          pnl: cumulative,
          timestamp: trade.timestamp,
        };
      });
      
      setEquityCurve(curve);
    } catch (error) {
      console.error('Failed to load equity curve:', error);
    }
  };

  const getTrendDirection = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Trading Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Real-time overview of your AI trading performance
          </p>
          
          {/* Connection Status */}
          <div className="flex items-center mt-4 space-x-4">
            <div className="flex items-center space-x-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  tradesConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              ></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {tradesConnected ? 'Live' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total P&L"
            value={`$${stats?.total_pnl.toFixed(2) || '0.00'}`}
            trend={getTrendDirection(stats?.total_pnl || 0)}
            trendValue={`${stats?.closed_trades || 0} trades`}
            icon={<CurrencyDollarIcon className="w-6 h-6 text-blue-600" />}
            loading={loading}
            valueColor={stats && stats.total_pnl > 0 ? 'green' : stats && stats.total_pnl < 0 ? 'red' : 'default'}
          />

          <MetricCard
            title="Win Rate"
            value={`${stats?.win_rate.toFixed(1) || '0.0'}%`}
            trendValue={`${stats?.winning_trades || 0}/${stats?.closed_trades || 0}`}
            icon={<ChartBarIcon className="w-6 h-6 text-green-600" />}
            loading={loading}
            valueColor={stats && stats.win_rate >= 50 ? 'green' : 'red'}
          />

          <MetricCard
            title="Open Positions"
            value={stats?.open_trades || 0}
            trendValue={`${stats?.total_trades || 0} total`}
            icon={<FireIcon className="w-6 h-6 text-orange-600" />}
            loading={loading}
          />

          <MetricCard
            title="Total Signals"
            value={stats?.total_signals || 0}
            icon={<ShieldCheckIcon className="w-6 h-6 text-purple-600" />}
            loading={loading}
          />
        </div>

        {/* Equity Curve Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700 mb-8">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Equity Curve
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityCurve}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="index"
                stroke="#9CA3AF"
                label={{ value: 'Trade #', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                stroke="#9CA3AF"
                label={{ value: 'Cumulative P&L ($)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="pnl"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                name="P&L"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Recent Signals */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Recent Activity
          </h2>
          
          {tradeMessage && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                    New {tradeMessage.data.type || 'Trade'} Update
                  </p>
                  <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                    {new Date(tradeMessage.timestamp).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-blue-900 dark:text-blue-100">
                    {tradeMessage.data.symbol || 'N/A'}
                  </p>
                  <p className="text-xs text-blue-700 dark:text-blue-300">
                    {tradeMessage.data.direction || 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          )}

          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Live updates will appear here...
          </p>
        </div>
      </div>
    </div>
  );
}
