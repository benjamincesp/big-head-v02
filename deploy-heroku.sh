#!/bin/bash

# Script de deployment para Heroku - Food Service 2025
# Ejecuta: chmod +x deploy-heroku.sh && ./deploy-heroku.sh

echo "🚀 Configurando Big-Head v02 en Heroku..."

APP_NAME="big-head"

# Verificar que Heroku CLI esté instalado
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI no está instalado. Instálalo desde: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Verificar que estés logueado en Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ No estás logueado en Heroku. Ejecuta: heroku login"
    exit 1
fi

echo "✅ Configurando variables de entorno..."

# OpenAI Configuration - AGREGAR TU API KEY AQUÍ
heroku config:set OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE" --app $APP_NAME
heroku config:set OPENAI_TIMEOUT=30 --app $APP_NAME
heroku config:set OPENAI_MAX_RETRIES=3 --app $APP_NAME
heroku config:set OPENAI_MODEL=gpt-4o-mini --app $APP_NAME

# Redis - Usar addon de Heroku (recomendado)
echo "📦 Configurando Redis..."
heroku addons:create heroku-redis:mini --app $APP_NAME 2>/dev/null || echo "ℹ️ Redis addon ya existe"
heroku config:set REDIS_SOCKET_TIMEOUT=15 --app $APP_NAME
heroku config:set REDIS_CONNECT_TIMEOUT=5 --app $APP_NAME

# API Configuration
heroku config:set HOST=0.0.0.0 --app $APP_NAME
heroku config:set ENVIRONMENT=production --app $APP_NAME

# Cache Configuration
heroku config:set CACHE_TTL=3600 --app $APP_NAME
heroku config:set CACHE_SIMILARITY_THRESHOLD=0.8 --app $APP_NAME

# Query Configuration
heroku config:set MAX_QUERY_LENGTH=1000 --app $APP_NAME
heroku config:set MAX_RESPONSE_TOKENS=500 --app $APP_NAME

# Logging
heroku config:set LOG_LEVEL=INFO --app $APP_NAME

# Vector Store
heroku config:set DISABLE_VECTOR_STORE=false --app $APP_NAME

# Security (actualizar con el dominio real)
HEROKU_DOMAIN="https://$APP_NAME.herokuapp.com"
heroku config:set ALLOWED_ORIGINS="$HEROKU_DOMAIN,http://localhost:5173,http://localhost:3000" --app $APP_NAME
heroku config:set CORS_ALLOW_CREDENTIALS=true --app $APP_NAME
heroku config:set RATE_LIMIT="30/minute" --app $APP_NAME

echo "✅ Configuración completada!"
echo ""
echo "🔍 Variables configuradas:"
heroku config --app $APP_NAME

echo ""
echo "🎯 Próximos pasos:"
echo "1. Haz push a tu repositorio: git push origin main"
echo "2. El deploy automático se ejecutará en Heroku"
echo "3. Verifica el deployment: heroku logs --tail --app $APP_NAME"
echo "4. Visita tu app: heroku open --app $APP_NAME"
echo ""
echo "🌐 URL de tu app: $HEROKU_DOMAIN"