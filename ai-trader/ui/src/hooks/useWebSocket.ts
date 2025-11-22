// WebSocket Hook for Real-time Updates
import { useEffect, useRef, useState, useCallback } from 'react';

export type WSRoom = 'signals' | 'trades' | 'logs' | 'system_health' | 'risk_metrics';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useWebSocket(room: WSRoom) {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    try {
      const url = `${WS_BASE_URL}/ws/${room}`;
      console.log(`Connecting to WebSocket: ${url}`);

      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log(`✅ WebSocket connected to room: ${room}`);
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Start heartbeat
        const heartbeatInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000); // 30 seconds

        ws.heartbeatInterval = heartbeatInterval as any;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`❌ WebSocket disconnected from room: ${room}`, event.code, event.reason);
        setIsConnected(false);

        // Clear heartbeat
        if ((ws as any).heartbeatInterval) {
          clearInterval((ws as any).heartbeatInterval);
        }

        // Attempt reconnection with exponential backoff
        const maxAttempts = 10;
        const baseDelay = 1000;
        
        if (reconnectAttemptsRef.current < maxAttempts) {
          const delay = baseDelay * Math.pow(2, reconnectAttemptsRef.current);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, delay);
        } else {
          setError('Failed to reconnect after maximum attempts');
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setError('Failed to create WebSocket connection');
    }
  }, [room]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      // Clear heartbeat
      if ((wsRef.current as any).heartbeatInterval) {
        clearInterval((wsRef.current as any).heartbeatInterval);
      }

      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    lastMessage,
    isConnected,
    error,
    sendMessage,
    reconnect: connect,
  };
}
