# Guía de Despliegue en PythonAnywhere: Sistema de Inventario Euler

Esta guía explica paso a paso cómo poner en producción la aplicación web en [PythonAnywhere](https://www.pythonanywhere.com/) en cuestión de 5 minutos, utilizando el plan gratuito o de pago.

---

## 1. Crear Cuenta en PythonAnywhere
1. Ingresa a [https://www.pythonanywhere.com/](https://www.pythonanywhere.com/).
2. Haz clic en **Pricing & signup** y elige la opción **Create a Beginner account** (100% gratuita) o el plan **Hacker ($5/mes)** si vas a usar un dominio propio.
3. Elige tu nombre de usuario (ejemplo: `tiendaeuler`).
   - Tu enlace público gratuito será: `https://tiendaeuler.pythonanywhere.com`.

---

## 2. Subir los Archivos del Proyecto
Tienes dos formas de subir el proyecto:

### Opción A: Vía Git (Recomendada)
1. En tu panel de PythonAnywhere, ve a la pestaña **Consoles** y abre una consola **Bash**.
2. Clona tu repositorio de GitHub:
   ```bash
   git clone https://github.com/tu-usuario/tienda-ropa-euler.git
   ```
3. Entra a la carpeta:
   ```bash
   cd tienda-ropa-euler
   ```

### Opción B: Vía Archivo ZIP (Desde el navegador)
1. En tu computadora, comprime todo el contenido de la carpeta del proyecto en un archivo `.zip`.
2. En PythonAnywhere, ve a la pestaña **Files**.
3. En la sección **Upload a file**, sube el archivo `.zip`.
4. Abre una consola **Bash** y descomprímelo:
   ```bash
   unzip nombre_del_archivo.zip -d tienda-ropa-euler
   ```

---

## 3. Crear el Entorno Virtual e Instalar Dependencias
En la misma consola Bash de PythonAnywhere, ejecuta:

```bash
# 1. Crear entorno virtual con Python 3.10 o 3.11
mkvirtualenv --python=/usr/bin/python3.10 env_euler

# 2. Instalar las dependencias del proyecto
cd ~/tienda-ropa-euler
pip install -r requirements.txt
```

> **Nota:** PythonAnywhere activará automáticamente el virtualenv `(env_euler)`.

---

## 4. Configurar la Aplicación Web en el Panel
1. En el menú superior de PythonAnywhere, ve a la pestaña **Web**.
2. Haz clic en el botón azul **Add a new web app**.
3. Si estás en cuenta gratuita, confirma el subdominio predeterminado (`tiendaeuler.pythonanywhere.com`).
4. Cuando te pregunte por el framework:
   - Selecciona **Manual configuration** (¡Importante! NO selecciones Flask directamente para tener control total de la ruta).
   - Elige **Python 3.10**.

### Configurar Rutas en la Pestaña "Web":
En la pantalla de configuración que se abre, completa estos campos:

- **Source code**:
  ```text
  /home/tu-usuario/tienda-ropa-euler
  ```
- **Working directory**:
  ```text
  /home/tu-usuario/tienda-ropa-euler
  ```
- **Virtualenv**:
  - Haz clic para editar e introduce:
  ```text
  /home/tu-usuario/.virtualenvs/env_euler
  ```

---

## 5. Configurar el Archivo WSGI
En la misma pestaña **Web**, en la sección **Code**, haz clic en el enlace del archivo:
`WSGI configuration file: /var/www/tu-usuario_pythonanywhere_com_wsgi.py`.

1. **Borra todo el contenido** existente en ese archivo.
2. Pega el siguiente código (reemplazando `tu-usuario` por tu nombre de usuario real en PythonAnywhere):

```python
import sys
import os

# Ruta hacia la carpeta del proyecto
project_home = '/home/tu-usuario/tienda-ropa-euler'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Importar la app de Flask
from app import app as application
```

3. Haz clic en el botón verde **Save** (arriba a la derecha).

---

## 6. Recargar la Aplicación y Probar
1. Vuelve a la pestaña **Web**.
2. Presiona el botón verde grande **Reload tu-usuario.pythonanywhere.com**.
3. Abre tu enlace en el navegador:
   `https://tu-usuario.pythonanywhere.com`

¡Listo! La aplicación creará automáticamente la base de datos `inventario.db` con los productos iniciales de prueba y estará disponible las 24 horas del día.

---

## 7. Consejos de Mantenimiento y Soporte (Para tu Mensualidad de $15 - $25)

1. **Botón de Extender en Plan Gratuito**:
   - En el plan gratuito, PythonAnywhere solicita presionar el botón *"Run until 3 months from today"* cada 3 meses. Recibirás un correo recordatorio.
2. **Descarga de Respaldos**:
   - Puedes ingresar al sistema en la sección **Configuración** y hacer clic en **Descargar Base de Datos (.db)** semanalmente.
   - Si el cliente borra algo por error, solo vuelves a subir el archivo `inventario.db` a `/home/tu-usuario/tienda-ropa-euler/` y recargas la web.
3. **Actualización de Tasa del Día**:
   - La encargada o dueño puede actualizar la tasa del día en cualquier momento desde su teléfono simplemente haciendo clic en la píldora superior **"Tasa del Día"**.
