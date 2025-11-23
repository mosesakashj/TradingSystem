# WebSocket Server for Real-time Updates
import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
from datetime import datetime
import redis.asyncio as redis
from enum import Enum

from .auth import verify_jwt_token


class Room(str, Enum):
    """WebSocket rooms for different data streams"""
    SIGNALS = "signals"
    TRADES = "trades"
    LOGS = "logs"
    SYSTEM_HEALTH = "system_health"
    RISK_METRICS = "risk_metrics"
    PRICES = "prices"


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # {room_name: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {
            Room.SIGNALS: set(),
            Room.TRADES: set(),
            Room.LOGS: set(),
            Room.SYSTEM_HEALTH: set(),
            Room.RISK_METRICS: set(),
            Room.PRICES: set(),
        }
        
        # Redis for pub/sub
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub_task: Optional[asyncio.Task] = None
    
    async def connect_redis(self, redis_url: str = "redis://localhost:6379/0"):
        """Connect to Redis for pub/sub"""
        try:
            self.redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            print("✅ WebSocket Redis connection established")
            
            # Start pub/sub listener
            self.pubsub_task = asyncio.create_task(self._redis_listener())
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
    
    async def _redis_listener(self):
        """Listen to Redis pub/sub channels and broadcast to WebSocket clients"""
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to all rooms
        channels = [f"trading:{room}" for room in Room]
        await pubsub.subscribe(*channels)
        
        print(f"✅ Subscribed to Redis channels: {channels}")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    
                    # Extract room name from channel (trading:signals -> signals)
                    room = channel.split(':', 1)[1] if ':' in channel else channel
                    
                    # Broadcast to WebSocket clients in that room
                    await self.broadcast_to_room(room, data)
        except Exception as e:
            print(f"❌ Redis listener error: {e}")
    
    async def connect(self, websocket: WebSocket, room: str, token: Optional[str] = None):
        """
        Accept new WebSocket connection and add to room
        
        Args:
            websocket: WebSocket connection
            room: Room name to join
            token: Optional JWT token for authentication
        """
        # Authenticate (in production, verify token)
        # if token:
        #     try:
        #         verify_jwt_token(token)
        #     except Exception:
        #         await websocket.close(code=1008)  # Policy violation
        #         return
        
        await websocket.accept()
        
        if room not in self.active_connections:
            self.active_connections[room] = set()
        
        self.active_connections[room].add(websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "room": room,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"✅ WebSocket connected to room: {room} (total: {len(self.active_connections[room])})")
    
    def disconnect(self, websocket: WebSocket, room: str):
        """
        Remove WebSocket connection from room
        
        Args:
            websocket: WebSocket connection
            room: Room name
        """
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
            print(f"❌ WebSocket disconnected from room: {room} (remaining: {len(self.active_connections[room])})")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"❌ Error sending personal message: {e}")
    
    async def broadcast_to_room(self, room: str, message: str or dict):
        """
        Broadcast message to all connections in a room
        
        Args:
            room: Room name
            message: Message to broadcast (string or dict)
        """
        if room not in self.active_connections:
            return
        
        # Convert to dict if string (likely from Redis)
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                message = {"data": message}
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Broadcast to all connected clients in room
        disconnected = set()
        
        for connection in self.active_connections[room]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections[room].discard(connection)
    
    async def publish_to_redis(self, room: str, message: dict):
        """
        Publish message to Redis channel (for cross-service communication)
        
        Args:
            room: Room/channel name
            message: Message dict to publish
        """
        if not self.redis_client:
            print("⚠️  Redis not connected, skipping publish")
            return
        
        try:
            channel = f"trading:{room}"
            await self.redis_client.publish(channel, json.dumps(message))
        except Exception as e:
            print(f"❌ Redis publish error: {e}")
    
    async def broadcast_signal(self, signal_data: dict):
        """Helper: Broadcast new signal"""
        await self.broadcast_to_room(Room.SIGNALS, {
            "type": "signal",
            "data": signal_data
        })
    
    async def broadcast_trade(self, trade_data: dict):
        """Helper: Broadcast trade update"""
        await self.broadcast_to_room(Room.TRADES, {
            "type": "trade",
            "data": trade_data
        })
    
    async def broadcast_log(self, log_data: dict):
        """Helper: Broadcast log message"""
        await self.broadcast_to_room(Room.LOGS, {
            "type": "log",
            "data": log_data
        })
    
    async def broadcast_health(self, health_data: dict):
        """Helper: Broadcast system health update"""
        await self.broadcast_to_room(Room.SYSTEM_HEALTH, {
            "type": "health",
            "data": health_data
        })
    
    async def broadcast_risk_metrics(self, risk_data: dict):
        """Helper: Broadcast risk metrics update"""
        await self.broadcast_to_room(Room.RISK_METRICS, {
            "type": "risk",
            "data": risk_data
        })
    
    async def close_all(self):
        """Close all WebSocket connections (for shutdown)"""
        for room, connections in self.active_connections.items():
            for connection in connections.copy():
                try:
                    await connection.close()
                except Exception:
                    pass
        
        if self.pubsub_task:
            self.pubsub_task.cancel()
        
        if self.redis_client:
            await self.redis_client.close()


# Global connection manager
manager = ConnectionManager()


# WebSocket endpoint handlers
async def websocket_endpoint(
    websocket: WebSocket,
    room: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time updates
    
    Usage in FastAPI:
        @app.websocket("/ws/{room}")
        async def websocket_route(websocket: WebSocket, room: str):
            await websocket_endpoint(websocket, room)
    """
    await manager.connect(websocket, room, token)
    
    try:
        while True:
            # Keep connection alive with ping/pong
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Echo back for debugging (optional)
                await manager.send_personal_message({
                    "type": "echo",
                    "data": data
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket, room)
