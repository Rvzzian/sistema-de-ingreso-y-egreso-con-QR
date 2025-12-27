# Sistema de Control de Ingreso y Egreso con QR

Este proyecto consiste en un **sistema de control de asistencias** mediante **códigos QR**, orientado al registro de **ingresos y egresos** de usuarios de forma segura y automatizada.

El sistema está desarrollado principalmente con **Python (Flask)** para el backend y tecnologías web básicas para el frontend.

---

## Tecnologías utilizadas

### Backend
- Python 3.13
- Flask
- Flask-Login (autenticación y manejo de sesiones)
- SQLite (base de datos)
- Flask-QRCode / qrcode[pil]
  
### Dependencias
- Flask  
  Framework web principal

- Flask-Login  
  Manejo de autenticación, sesiones y rutas protegidas

- Werkzeug  
  Hashing y verificación segura de contraseñas

- SQLite3  
  Base de datos embebida

- qrcode  
  Generación dinámica de códigos QR

- Pillow  
  Procesamiento de imágenes para QR

- python-dotenv  
  Carga de variables de entorno desde archivos `.env`


### Frontend
- HTML
- CSS-BOOSTRAP
- JavaScript
- Python

### Otros
- Ngrok (túnel HTTPS para pruebas locales)

--- 

## Funcionalidades principales

- Autenticación de usuarios
- Registro de usuarios
- Generación de códigos QR
- Marcado de ingreso y egreso mediante QR
- Manejo de sesiones protegidas
- Persistencia de datos en base de datos local

---

## Requisitos previos

Antes de iniciar, asegúrate de tener instalado:

- **Python 3.13**
  - Descargar desde: https://www.python.org
  - Verificar que Python esté agregado al **PATH** del sistema

- **pip** (incluido con Python)

---

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/Rvzzian/sistema-de-ingreso-y-egreso-con-QR.git
cd sistema-de-ingreso-y-egreso-con-QR

2. Descargar dependencias
```cmd - visual
pip install flask flask-login qrcode[pil] pillow

3. crear el .env
desde la raiz del proyecto crean el .env y asignan las variables sus credenciales
ADMIN_USERNAME=
ADMIN_PASSWORD=
SECRET_KEY=

4. correr el sistema
```cmd - visual
python app.py
con esto tendriamos corriendo a nivel local pero por momento no sirve al tener que utilizar https para activar la camara desde la pagina

5.tunel que brinda el ssl
instalaremos ngrok (busquen un tuto para esto) agregaremos nuestra auth y despues activamos el tunel
```cmd - visual
ngrok http 5000

6. para expandir la funcionalidad free y con url fija + ssl utilicen pythonanywhere es free para proyectos livianos
https://www.pythonanywhere.com/


