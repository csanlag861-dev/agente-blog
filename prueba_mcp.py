import asyncio
from mcp import Client

async def main():
    async with Client("http://127.0.0.1:8001/mcp") as cliente:
        herramientas = await cliente.list_tools()
        print("Herramientas disponibles:")
        for herramienta in herramientas.tools:
            print("-", herramienta.name)

        resultado = await cliente.call_tool("listar_articulos", {})
        print("\nArtículos:", resultado.structured_content or resultado.content)

asyncio.run(main())