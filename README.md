# Food Service 2025 - Sistema Multi-Agente

Sistema completo de multi-agentes para Food Service 2025 con capacidades avanzadas de búsqueda, caché inteligente y API REST.

## 🏗️ Arquitectura del Sistema

```
food_service_2024/
├── agents/                 # Agentes especializados
│   ├── general_agent.py   # Agente para consultas generales
│   ├── exhibitors_agent.py # Agente para datos de expositores
│   └── visitors_agent.py   # Agente para datos de visitantes
├── cache/                  # Sistema de caché inteligente
│   ├── redis_manager.py   # Manejo de conexiones Redis
│   └── query_cache.py     # Caché con detección de similitud
├── tools/                  # Herramientas especializadas
│   ├── document_search.py # Búsqueda en documentos generales
│   ├── exhibitor_query.py # Extracción de datos de expositores
│   └── visitor_query.py   # Extracción de datos de visitantes
├── folders/               # Documentos por categoría
│   ├── general/          # Documentos generales
│   ├── exhibitors/       # Documentos de expositores
│   └── visitors/         # Documentos de visitantes
├── orchestrator.py       # Orquestador principal
├── api.py               # API REST con FastAPI
└── docker-compose.yml   # Configuración Docker
```

## 🚀 Características Principales

### 🤖 Sistema Multi-Agente
- **GeneralAgent**: Maneja consultas generales, respuestas máximo 3 párrafos
- **ExhibitorsAgent**: Extrae datos exactos de expositores (nombres, stands, cantidades)
- **VisitorsAgent**: Extrae estadísticas precisas de visitantes (demografía, asistencia)
- **Auto-detección**: Selección automática del agente según palabras clave

### 💾 Caché Inteligente
- **Redis** como motor de caché
- **Detección de similitud** para consultas parecidas (80% threshold)
- **Contador de hits** para consultas frecuentes
- **TTL configurable** por tipo de consulta
- **Invalidación por agente** para refresh de datos

### 🛠️ Herramientas Especializadas
- **DocumentSearchTool**: Búsqueda semántica en PDFs y Excel generales
- **ExhibitorQueryTool**: Extracción inteligente de nombres de empresas y stands desde PDFs y Excel
- **VisitorQueryTool**: Análisis de datos demográficos y estadísticas de asistencia desde PDFs y Excel

### 🌐 API REST Completa
- **FastAPI** con documentación automática
- **CORS** configurado para integración web
- **Manejo robusto de errores**
- **Health checks** y monitoreo
- **Estadísticas en tiempo real**

## 📋 Endpoints de la API

### Consultas Principales
- `POST /food-service/query` - Procesar consulta principal
- `GET /food-service/agents` - Listar agentes disponibles
- `GET /food-service/stats` - Estadísticas del sistema

### Gestión de Datos
- `POST /food-service/refresh/{agent_type}` - Actualizar datos de agente
- `DELETE /food-service/cache` - Limpiar caché
- `GET /food-service/cache/stats` - Estadísticas de caché

### Monitoreo
- `GET /food-service/health` - Estado de salud del sistema
- `GET /food-service/test` - Test básico de conectividad

## 🛠️ Instalación y Configuración

### Prerrequisitos
- Python 3.11+
- Docker y Docker Compose
- OpenAI API Key
- Redis (incluido en Docker Compose)

### 1. Clonar y Configurar

```bash
# Clonar el proyecto
git clone <repository-url>
cd food_service_2024

# Crear archivo de entorno
cp .env.example .env
```

### 2. Configurar Variables de Entorno

Editar `.env`:
```bash
OPENAI_API_KEY=tu_clave_openai_aquí
REDIS_HOST=localhost
REDIS_PORT=6379
PORT=8000
```

### 3. Preparar Documentos

Colocar documentos PDF y Excel en las carpetas correspondientes:
```bash
# Documentos generales (PDF y Excel)
folders/general/
├── info_general.pdf
├── programa_evento.pdf
└── datos_generales.xlsx

# Documentos de expositores (PDF y Excel)
folders/exhibitors/
├── lista_expositores.pdf
├── stands_asignados.pdf
└── empresas_participantes.xlsx

# Documentos de visitantes (PDF y Excel)
folders/visitors/
├── estadisticas_asistencia.pdf
├── demografía_visitantes.pdf
└── datos_diarios.xlsx
```

### 4. Ejecutar con Docker (Recomendado)

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f food_service_api

# Parar servicios
docker-compose down
```

### 5. Ejecutar en Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar Redis (separadamente)
redis-server

# Ejecutar API
python api.py
```

## 📚 Uso de la API

### Ejemplo de Consulta Básica

```bash
curl -X POST "http://localhost:8000/food-service/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cuántos expositores participan en Food Service 2025?",
    "use_cache": true
  }'
```

### Ejemplo de Consulta con Agente Específico

```bash
curl -X POST "http://localhost:8000/food-service/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Lista de empresas expositoras",
    "agent_type": "exhibitors",
    "use_cache": true
  }'
```

### Obtener Estadísticas

```bash
curl "http://localhost:8000/food-service/stats"
```

### Refrescar Datos

```bash
curl -X POST "http://localhost:8000/food-service/refresh/exhibitors"
```

## 🔧 Configuración Avanzada

### Redis
```yaml
# docker-compose.yml
redis:
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Logging
```python
# Configurar nivel de logging
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### Cache TTL
```python
# En query_cache.py
default_ttl = 3600  # 1 hora en segundos
```

## 📊 Monitoreo y Administración

### Docker Services Health Check
```bash
docker-compose ps
```

### Redis Commander (Opcional)
```bash
# Iniciar con perfil admin
docker-compose --profile admin up -d

# Acceder en http://localhost:8081
```

### Logs de la Aplicación
```bash
# Ver logs en tiempo real
docker-compose logs -f food_service_api

# Ver logs de Redis
docker-compose logs -f redis
```

## 🧪 Testing

### Test Básico
```bash
curl "http://localhost:8000/food-service/test"
```

### Health Check
```bash
curl "http://localhost:8000/food-service/health"
```

### Test de Agentes
```bash
# Test agente general
curl -X POST "http://localhost:8000/food-service/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "información general sobre el evento"}'

# Test agente expositores
curl -X POST "http://localhost:8000/food-service/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "lista de empresas expositoras"}'

# Test agente visitantes  
curl -X POST "http://localhost:8000/food-service/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "estadísticas de visitantes por día"}'
```

## 🔒 Seguridad y Mejores Prácticas

### Variables de Entorno
- Nunca commitear archivos `.env` con datos reales
- Usar secrets de Docker en producción
- Rotar claves API regularmente

### Redis Security
```bash
# En producción, configurar autenticación Redis
REDIS_PASSWORD=tu_password_seguro
```

### Rate Limiting
```python
# Implementar rate limiting en FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
```

## 📈 Escalabilidad

### Múltiples Instancias
```yaml
# docker-compose.yml
food_service_api:
  deploy:
    replicas: 3
  # Load balancer necesario
```

### Base de Datos Persistente
```python
# Migrar de caché a base de datos para datos persistentes
# PostgreSQL + SQLAlchemy para datos críticos
```

## 🐛 Troubleshooting

### Error de Conexión Redis
```bash
# Verificar estado de Redis
docker-compose logs redis

# Reiniciar Redis
docker-compose restart redis
```

### Error de OpenAI API
```bash
# Verificar clave API
echo $OPENAI_API_KEY

# Verificar límites de rate
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/models"
```

### Problemas de PDF
```bash
# Verificar permisos de archivos
ls -la folders/

# Verificar formato de PDFs
file folders/general/*.pdf
```

## 📝 Changelog

### v1.0.0
- ✅ Sistema multi-agente completo
- ✅ Caché inteligente con Redis
- ✅ API REST con FastAPI
- ✅ Docker containerización
- ✅ Extracción de datos PDF y Excel
- ✅ Auto-detección de agentes
- ✅ Health checks y monitoreo

## 🤝 Contribución

1. Fork del proyecto
2. Crear branch para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🎯 Roadmap

- [ ] Integración con Elasticsearch para búsqueda avanzada
- [ ] Dashboard web para administración
- [ ] Soporte para más formatos de documentos
- [ ] API de streaming para respuestas en tiempo real
- [ ] Métricas avanzadas con Prometheus
- [ ] Tests automatizados completos

---

**Food Service 2025 Multi-Agent System** - Desarrollado con ❤️ usando OpenAI GPT-4o-mini, FastAPI, Redis y Docker.