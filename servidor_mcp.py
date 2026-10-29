"""Servidor MCP"""
from mcp.server import MCPServer
from herramientas import listar_articulos as obtener_publicados
from herramientas import crear_borrador as guardar_borrador

mcp = MCPServer("Blog de fútbol", description="Servidor de herramientas para el blog de fútbol")

@mcp.tool()
def listar_articulos() -> list[dict]:
    """Lista los articulos publicados del blog de fútbol."""
    return obtener_publicados()

@mcp.tool()
def crear_borrador(titulo: str, cuerpo: str) -> dict:
    """Crea un borrador NO publicado desde datos proporcionados."""
    return guardar_borrador(titulo, cuerpo)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)