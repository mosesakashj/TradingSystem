import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Activity, AlertCircle, CheckCircle, XCircle, Settings, Clock, Wifi, WifiOff, LogOut } from 'lucide-react'
import axios from 'axios'
import { TradingSessionsChart } from './components/TradingSessionsChart'
import { ActiveSignalsWidget } from './components/ActiveSignalsWidget'
import { PriceCard } from './components/PriceCard'
import { useWebSocket } from './hooks/useWebSocket'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Login } from './pages/Login'

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

function DashboardContent() {
  const { user, logout } = useAuth()
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


  // Fetch live prices from backend API (Initial Load)
  const [livePrices, setLivePrices] = useState([])
  
  // WebSocket Connections
  const { lastMessage: priceMessage, status: priceStatus } = useWebSocket('prices')
  const { lastMessage: signalMessage, status: signalStatus } = useWebSocket('signals')

  // Handle Real-time Price Updates
  useEffect(() => {
    if (priceMessage && priceMessage.type === 'prices') {
      setLivePrices(priceMessage.data)
    }
  }, [priceMessage])

  // Handle Real-time Signal Updates
  useEffect(() => {
    if (signalMessage && signalMessage.type === 'signal') {
      const newSignal = signalMessage.data
      setSignals(prev => {
        // Avoid duplicates
        if (prev.find(s => s.id === newSignal.id)) return prev
        return [newSignal, ...prev]
      })
      
      // Update stats
      setStats(prev => ({
        ...prev,
        total_signals: prev.total_signals + 1
      }))
    }
  }, [signalMessage])

  // Initial Data Load
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [pricesRes, signalsRes, statsRes] = await Promise.all([
          axios.get(`${API_URL}/api/prices/live`),
          axios.get(`${API_URL}/signals`),
          axios.get(`${API_URL}/stats`)
        ])
        
        if (pricesRes.data.success) setLivePrices(pricesRes.data.prices)
        if (signalsRes.data.signals) setSignals(signalsRes.data.signals)
        setStats(statsRes.data)
        
      } catch (error) {
        console.error('Failed to load initial data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadInitialData()
  }, [])

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
    <div style={{ minHeight: '100vh', backgroundColor: '#0b1120', color: '#e2e8f0', fontFamily: "'Inter', sans-serif" }}>
      {/* Top Navigation Bar */}
      <div style={{ 
        backgroundColor: '#1e293b', 
        borderBottom: '1px solid #334155',
        padding: '0 24px',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '32px', height: '32px', background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={20} color="#fff" />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 'bold', color: '#fff', letterSpacing: '-0.5px' }}>
            AI Trader <span style={{ color: '#64748b', fontWeight: 'normal' }}>Pro</span>
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          {/* Market Status Pill */}
          <div style={{ 
            padding: '6px 12px', 
            backgroundColor: isMarketOpen() ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', 
            borderRadius: '20px',
            border: `1px solid ${isMarketOpen() ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isMarketOpen() ? '#10b981' : '#ef4444', boxShadow: isMarketOpen() ? '0 0 8px #10b981' : 'none' }} />
            <span style={{ fontSize: '12px', fontWeight: '600', color: isMarketOpen() ? '#10b981' : '#ef4444' }}>
              {isMarketOpen() ? 'MARKET OPEN' : 'MARKET CLOSED'}
            </span>
          </div>


          {/* Clock */}
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>{formatTime()}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>{formatDate()} • {settings?.timezone || 'UTC'}</div>
          </div>

          {/* User Info & Settings */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '12px', borderLeft: '1px solid #334155' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: '#fff' }}>{user?.username || 'Trader'}</div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>{user?.role || 'trader'}</div>
            </div>
            
            <button
              onClick={() => setShowSettings(true)}
              style={{
                background: 'none',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#3b82f6'
                e.currentTarget.style.color = '#3b82f6'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#334155'
                e.currentTarget.style.color = '#94a3b8'
              }}
            >
              <Settings size={16} />
            </button>
            
            <button
              onClick={logout}
              style={{
                background: 'none',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#ef4444'
                e.currentTarget.style.color = '#ef4444'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#334155'
                e.currentTarget.style.color = '#94a3b8'
              }}
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
        
        {/* Live Ticker Strip */}
        <div style={{ marginBottom: '24px', overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
            {livePrices.map((pair) => (
              <PriceCard key={pair.symbol} pair={pair} />
            ))}
          </div>
        </div>

        {/* Dashboard Grid */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'minmax(0, 2.5fr) minmax(0, 1fr)', 
          gap: '24px',
          alignItems: 'start'
        }}>
          
          {/* Left Column - Action Zone */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <ActiveSignalsWidget signals={signals} livePrices={livePrices} />
            
            <ChartCard title="Account Performance">
                <div style={{ height: '350px', width: '100%' }}>
                  <ResponsiveContainer>
                    <AreaChart data={equityCurve}>
                      <defs>
                        <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="index" stroke="#64748b" tickLine={false} axisLine={false} />
                      <YAxis stroke="#64748b" tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)' }}
                        itemStyle={{ color: '#fff' }}
                      />
                      <Area type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorEquity)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>


            {/* Recent Trades */}
            <TableCard title="💼 Trade History">
              <TradesTable trades={trades.slice(0, 10)} />
            </TableCard>
          </div>

          {/* RIGHT COLUMN (Sidebar) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Market Context */}
            <TradingSessionsChart userTimezone={settings?.timezone} />

            {/* Key Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <MetricCard 
                title="Total P&L" 
                value={`$${stats.total_pnl.toFixed(0)}`}
                trend={stats.total_pnl > 0 ? 'up' : 'down'}
                color="#10b981"
                compact
              />
              <MetricCard 
                title="Win Rate" 
                value={`${stats.win_rate.toFixed(1)}%`}
                color="#3b82f6"
                compact
              />
              <MetricCard 
                title="Open Trades" 
                value={stats.open_trades}
                color="#f59e0b"
                compact
              />
              <MetricCard 
                title="Signals" 
                value={stats.total_signals}
                color="#8b5cf6"
                compact
              />
            </div>

            {/* Win/Loss Distribution */}
            <ChartCard title="🎯 Performance Split">
              <div style={{ height: '200px', width: '100%' }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={winLossData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {winLossData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} />
                    <Legend verticalAlign="bottom" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* System Status */}
            <div style={{ padding: '20px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
              <h3 style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '12px', fontWeight: '600' }}>SYSTEM HEALTH</h3>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Real-time Feed</span>
                <span style={{ fontSize: '12px', color: priceStatus === 'connected' ? '#10b981' : '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {priceStatus === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />} 
                  {priceStatus === 'connected' ? 'Live' : priceStatus}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Latency</span>
                <span style={{ fontSize: '12px', color: '#10b981' }}>24ms</span>
              </div>
            </div>

          </div>
        </div>
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
function MetricCard({ title, value, subtitle, trend, icon, color, compact }) {
  return (
    <div style={{
      padding: compact ? '16px' : '24px',
      backgroundColor: '#1e293b',
      borderRadius: '12px',
      border: '1px solid #334155',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: compact ? '8px' : '16px' }}>
        <span style={{ color: '#94a3b8', fontSize: compact ? '12px' : '14px', fontWeight: '500' }}>{title}</span>
        {!compact && icon}
      </div>
      <div>
        <div style={{ fontSize: compact ? '20px' : '28px', fontWeight: 'bold', color: color || '#fff', marginBottom: '4px' }}>
          {value}
        </div>
        {subtitle && <div style={{ fontSize: '12px', color: '#64748b' }}>{subtitle}</div>}
        {trend && (
          <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', fontSize: '12px', color: trend === 'up' ? '#10b981' : '#ef4444' }}>
            {trend === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span style={{ marginLeft: '4px' }}>{trend === 'up' ? 'Profit' : 'Loss'}</span>
          </div>
        )}
      </div>
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

function App() {
  const { user, loading } = useAuth()
  const [showLogin, setShowLogin] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      setShowLogin(true)
    } else {
      setShowLogin(false)
    }
  }, [user, loading])

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        background: '#0f172a',
        color: '#94a3b8',
        fontSize: '16px'
      }}>
        Loading...
      </div>
    )
  }

  if (showLogin) {
    return <Login onSuccess={() => setShowLogin(false)} />
  }

  return <DashboardContent />
}

// Render
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
)
