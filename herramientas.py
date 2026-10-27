import os
import requests

API_URL = os.getenv("API_TOKEN", "http://127.0.0.1:8000/api/articulos/").rstrip("/") + "/"

def listar_articulos() -> list[dict]:
    """Devuelve articulos publicados del blog."""
    respuesta = requests.get(API_URL, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict) and isinstance(datos.get("results"), list):
        return datos["results"]
    raise ValueError("La API no devolvio una lista de articulos")

def crear_borrador(titulo: str, cuerpo: str) -> dict:
    """Guarda un borrador NO publicado y devuelve sus datos."""
    if not all((titulo.strip(), cuerpo.strip())):
        raise ValueError("Titulo y cuerpo no pueden estar vacios")
    token = os.getenv("API_TOKEN", "")
    if not token:
        raise RuntimeError("Falta la variable API_TOKEN")
    respuesta = requests.post(
        API_URL,
        json={"titulo": titulo, "cuerpo": cuerpo},
        headers={"Authorization": f"Token {token}"},
        timeout=15,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    if datos.get("estado") != "borrador":
        raise RuntimeError("La API no ha confirmado el estado borrador")
    return datos