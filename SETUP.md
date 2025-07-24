# 🚀 Setup Rápido - Food Service 2025

## ⚡ Inicio Rápido

### 1. Configurar Entorno
```bash
# Copiar archivo de configuración
cp .env.example .env

# Editar con tu clave de OpenAI
nano .env
# Agregar: OPENAI_API_KEY=tu_clave_aquí
```

### 2. Agregar Documentos
```bash
# Colocar documentos en carpetas
folders/general/     # PDFs y Excel generales
folders/exhibitors/  # PDFs y Excel de expositores
folders/visitors/    # PDFs y Excel de visitantes
```

### 3. Opción A: Ejecutar con Docker (Recomendado)
```bash
# Iniciar servicios (Redis + API)
docker-compose up -d

# Ver logs
docker-compose logs -f food_service_api

# Parar servicios
docker-compose down
```

### 3. Opción B: Ejecutar Local
```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar Redis (en terminal separado)
redis-server

# Ejecutar API
python api.py
```

### 4. Probar Sistema
```bash
# Documentación interactiva
open http://localhost:8000/docs

# Test de consulta
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuántos expositores hay en Food Service 2025?"}'
```

## 🔧 Variables de Entorno Requeridas

```bash
# .env
OPENAI_API_KEY=tu_clave_openai_aquí
REDIS_HOST=localhost
REDIS_PORT=6379
PORT=8000
```

## 📊 API Simplificada

**Solo 1 endpoint:**
- `POST /query` - Consulta principal para todo tipo de preguntas

**Documentación:**
- `GET /docs` - Documentación interactiva
- `GET /redoc` - Documentación alternativa

## 🧪 Test Completo

```bash
python test_system.py
```

## 📚 Tipos de Consultas

**Expositores:**
- "¿Qué empresas participan?"
- "Lista de expositores"
- "Información de stands"

**Visitantes:**
- "Estadísticas de asistencia"
- "¿Cuántos visitantes hubo?"
- "Demografía de visitantes"

**General:**
- "Información del evento"
- "Fechas y horarios"
- "Ubicación y accesos"