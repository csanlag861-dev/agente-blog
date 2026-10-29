"""Agente único con límite de pasos y dos herramientas verificadas."""
import json
import os
from ollama import chat
from herramientas import listar_articulos, crear_borrador

MODELO = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
HERRAMIENTAS = {
    "listar_articulos": listar_articulos,
    "crear_borrador": crear_borrador,
}
REGLAS = (
    "Eres redactor de un blog de fútbol en español. Escribe artículos "
    "claros, atractivos y bien estructurados para aficionados. Trabaja "
    "solo con los hechos que facilite el usuario; no inventes resultados, "
    "estadísticas, declaraciones, lesiones, fichajes ni enlaces. "
    "Antes de crear un borrador, consulta los artículos publicados para "
    "evitar repetir temas. Si faltan datos importantes, pide aclaración. "
    "Puedes crear como máximo un borrador, nunca publicar ni borrar. "
    "Indica que es una simulación si los hechos son ficticios."
)


def ejecutar(encargo: str) -> None:
    mensajes = [
        {"role": "system", "content": REGLAS},
        {"role": "user", "content": encargo},
    ]
    consultado = False
    borrador_intentado = False
    for _ in range(6):
        respuesta = chat(
            model=MODELO,
            messages=mensajes,
            tools=list(HERRAMIENTAS.values()),
        )
        mensajes.append(respuesta.message)
        llamadas = respuesta.message.tool_calls or []
        if not llamadas:
            print(respuesta.message.content or "Sin respuesta final del modelo")
            return
        for llamada in llamadas:
            nombre = llamada.function.name
            argumentos = llamada.function.arguments
            try:
                if nombre not in HERRAMIENTAS:
                    raise ValueError("Herramienta no autorizada")
                if nombre == "crear_borrador" and not consultado:
                    raise ValueError("Consulta articulos antes de guardar")
                if nombre == "crear_borrador" and borrador_intentado:
                    raise ValueError("Ya se ha intentado crear un borrador")
                if not isinstance(argumentos, dict):
                    raise ValueError("Argumentos no validos")
                if nombre == "crear_borrador":
                    borrador_intentado = True
                resultado = HERRAMIENTAS[nombre](**argumentos)
                if nombre == "listar_articulos":
                    consultado = True
            except Exception as error:
                print(
                    f"Error al ejecutar {nombre}: "
                    f"{type(error).__name__}: {error}"
                )
                return
            print("Herramienta:", nombre, "->", resultado)
            mensajes.append({
                "role": "tool",
                "tool_name": nombre,
                "content": json.dumps(resultado, ensure_ascii=False),
            })
    print("Detenido: máximo de seis ciclos alcanzado")

if __name__ == "__main__":
    ejecutar(input("Cuéntame tu idea para el artículo: "))