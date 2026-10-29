# Cambios para cargar y usar `API_TOKEN`

Este documento explica los cambios realizados para que el agente pueda leer
`API_TOKEN` desde `.env.local` y para que un error al guardar no provoque
intentos repetidos.

> **Importante:** los ejemplos no contienen valores secretos. No copies el
> token en este documento, en el código ni en Git.

## 1. Cargar `.env.local` al iniciar

### Antes

En `herramientas.py` se importaba `os` y se consultaba `API_TOKEN` más adelante,
pero ningún código leía el archivo `.env.local`:

```python
import os
import requests

API_URL = os.getenv(
    "API_TOKEN",
    "http://127.0.0.1:8000/api/articulos/",
).rstrip("/") + "/"
```

La función de guardado ya intentaba obtener la variable del entorno:

```python
token = os.getenv("API_TOKEN", "")
if not token:
    raise RuntimeError("Falta la variable API_TOKEN")
```

`os.getenv` consulta las variables del proceso; no abre archivos `.env`. Por
eso, aunque `.env.local` tuviera `API_TOKEN`, la función podía encontrarlo
vacío y lanzar el error.

### Ahora

Al principio de `herramientas.py` se añadieron estas importaciones y la carga:

```python
import os
from pathlib import Path

from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).with_name(".env.local"))
```

- `python-dotenv` proporciona `load_dotenv`, que lee el archivo y pone sus
  variables a disposición de `os.getenv`.
- `Path(__file__).with_name(".env.local")` localiza el archivo junto a
  `herramientas.py`, independientemente de la carpeta desde la que se lance el
  programa.
- La carga se ejecuta al importar el módulo, antes de que las herramientas
  consulten `API_TOKEN` o `API_URL`.
- Si una variable ya existe en el entorno del sistema, `load_dotenv` no la
  reemplaza por defecto.

La lectura del token en la función se mantiene:

```python
token = os.getenv("API_TOKEN", "")
if not token:
    raise RuntimeError("Falta la variable API_TOKEN")
```

Ahora esa lectura se hace después de cargar `.env.local`. La comprobación sigue
siendo útil: si el archivo falta o no contiene `API_TOKEN`, el programa avisa
con un error explícito en lugar de enviar una petición sin credenciales.

## 2. Enviar el token en la petición

Leer el token no basta: también hay que incluirlo en la petición HTTP que crea
el borrador.

### Antes

La versión previa enviaba este encabezado:

```python
headers={"Authorization": f"Token {token}"}
```

### Ahora

El encabezado usa el esquema Bearer que espera esta API:

```python
headers={"Authorization": f"Bearer {token}"}
```

El valor de `token` se inserta en el encabezado `Authorization`; no se escribe
directamente en el código. Si el servidor cambia el esquema de autenticación,
este encabezado debe coincidir con el que requiera la API.

## 3. Declarar la dependencia

### Antes

`python-dotenv` no estaba incluido entre las dependencias del proyecto.

### Ahora

En `pyproject.toml` se añadió:

```toml
"python-dotenv>=1.2.4",
```

También se actualizó `uv.lock`, que registra la resolución de dependencias del
proyecto. Así, al instalar las dependencias con `uv`, queda disponible la
función `load_dotenv`.

## 4. Evitar reintentos del agente tras un error

Este cambio no carga el token, pero evita el comportamiento confuso que se
observó cuando fallaba el guardado: el modelo podía pedir de nuevo la misma
herramienta.

### Antes

El agente guardaba el error como resultado de la herramienta y continuaba el
bucle, de modo que el modelo podía volver a intentarlo:

```python
except Exception as error:
    resultado = {"error": type(error).__name__, "detalle": str(error)}

print("Herramienta:", nombre, "->", resultado)
mensajes.append({
    "role": "tool",
    "tool_name": nombre,
    "content": json.dumps(resultado, ensure_ascii=False),
})
```

Además, `guardado` solo se marcaba si la función terminaba correctamente.

### Ahora

El estado indica que ya se intentó guardar, no solo que se guardó con éxito:

```python
borrador_intentado = False
```

Antes de ejecutar la herramienta se comprueba y actualiza:

```python
if nombre == "crear_borrador" and borrador_intentado:
    raise ValueError("Ya se ha intentado crear un borrador")

if nombre == "crear_borrador":
    borrador_intentado = True

resultado = HERRAMIENTAS[nombre](**argumentos)
```

Si una herramienta falla, ahora se informa del error y se termina esa ejecución:

```python
except Exception as error:
    print(
        f"Error al ejecutar {nombre}: "
        f"{type(error).__name__}: {error}"
    )
    return
```

Esto evita varios intentos automáticos seguidos. Si el error se debe a
credenciales, primero hay que corregir la configuración y luego volver a
ejecutar el agente.

## 5. Documentar la configuración

Se añadió una sección a `README.md` para indicar que `API_TOKEN` va en
`.env.local`, que ese archivo no debe compartirse y cuál es la URL
predeterminada de la API si no se define `API_URL`.

El archivo local debe tener variables con este formato, usando tus propios
valores:

```dotenv
API_TOKEN=tu_token
API_URL=http://127.0.0.1:3000/api/articulos/
```

`API_URL` es opcional; `API_TOKEN` es necesario para crear un borrador. No
añadas los valores reales a `changes.md`, al código ni a otros archivos que
vayas a publicar.

## 6. Proteger `.env.local` en Git

`.env.local` ya aparecía en `.gitignore`, que impide añadirlo accidentalmente
en el futuro. Sin embargo, Git ya lo tenía bajo seguimiento. Se retiró del
índice de Git sin borrar la copia local:

```powershell
git rm --cached -- .env.local
```

La eliminación del índice queda preparada para el próximo commit; el archivo
local continúa en el equipo. Esta operación no borra el contenido de commits
anteriores. Si el token estuvo publicado o compartido, hay que revocarlo o
rotarlo en el servicio que lo emitió.

## Comprobación realizada

Se comprobó que el proceso carga `API_TOKEN` desde `.env.local` y que una
petición HTTP simulada recibe un encabezado de autorización con esquema Bearer.
También se simuló un error de guardado y se verificó que el agente informa del
error sin volver a intentar crear el borrador. No se realizó una petición real
a la API.
