#!/bin/bash

# 🚀 Food Service 2025 - Script de Inicio

echo "🚀 Iniciando Food Service 2025 Multi-Agent System..."

# Verificar si existe el archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde .env.example..."
    cp .env.example .env
    echo "✅ Archivo .env creado. Por favor edita el archivo y agrega tu OPENAI_API_KEY"
    echo "📝 Ejecuta: nano .env"
    exit 1
fi

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Instalando dependencias Python..."
    
    # Verificar si Python está instalado
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 no está instalado. Por favor instala Python 3.11+"
        exit 1
    fi
    
    # Instalar dependencias
    echo "📦 Instalando dependencias..."
    pip install -r requirements.txt
    
    # Verificar si Redis está corriendo
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "🔴 Redis no está corriendo. Iniciando Redis..."
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes
            echo "✅ Redis iniciado"
        else
            echo "❌ Redis no está instalado. Instala Redis o usa Docker"
            exit 1
        fi
    fi
    
    # Ejecutar la aplicación
    echo "🚀 Iniciando API de Food Service 2025..."
    python api.py
    
else
    echo "🐳 Docker detectado. Iniciando con Docker Compose..."
    
    # Verificar si docker-compose está instalado
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose no está instalado"
        exit 1
    fi
    
    # Iniciar servicios con Docker
    echo "📦 Iniciando servicios (Redis + API)..."
    docker-compose up -d
    
    echo "✅ Servicios iniciados!"
    echo "📊 Para ver logs: docker-compose logs -f food_service_api"
    echo "🛑 Para parar: docker-compose down"
fi

echo ""
echo "🎉 Food Service 2025 está corriendo!"
echo "📚 Documentación: http://localhost:8000/docs"
echo "🔍 Endpoint principal: POST http://localhost:8000/query"
echo ""
echo "🧪 Para probar el sistema:"
echo "curl -X POST http://localhost:8000/query \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"query\": \"¿Cuántos expositores hay?\"}'"