from datetime import date
from math import ceil
import os
from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).with_name(".env.local"))

API_URL = os.getenv("API_URL", "http://127.0.0.1:3000/api/articulos/").rstrip("/") + "/"

def listar_articulos() -> list[dict]:
    """Devuelve articulos publicados del blog."""
    respuesta = requests.get(API_URL, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict) and isinstance(datos.get("articles"), list):
        return datos["articles"]
    if isinstance(datos, dict) and isinstance(datos.get("results"), list):
        return datos["results"]
    raise ValueError("La API no devolvio una lista de articulos")

def crear_borrador(titulo: str, cuerpo: str) -> dict:
    """Guarda un borrador NO publicado y devuelve sus datos."""
    titulo, cuerpo = titulo.strip(), cuerpo.strip()
    if not all((titulo, cuerpo)):
        raise ValueError("Titulo y cuerpo no pueden estar vacios")
    token = os.getenv("API_TOKEN", "")
    if not token:
        raise RuntimeError("Falta la variable API_TOKEN")
    if len(titulo) > 160 or len(cuerpo) > 5000:
        raise ValueError("El titulo no puede superar 160 caracteres y el cuerpo 5000")

    slug = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:111].rstrip("-")
    slug = f"{slug or 'borrador'}-{uuid4().hex[:8]}"
    excerpt = cuerpo[:297].rstrip()
    if len(cuerpo) > 300:
        excerpt += "..."

    respuesta = requests.post(
        API_URL,
        json={
            "slug": slug,
            "title": titulo,
            "category": "Prueba",
            "date": date.today().isoformat(),
            "readingTime": f"{max(1, ceil(len(cuerpo.split()) / 200))} min de lectura",
            "excerpt": excerpt,
            "lead": cuerpo[:600],
            "image": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1600&q=85",
            "imageAlt": "Imagen de prueba",
            "sections": [{"heading": "Contenido", "paragraphs": [cuerpo]}],
            "published": False,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    articulo = datos.get("article") if isinstance(datos, dict) else None
    if not isinstance(articulo, dict) or articulo.get("published") is not False:
        raise RuntimeError("La API no ha confirmado el estado borrador")
    return articulo