import asyncio
from mcstatus import JavaServer

async def test_mc():
    address = "moonfish.aternos.host:24735"
    print(f"Testing address: {address}")
    try:
        server = await JavaServer.async_lookup(address)
        status = await server.async_status()
        print("Success!")
        print(status.raw)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mc())
