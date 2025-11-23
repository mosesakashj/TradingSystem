import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE_URL = 'ws://localhost:8000/ws';

export function useWebSocket(room) {
  const [lastMessage, setLastMessage] = useState(null);
  const [status, setStatus] = useState('disconnected'); // connecting, connected, disconnected
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    ws.current = new WebSocket(`${WS_BASE_URL}/${room}`);

    ws.current.onopen = () => {
      setStatus('connected');
      console.log(`✅ WS Connected: ${room}`);
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
      } catch (err) {
        console.error('❌ WS Parse Error:', err);
      }
    };

    ws.current.onclose = () => {
      setStatus('disconnected');
      console.log(`⚠️ WS Disconnected: ${room}, reconnecting...`);
      // Reconnect after 3s
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.current.onerror = (err) => {
      console.error('❌ WS Error:', err);
      ws.current.close();
    };
  }, [room]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        // Prevent reconnect on unmount
        ws.current.onclose = null; 
        ws.current.close();
      }
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connect]);

  return { lastMessage, status };
}
