from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/monitor/{roll_id}")
async def websocket_endpoint(websocket: WebSocket, roll_id: int):
    print(f"[WS] Connected to roll_id={roll_id}")
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 可以在这里处理来自前端的消息
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/ws-test")
async def ws_test():
    return {"status": "ok", "message": "WebSocket router is working"}
