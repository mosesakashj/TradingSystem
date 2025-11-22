import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Activity, AlertCircle, CheckCircle, XCircle, Settings, Clock, Wifi, WifiOff } from 'lucide-react'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

// Timezone data
const TIMEZONES = [
  { value: 'UTC', label: 'UTC'},
  { value: 'America/New_York', label: 'New York (EST/EDT)' },
  { value: 'America/Chicago', label: 'Chicago (CST/CDT)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' }
]

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [trades, setTrades] = useState([])
  const [signals, setSignals] = useState([])
  const [systemStatus, setSystemStatus] = useState(null)
  const [settings, setSettings] = useState(null)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [showSettings, setShowSettings] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
    loadSettings()
    
    const dataInterval = setInterval(loadDashboardData, 5000)
    const statusInterval = setInterval(loadSystemStatus, 10000)
    const clockInterval = setInterval(() => setCurrentTime(new Date()), 1000)
    
    return () => {
      clearInterval(dataInterval)
      clearInterval(statusInterval)
      clearInterval(clockInterval)
    }
  }, [])

  const loadSettings = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/settings`).catch(() => ({ 
        data: { timezone: 'UTC', show_sessions: true, mt5_enabled: false, theme: 'dark' } 
      }))
      setSettings(res.data)
    } catch (error) {
      setSettings({ timezone: 'UTC', show_sessions: true, mt5_enabled: false, theme: 'dark' })
    }
  }

  const loadSystemStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/status`)
      setSystemStatus(res.data)
    } catch (error) {
      setSystemStatus({ status: 'offline' })
    }
  }

  const loadDashboardData = async () => {
    try {
      const [statsRes, tradesRes, signalsRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/stats`).catch(() => ({ data: getMockStats() })),
        axios.get(`${API_URL}/trades?limit=20`).catch(() => ({ data: { trades: getMockTrades() } })),
        axios.get(`${API_URL}/signals?limit=10`).catch(() => ({ data: { signals: getMockSignals() } })),
        axios.get(`${API_URL}/api/status`).catch(() => ({ data: { status: 'offline' } }))
      ])
      
      setStats(statsRes.data)
      setTrades(tradesRes.data.trades || [])
      setSignals(signalsRes.data.signals || [])
      setSystemStatus(statusRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error loading dashboard:', error)
      setStats(getMockStats())
      setTrades(getMockTrades())
      setSignals(getMockSignals())
      setSystemStatus({ status: 'offline' })
      setLoading(false)
    }
  }

  const getMockStats = () => ({
    total_signals: 156,
    total_trades: 89,
    open_trades: 3,
    total_pnl: 1247.50,
    win_rate: 64.2,
    closed_trades: 86,
    winning_trades: 55
  })

  const getMockTrades = () => Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    symbol: ['EURUSD', 'GBPUSD', 'XAUUSD', 'BTCUSD'][Math.floor(Math.random() * 4)],
    direction: Math.random() > 0.5 ? 'buy' : 'sell',
    entry_price_filled: 1.0850 + (Math.random() - 0.5) * 0.01,
    net_pnl: (Math.random() - 0.4) * 500,
    timestamp: new Date(Date.now() - i * 3600000).toISOString()
  }))

  const getMockSignals = () => Array.from({ length: 10 }, (_, i) => ({
    id: i + 1,
    symbol: ['EURUSD', 'GBPUSD'][Math.floor(Math.random() * 2)],
    direction: Math.random() > 0.5 ? 'buy' : 'sell',
    status: ['received', 'executed', 'rejected'][Math.floor(Math.random() * 3)],
    entry_price: 1.0850 + (Math.random() - 0.5) * 0.01,
    take_profit: 1.0850 + Math.random() * 0.01,
    timestamp: new Date(Date.now() - i * 1800000).toISOString()
  }))

  // Fetch live prices from backend API
  const [livePrices, setLivePrices] = useState([])

  useEffect(() => {
    loadLivePrices()
    const priceInterval = setInterval(loadLivePrices, 5000) // Update every 5s
    return () => clearInterval(priceInterval)
  }, [])

  const loadLivePrices = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/prices/live`)
      if (res.data.success && res.data.prices) {
        setLivePrices(res.data.prices)
      } else {
        // If API returns error, keep current prices or show empty
        console.warn('API returned no prices:', res.data)
      }
    } catch (error) {
      console.error('Failed to load live prices:', error)
      // Keep showing last known prices, don't clear them
    }
  }

  // Check if market is open
  const isMarketOpen = () => {
    const day = currentTime.getUTCDay()
    const hour = currentTime.getUTCHours()
    
    // Forex: Closed Saturday and Sunday
    if (day === 6 || day === 0) return false
    
    // Closed Friday 10 PM UTC to Sunday 10 PM UTC
    if (day === 5 && hour >= 22) return false
    
    return true
  }

  // Generate equity curve from trades
  const equityCurve = trades.reduce((acc, trade, idx) => {
    const prev = acc[idx - 1] || { equity: 10000 }
    acc.push({
      index: idx + 1,
      equity: prev.equity + (trade.net_pnl || 0),
      pnl: trade.net_pnl || 0,
      timestamp: trade.timestamp
    })
    return acc
  }, []).reverse()

  // Win/Loss pie data
  const winLossData = stats ? [
    { name: 'Wins', value: stats.winning_trades, color: '#10b981' },
    { name: 'Losses', value: stats.closed_trades - stats.winning_trades, color: '#ef4444' }
  ] : []

  // Format time in user timezone
  const formatTime = () => {
    try {
      const tz = settings?.timezone || 'UTC'
      return currentTime.toLocaleTimeString('en-US', { 
        timeZone: tz,
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    } catch {
      return currentTime.toUTCString()
    }
  }

  const formatDate = () => {
    try {
      const tz = settings?.timezone || 'UTC'
      return currentTime.toLocaleDateString('en-US', { 
        timeZone: tz,
        weekday: 'short',
        month: 'short',
        day: 'numeric'
      })
    } catch {
      return currentTime.toDateString()
    }
  }

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', backgroundColor: '#0f172a', minHeight: '100vh', color: '#e2e8f0' }}>Loading dashboard...</div>
  }

  const apiOnline = systemStatus?.status === 'online'

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: '#e2e8f0', padding: '24px' }}>
      {/* Header with Clock and Status */}
      <div style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: '#fff', marginBottom: '8px' }}>
            🚀 AI Trading Dashboard
          </h1>
          <p style={{ color: '#94a3b8' }}>Real-time monitoring and analytics</p>
        </div>
        
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          {/* Live Clock */}
          <div style={{ 
            padding: '12px 20px', 
            backgroundColor: '#1e293b', 
            borderRadius: '8px',
            border: '1px solid #334155',
            textAlign: 'right'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Clock size={16} color="#64748b" />
              <span style={{ fontSize: '12px', color: '#64748b' }}>{settings?.timezone || 'UTC'}</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#fff' }}>{formatTime()}</div>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>{formatDate()}</div>
          </div>

          {/* API Status */}
          <div style={{ 
            padding: '12px 20px', 
            backgroundColor: '#1e293b', 
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {apiOnline ? <Wifi size={20} color="#10b981" /> : <WifiOff size={20} color="#ef4444" />}
              <div>
                <div style={{ fontSize: '12px', color: '#64748b' }}>API Status</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: '600',
                  color: apiOnline ? '#10b981' : '#ef4444'
                }}>
                  {apiOnline ? 'Online' : 'Offline'}
                </div>
              </div>
            </div>
          </div>

          {/* Settings Button */}
          <button
            onClick={() => setShowSettings(true)}
            style={{
              padding: '12px 16px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Settings size={20} />
            Settings
          </button>
        </div>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <MetricCard 
          title="Total P&L" 
          value={`$${stats.total_pnl.toFixed(2)}`}
          trend={stats.total_pnl > 0 ? 'up' : 'down'}
          icon={<DollarSign size={24} color="#10b981" />}
          color="#10b981"
        />
        <MetricCard 
          title="Win Rate" 
          value={`${stats.win_rate.toFixed(1)}%`}
          subtitle={`${stats.winning_trades}/${stats.closed_trades}`}
          icon={<TrendingUp size={24} color="#3b82f6" />}
          color="#3b82f6"
        />
        <MetricCard 
          title="Open Trades" 
          value={stats.open_trades}
          subtitle={`${stats.total_trades} total`}
          icon={<Activity size={24} color="#f59e0b" />}
          color="#f59e0b"
        />
        <MetricCard 
          title="Total Signals" 
          value={stats.total_signals}
          subtitle="Received"
          icon={<CheckCircle size={24} color="#8b5cf6" />}
          color="#8b5cf6"
        />
      </div>

      {/* Live Price Ticker */}
      <div style={{ marginBottom: '32px' }}>
        <ChartCard title="💹 Live Market Prices & Order Flow">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {livePrices.map((pair) => (
              <PriceCard key={pair.symbol} pair={pair} />
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Trading Sessions Chart */}
      <div style={{ marginBottom: '32px' }}>
        <TradingSessionsChart userTimezone={settings?.timezone} />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        {/* Equity Curve with Entry/Target Points */}
        <ChartCard title="📈 Equity Curve & Signals">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="index" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Area type="monotone" dataKey="equity" stroke="#10b981" fillOpacity={1} fill="url(#colorEquity)" />
              {/* Entry/Target example markers */}
              {signals.slice(0, 3).map((signal, i) => (
                <React.Fragment key={i}>
                  <ReferenceLine y={signal.entry_price * 10000} stroke="#3b82f6" strokeDasharray="3 3" label={{ value: 'Entry', fill: '#3b82f6', fontSize: 10 }} />
                  {signal.take_profit && (
                    <ReferenceLine y={signal.take_profit * 10000} stroke="#10b981" strokeDasharray="3 3" label={{ value: 'Target', fill: '#10b981', fontSize: 10 }} />
                  )}
                </React.Fragment>
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Win/Loss Distribution */}
        <ChartCard title="🎯 Win/Loss Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={winLossData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {winLossData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Recent Trades & Signals */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '20px' }}>
        <TableCard title="💼 Recent Trades">
          <TradesTable trades={trades.slice(0, 10)} />
        </TableCard>

        <TableCard title="📡 Recent Signals">
          <SignalsTable signals={signals} />
        </TableCard>
      </div>

      {/* Footer */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#1e293b', borderRadius: '12px', textAlign: 'center' }}>
        <p style={{ color: '#94a3b8', marginBottom: '12px' }}>
          <strong>API Documentation:</strong> <a href="http://localhost:8000/docs" target="_blank" style={{ color: '#3b82f6' }}>http://localhost:8000/docs</a>
        </p>
        <p style={{ fontSize: '14px', color: '#64748b' }}>
          Dashboard auto-refreshes every 5 seconds • Market: {isMarketOpen() ? '🟢 Open' : '🔴 Closed'}
        </p>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal 
          settings={settings}
          onClose={() => setShowSettings(false)}
          onSave={(newSettings) => {
            setSettings(newSettings)
            setShowSettings(false)
            loadSettings()
          }}
        />
      )}
    </div>
  )
}

// Trading Sessions Chart Component
function TradingSessionsChart({ userTimezone = 'UTC' }) {
  const [currentHour, setCurrentHour] = useState(new Date().getUTCHours())

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentHour(new Date().getUTCHours())
    }, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  // Session timings in UTC
  const sessions = [
    {
      name: 'Asia/Tokyo',
      start: 0,
      end: 9,
      color: '#f59e0b', // Amber
      bgColor: 'rgba(245, 158, 11, 0.2)'
    },
    {
      name: 'London',
      start: 8,
      end: 16,
      color: '#3b82f6', // Blue
      bgColor: 'rgba(59, 130, 246, 0.2)'
    },
    {
      name: 'New York',
      start: 13,
      end: 22,
      color: '#10b981', // Green
      bgColor: 'rgba(16, 185, 129, 0.2)'
    }
  ]

  // Calculate overlaps
  const overlaps = [
    {
      name: 'London + New York',
      start: 13,
      end: 16,
      label: 'Peak Liquidity',
      color: 'rgba(139, 92, 246, 0.3)' // Purple
    },
    {
      name: 'Asia + London',
      start: 8,
      end: 9,
      label: 'Moderate Activity',
      color: 'rgba(236, 72, 153, 0.3)' // Pink
    }
  ]

  // Generate 24 hours
  const hours = Array.from({ length: 24 }, (_, i) => i)

  // Determine which sessions are currently active
  const getActiveSessions = () => {
    const active = []
    sessions.forEach(session => {
      if (currentHour >= session.start && currentHour < session.end) {
        active.push(session)
      }
    })
    return active
  }

  const activeSessions = getActiveSessions()

  return (
    <div style={{ padding: '24px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#fff', margin: 0 }}>
          🌍 Trading Sessions & Overlap (UTC)
        </h3>
        
        {/* Active Session Indicator */}
        <div style={{
          padding: '12px 20px',
          backgroundColor: activeSessions.length > 0 ? '#0f172a' : '#1e293b',
          borderRadius: '8px',
          border: activeSessions.length > 0 ? `2px solid ${activeSessions[0]?.color}` : '1px solid #334155',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          {activeSessions.length > 0 ? (
            <>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: activeSessions[0].color,
                animation: 'pulse 2s infinite',
                boxShadow: `0 0 10px ${activeSessions[0].color}`
              }} />
              <div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>ACTIVE NOW</div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: activeSessions[0].color }}>
                  {activeSessions.map(s => s.name).join(' + ')}
                </div>
              </div>
            </>
          ) : (
            <>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#64748b'
              }} />
              <div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>MARKET STATUS</div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#94a3b8' }}>
                  Between Sessions
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Add pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {sessions.map(session => (
          <div key={session.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '2px',
              backgroundColor: session.color
            }} />
            <span style={{ fontSize: '13px', color: '#94a3b8' }}>
              {session.name} ({session.start}:00-{session.end}:00)
            </span>
          </div>
        ))}
      </div>

      {/* Timeline Chart */}
      <div style={{ position: 'relative', marginTop: '30px' }}>
        {/* Hour markers */}
        <div style={{ display: 'flex', marginBottom: '8px' }}>
          {hours.map(hour => (
            <div
              key={hour}
              style={{
                flex: 1,
                textAlign: 'center',
                fontSize: '11px',
                color: hour === currentHour ? '#10b981' : '#64748b',
                fontWeight: hour === currentHour ? 'bold' : 'normal'
              }}
            >
              {hour === currentHour && '▼'}
              {hour === 0 || hour % 3 === 0 ? `${hour}h` : ''}
            </div>
          ))}
        </div>

        {/* Session rows */}
        <div style={{ position: 'relative' }}>
          {sessions.map((session, idx) => (
            <div key={session.name} style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                {session.name}
              </div>
              <div style={{ position: 'relative', height: '32px', backgroundColor: '#0f172a', borderRadius: '6px', overflow: 'hidden' }}>
                {/* Session bar */}
                <div style={{
                  position: 'absolute',
                  left: `${(session.start / 24) * 100}%`,
                  width: `${((session.end - session.start) / 24) * 100}%`,
                  height: '100%',
                  backgroundColor: session.bgColor,
                  border: `2px solid ${session.color}`,
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: session.color,
                  fontSize: '11px',
                  fontWeight: '600'
                }}>
                  {session.end - session.start} hrs
                </div>

                {/* Current time marker */}
                {currentHour >= session.start && currentHour < session.end && (
                  <div style={{
                    position: 'absolute',
                    left: `${(currentHour / 24) * 100}%`,
                    width: '2px',
                    height: '100%',
                    backgroundColor: '#10b981'
                  }} />
                )}
              </div>
            </div>
          ))}

          {/* Overlap visualization */}
          <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #334155' }}>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '12px', fontWeight: '600' }}>
              📊 Session Overlaps (High Liquidity)
            </div>
            <div style={{ position: 'relative', height: '40px', backgroundColor: '#0f172a', borderRadius: '6px', overflow: 'hidden' }}>
              {overlaps.map(overlap => (
                <div
                  key={overlap.name}
                  style={{
                    position: 'absolute',
                    left: `${(overlap.start / 24) * 100}%`,
                    width: `${((overlap.end - overlap.start) / 24) * 100}%`,
                    height: '100%',
                    backgroundColor: overlap.color,
                    border: '2px solid rgba(139, 92, 246, 0.6)',
                    borderRadius: '4px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '4px'
                  }}
                >
                  <div style={{ fontSize: '10px', color: '#fff', fontWeight: '600' }}>
                    {overlap.name}
                  </div>
                  <div style={{ fontSize: '9px', color: '#e2e8f0' }}>
                    {overlap.start}:00-{overlap.end}:00
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div style={{
        marginTop: '20px',
        padding: '12px',
        backgroundColor: '#0f172a',
        borderRadius: '8px',
        border: '1px solid #334155'
      }}>
        <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.6' }}>
          <strong style={{ color: '#fff' }}>💡 Trading Tips:</strong><br />
          • <strong style={{ color: '#8b5cf6' }}>London + NY Overlap (13:00-16:00 UTC)</strong> = Highest liquidity & volatility<br />
          • <strong style={{ color: '#ec4899' }}>Asia + London Overlap (08:00-09:00 UTC)</strong> = Moderate activity<br />
          • Current time: <strong style={{ color: '#10b981' }}>{currentHour}:00 UTC</strong>
        </div>
      </div>
    </div>
  )
}

// Component implementations...
function PriceCard({ pair }) {
  // Format price with proper decimals
  const formatPrice = (price) => {
    if (!price) return '-'
    const decimals = pair.symbol?.includes('JPY') ? 2 : (pair.symbol?.includes('BTC') || pair.symbol?.includes('ETH')) ? 2 : 4
    return typeof price === 'number' ? price.toFixed(decimals) : price
  }

  return (
    <div style={{
      padding: '16px',
      backgroundColor: '#0f172a',
      borderRadius: '8px',
      border: `1px solid ${pair.marketOpen ? '#334155' : '#7f1d1d'}`,
      position: 'relative'
    }}>
      {!pair.marketOpen && (
        <div style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          padding: '4px 8px',
          backgroundColor: '#7f1d1d',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: '600',
          color: '#fca5a5'
        }}>
          CLOSED
        </div>
      )}
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: '600', color: '#fff' }}>{pair.symbol}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{pair.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#fff' }}>{formatPrice(pair.price)}</div>
          <div style={{
            fontSize: '12px',
            color: (pair.change || 0) >= 0 ? '#10b981' : '#ef4444',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            marginTop: '2px'
          }}>
            {(pair.change || 0) >= 0 ? '▲' : '▼'} {Math.abs(pair.change || 0).toFixed(2)}%
          </div>
        </div>
      </div>

      {pair.marketOpen && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}>
            <span>Buy {pair.buyPercent}%</span>
            <span>Sell {pair.sellPercent}%</span>
          </div>
          <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{
              width: `${pair.buyPercent}%`,
              backgroundColor: '#10b981',
              transition: 'width 0.3s ease'
            }} />
            <div style={{
              width: `${pair.sellPercent}%`,
              backgroundColor: '#ef4444',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{
            marginTop: '8px',
            fontSize: '11px',
            color: '#64748b',
            textAlign: 'center'
          }}>
            Sentiment: <span style={{
              color: pair.buyPercent > 60 ? '#10b981' : pair.sellPercent > 60 ? '#ef4444' : '#f59e0b',
              fontWeight: '600'
            }}>
              {pair.buyPercent > 60 ? 'Bullish' : pair.sellPercent > 60 ? 'Bearish' : 'Neutral'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function TradesTable({ trades }) {
  return (
    <table style={{ width: '100%', fontSize: '14px' }}>
      <thead style={{ borderBottom: '1px solid #334155' }}>
        <tr>
          <th style={{ padding: '12px 8px', textAlign: 'left' }}>Symbol</th>
          <th style={{ padding: '12px 8px', textAlign: 'left' }}>Type</th>
          <th style={{ padding: '12px 8px', textAlign: 'right' }}>Price</th>
          <th style={{ padding: '12px 8px', textAlign: 'right' }}>P&L</th>
        </tr>
      </thead>
      <tbody>
        {trades.map((trade) => (
          <tr key={trade.id} style={{ borderBottom: '1px solid #1e293b' }}>
            <td style={{ padding: '12px 8px', fontWeight: '600' }}>{trade.symbol}</td>
            <td style={{ padding: '12px 8px' }}>
              <span style={{
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: trade.direction === 'buy' ? '#1e40af' : '#991b1b',
                color: '#fff',
                fontSize: '12px'
              }}>
                {trade.direction.toUpperCase()}
              </span>
            </td>
            <td style={{ padding: '12px 8px', textAlign: 'right', color: '#94a3b8' }}>
              {trade.entry_price_filled?.toFixed(4) || '-'}
            </td>
            <td style={{ 
              padding: '12px 8px', 
              textAlign: 'right',
              color: trade.net_pnl >= 0 ? '#10b981' : '#ef4444',
              fontWeight: '600'
            }}>
              ${trade.net_pnl?.toFixed(2) || '0.00'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function SignalsTable({ signals }) {
  return (
    <table style={{ width: '100%', fontSize: '14px' }}>
      <thead style={{ borderBottom: '1px solid #334155' }}>
        <tr>
          <th style={{ padding: '12px 8px', textAlign: 'left' }}>Symbol</th>
          <th style={{ padding: '12px 8px', textAlign: 'left' }}>Type</th>
          <th style={{ padding: '12px 8px', textAlign: 'left' }}>Status</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((signal) => (
          <tr key={signal.id} style={{ borderBottom: '1px solid #1e293b' }}>
            <td style={{ padding: '12px 8px', fontWeight: '600' }}>{signal.symbol}</td>
            <td style={{ padding: '12px 8px' }}>
              <span style={{
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: signal.direction === 'buy' ? '#1e40af' : '#991b1b',
                color: '#fff',
                fontSize: '12px'
              }}>
                {signal.direction.toUpperCase()}
              </span>
            </td>
            <td style={{ padding: '12px 8px' }}>
              {signal.status === 'executed' && <CheckCircle size={16} color="#10b981" style={{ display: 'inline', marginRight: '8px' }} />}
              {signal.status === 'rejected' && <XCircle size={16} color="#ef4444" style={{ display: 'inline', marginRight: '8px' }} />}
              {signal.status === 'received' && <AlertCircle size={16} color="#f59e0b" style={{ display: 'inline', marginRight: '8px' }} />}
              <span>{signal.status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function SettingsModal({ settings, onClose, onSave }) {
  const [formData, setFormData] = useState(settings || {})
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await axios.put('http://localhost:8000/api/settings', formData)
      onSave(formData)
    } catch (error) {
      alert('Failed to save settings')
    }
    setSaving(false)
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: '#1e293b',
        borderRadius: '12px',
        padding: '32px',
        maxWidth: '600px',
        width: '90%',
        maxHeight: '90vh',
        overflow: 'auto'
      }}>
        <h2 style={{ fontSize: '24px', marginBottom: '24px', color: '#fff' }}>⚙️ Settings</h2>

        {/* Timezone */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#94a3b8', fontSize: '14px' }}>
            Timezone
          </label>
          <select
            value={formData.timezone || 'UTC'}
            onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: '14px'
            }}
          >
            {TIMEZONES.map(tz => (
              <option key={tz.value} value={tz.value}>{tz.label}</option>
            ))}
          </select>
        </div>

        {/* MT5 Configuration */}
        <h3 style={{ fontSize: '18px', marginBottom: '16px', color: '#fff', borderTop: '1px solid #334155', paddingTop: '24px' }}>
          MT5 Configuration
        </h3>
        
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#94a3b8', fontSize: '14px' }}>
            MT5 Login
          </label>
          <input
            type="text"
            value={formData.mt5_login || ''}
            onChange={(e) => setFormData({ ...formData, mt5_login: e.target.value })}
            placeholder="Enter MT5 account number"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: '14px'
            }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#94a3b8', fontSize: '14px' }}>
            MT5 Password
          </label>
          <input
            type="password"
            value={formData.mt5_password || ''}
            onChange={(e) => setFormData({ ...formData, mt5_password: e.target.value })}
            placeholder="Enter MT5 password"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: '14px'
            }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: '#94a3b8', fontSize: '14px' }}>
            MT5 Server
          </label>
          <input
            type="text"
            value={formData.mt5_server || ''}
            onChange={(e) => setFormData({ ...formData, mt5_server: e.target.value })}
            placeholder="e.g., Exness-MT5Demo"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: '14px'
            }}
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={formData.mt5_enabled || false}
              onChange={(e) => setFormData({ ...formData, mt5_enabled: e.target.checked })}
              style={{ width: '18px', height: '18px' }}
            />
            <span style={{ color: '#e2e8f0', fontSize: '14px' }}>Enable MT5 Integration</span>
          </label>
        </div>

        {/* Display Preferences */}
        <h3 style={{ fontSize: '18px', marginBottom: '16px', color: '#fff', borderTop: '1px solid #334155', paddingTop: '24px' }}>
          Display Preferences
        </h3>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={formData.show_sessions !== false}
              onChange={(e) => setFormData({ ...formData, show_sessions: e.target.checked })}
              style={{ width: '18px', height: '18px' }}
            />
            <span style={{ color: '#e2e8f0', fontSize: '14px' }}>Show Trading Sessions (NY/London/Asia)</span>
          </label>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '32px' }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              flex: 1,
              padding: '12px 24px',
              backgroundColor: '#3b82f6',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.5 : 1
            }}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '12px 24px',
              backgroundColor: '#374151',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

// Reusable Components
function MetricCard({ title, value, subtitle, trend, icon, color }) {
  return (
    <div style={{
      padding: '24px',
      backgroundColor: '#1e293b',
      borderRadius: '12px',
      border: '1px solid #334155'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '16px' }}>
        <span style={{ color: '#94a3b8', fontSize: '14px' }}>{title}</span>
        {icon}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 'bold', color: color || '#fff', marginBottom: '4px' }}>
        {value}
      </div>
      {subtitle && <div style={{ fontSize: '14px', color: '#64748b' }}>{subtitle}</div>}
      {trend && (
        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', fontSize: '14px', color: trend === 'up' ? '#10b981' : '#ef4444' }}>
          {trend === 'up' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          <span style={{ marginLeft: '4px' }}>{trend === 'up' ? 'Profit' : 'Loss'}</span>
        </div>
      )}
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <div style={{
      padding: '24px',
      backgroundColor: '#1e293b',
      borderRadius: '12px',
      border: '1px solid #334155'
    }}>
      <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', color: '#fff' }}>{title}</h3>
      {children}
    </div>
  )
}

function TableCard({ title, children }) {
  return (
    <div style={{
      padding: '24px',
      backgroundColor: '#1e293b',
      borderRadius: '12px',
      border: '1px solid #334155'
    }}>
      <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', color: '#fff' }}>{title}</h3>
      {children}
    </div>
  )
}

// Render
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Dashboard />
  </React.StrictMode>
)
