# Log Analyzer con AI Functions

Sistema de análisis de logs usando [Strands AI Functions](https://github.com/strands-labs/ai-functions) con AWS Bedrock.
Clasifica logs por severidad, genera resúmenes y sugiere correcciones.

## Requisitos previos

1. **Python 3.12+**
2. **[uv](https://docs.astral.sh/uv/)** instalado
3. **Credenciales AWS configuradas** con acceso a Amazon Bedrock:
   ```bash
   aws configure
   ```
   Habilitar acceso al modelo Claude en Bedrock ([documentación](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)).

## Setup

```bash
uv add strands-ai-functions fastapi uvicorn
```

## Uso

Analizar los logs de ejemplo:

```bash
uv run cli.py
```

Analizar un archivo propio:

```bash
uv run cli.py path/to/your/logs.txt
```

Los resultados se guardan en `analysis_results.json` y en `logs.db` (SQLite).

## Estructura del proyecto

| Archivo            | Descripción                                              |
|--------------------|----------------------------------------------------------|
| `analyzer.py`      | AI Functions: clasificación, resumen y sugerencia de fix |
| `log_reader.py`    | Parser de archivos de log                                |
| `cli.py`           | Script CLI para procesar logs                            |
| `sample_logs.txt`  | Archivo de logs de ejemplo                               |
| `storage.py`       | Capa de persistencia SQLite                              |
| `api.py`           | API REST con FastAPI                                     |
| `dashboard.html`   | Dashboard web (stats, filtros, tabla de logs)            |

## API REST

Iniciar el servidor:

```bash
uv run python -m uvicorn api:app --reload
```

### Endpoints

| Método   | Ruta                 | Descripción                                  |
|----------|----------------------|----------------------------------------------|
| `GET`    | `/api/logs`          | Lista logs con filtros (level, source, search) |
| `GET`    | `/api/stats`         | Estadísticas por level y source              |
| `POST`   | `/api/analyze`       | Analiza una lista de logs crudos (JSON body) |
| `POST`   | `/api/analyze/file`  | Sube y analiza un archivo de logs            |
| `POST`   | `/api/import`        | Importa desde un `analysis_results.json`     |
| `DELETE` | `/api/logs`          | Elimina todos los logs                       |

- **Dashboard**: http://localhost:8000
- **Swagger (API docs)**: http://localhost:8000/docs

## Modelo

Por defecto usa **Claude Sonnet en Amazon Bedrock**. Para cambiar el modelo:

```python
from strands.models.bedrock import BedrockModel
from ai_functions import ai_function

model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")

@ai_function(model=model, post_conditions=[...], max_attempts=3)
def analyze_log(log_entry: str) -> LogAnalysis:
    ...
```

## Roadmap

- [x] **Paso 1**: Analyzer core + CLI
- [x] **Paso 2**: API REST (FastAPI) + Storage (SQLite)
- [x] **Paso 3**: Dashboard web
