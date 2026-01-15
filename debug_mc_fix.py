import asyncio
from mcstatus import JavaServer

async def test_mc_split():
    address = "moonfish.aternos.host:24735"
    print(f"Testing split address: {address}")
    try:
        if ":" in address:
            host, port = address.split(":")
            print(f"Direct connection to {host}:{port}")
            server = JavaServer(host, int(port))
        else:
            print("Lookup")
            server = await JavaServer.async_lookup(address)
            
        status = await server.async_status()
        print("Success!")
        print(status.raw)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mc_split())
