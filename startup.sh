#!/bin/bash

# Instalar dependencias
pip install -r requirements.txt

# Realizar migraciones de base de datos
python manage.py migrate --noinput

# Colectar archivos estáticos
python manage.py collectstatic --noinput

# Iniciar Gunicorn
daphne -b 0.0.0.0 -p 8000 config.asgi:application