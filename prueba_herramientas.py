"""Prueba de integracion de las funciones HTTP sin modelo IA."""
from herramientas import listar_articulos, crear_borrador

antes = listar_articulos()
print("Artículos publicados antes:", len(antes))
creado = crear_borrador(
    "Prueba de robótica en el aula",
    "Texto de laboratorio; esto es un texto de prueba.",
)
assert creado["published"] is False
assert all(a["slug"] != creado["slug"] for a in listar_articulos())
print("Borrador creado:", creado["slug"])
print("Comprobación: el borrador no es público")