import asyncio
import websockets

async def t():
    async with websockets.connect("ws://127.0.0.1:8001/ws/user/3") as ws:
        await ws.send("ping")
        print("收到:", await ws.recv())

asyncio.run(t())
