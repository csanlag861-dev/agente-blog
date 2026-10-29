"""Genera un articulo con Ollama y lo guarda mediante un servidor MCP."""
import asyncio
import json
import os
import sys
from mcp import Client
from ollama import AsyncClient
from pydantic import BaseModel, Field

MODELO = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
URL_MCP = "http://127.0.0.1:8001/mcp"


class Articulo(BaseModel):
    titulo: str = Field(min_length=5, max_length=200)
    cuerpo: str = Field(min_length=50)


async def usar_mcp(nombre, argumentos):
    # Una conexion nueva para cada llamada: no permanece abierta mientras Ollama trabaja.
    async with Client(URL_MCP) as cliente:
        respuesta = await cliente.call_tool(nombre, argumentos)
    if respuesta.is_error:
        texto = " ".join(b.text for b in respuesta.content if b.type == "text")
        raise RuntimeError(f"{nombre}: {texto or 'error de la herramienta'}")
    datos = respuesta.structured_content
    if datos is None:
        texto = "\n".join(b.text for b in respuesta.content if b.type == "text")
        datos = json.loads(texto)
    if isinstance(datos, dict) and set(datos) == {"result"}:
        datos = datos["result"]
    if isinstance(datos, dict) and datos.get("error"):
        raise RuntimeError(f"{nombre}: {datos['error']}")
    return datos


async def redactar(encargo, titulos):
    print(f"Ollama ({MODELO}): redactando el articulo...", flush=True)
    mensajes = [
        {"role": "system", "content": (
            "Redactas noticias de fútbol de unas 300 palabras. Usa solo los "
            "datos del usuario; no inventes fechas, dispositivos ni fuentes. "
            "Indica cuando se trate de una simulacion educativa. "
            "Evita noticias repetidas. Devuelve solo titulo y cuerpo en JSON."
        )},
        {"role": "user", "content": f"Titulos publicados: {titulos}\n\n{encargo}"},
    ]
    tarea = asyncio.create_task(AsyncClient(timeout=150).chat(
        model=MODELO, messages=mensajes, think=False,
        format=Articulo.model_json_schema(),
        options={"temperature": 0, "num_predict": 700},
    ))
    try:
        for segundos in range(20, 121, 20):
            terminado, _ = await asyncio.wait({tarea}, timeout=20)
            if terminado:
                respuesta = await tarea
                return Articulo.model_validate_json(respuesta.message.content)
            print(f"Ollama sigue redactando ({segundos} s)...", flush=True)
        raise TimeoutError("Ollama no ha respondido en 120 segundos")
    finally:
        if not tarea.done():
            tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)


async def ejecutar(encargo):
    publicados = await usar_mcp("listar_articulos", {})
    if not isinstance(publicados, list):
        raise RuntimeError("listar_articulos no devolvio una lista")
    titulos = [a["titulo"] for a in publicados
               if isinstance(a, dict) and isinstance(a.get("titulo"), str)]
    print(f"MCP: consultados {len(publicados)} articulos publicados.", flush=True)
    articulo = await redactar(encargo, titulos)
    print(f"Ollama: articulo redactado ({articulo.titulo}).", flush=True)
    print("MCP: enviando el borrador a Django...", flush=True)
    creado = await usar_mcp("crear_borrador", articulo.model_dump())
    if not isinstance(creado, dict) or not creado.get("id") or creado.get("estado") != "borrador":
        raise RuntimeError(f"Django no ha confirmado el guardado: {creado!r}")
    print(f"BORRADOR GUARDADO EN DJANGO: ID {creado['id']} (borrador)", flush=True)


def detalle(error):
    if isinstance(error, BaseExceptionGroup):
        return " | ".join(detalle(e) for e in error.exceptions)
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    encargo = input("Cuéntame tu idea para el artículo: ").strip()
    if not encargo:
        sys.exit("ERROR: el encargo está vacío")
    try:
        asyncio.run(ejecutar(encargo))
    except Exception as error:
        print("ERROR:", detalle(error), file=sys.stderr, flush=True)
        sys.exit(1)