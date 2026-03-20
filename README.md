# Log Analyzer con AI Functions

Sistema de análisis de logs usando [Strands AI Functions](https://github.com/strands-labs/ai-functions) con AWS Bedrock.
Clasifica logs por severidad y categoría, genera resúmenes, sugiere correcciones y detecta incidentes correlacionando múltiples logs.

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

## Arquitectura AI — Pipeline de funciones

Cada log pasa por un pipeline de 4 `@ai_function` encadenadas:

```
log_entry
    │
    ├─► classify_severity()  → LogLevel (DEBUG..CRITICAL)
    ├─► categorize_log()     → category (networking, database, security...)
    │         │
    │         ▼
    ├─► summarize_log()      → summary (max 30 words, post-condition)
    │         │
    │         ▼
    └─► suggest_fix()        → suggestion (solo si WARNING/ERROR/CRITICAL)
                                  │
                                  ▼
                     validate_suggestion_quality()  ← AI post-condition
```

Además, `correlate_logs()` analiza grupos de logs problemáticos para detectar incidentes y generar reportes con root cause y acciones recomendadas.

## Estructura del proyecto

| Archivo            | Descripción                                              |
|--------------------|----------------------------------------------------------|
| `analyzer.py`      | Pipeline de AI Functions + correlación de incidentes     |
| `log_reader.py`    | Parser de archivos de log                                |
| `cli.py`           | Script CLI para procesar logs                            |
| `sample_logs.txt`  | Archivo de logs de ejemplo                               |
| `storage.py`       | Capa de persistencia SQLite (logs + incidents)           |
| `api.py`           | API REST con FastAPI                                     |
| `dashboard.html`   | Dashboard web (stats, filtros, tabla, incidentes)        |

## API REST

Iniciar el servidor:

```bash
uv run python -m uvicorn api:app --reload --port 8080
```

### Endpoints

| Método   | Ruta                 | Descripción                                      |
|----------|----------------------|--------------------------------------------------|
| `GET`    | `/api/logs`          | Lista logs con filtros (level, source, category)  |
| `GET`    | `/api/stats`         | Estadísticas por level, source y category        |
| `POST`   | `/api/analyze`       | Analiza una lista de logs crudos (JSON body)     |
| `POST`   | `/api/analyze/file`  | Sube y analiza un archivo de logs                |
| `POST`   | `/api/correlate`     | Correlaciona logs problemáticos → incidente      |
| `GET`    | `/api/incidents`     | Lista reportes de incidentes                     |
| `POST`   | `/api/import`        | Importa desde un `analysis_results.json`         |
| `DELETE` | `/api/logs`          | Elimina todos los logs e incidentes              |

- **Dashboard**: http://localhost:8080
- **Swagger (API docs)**: http://localhost:8080/docs

## Modelo

Por defecto usa **Claude Sonnet en Amazon Bedrock**. Para cambiar el modelo, pasá `model` al decorador:

```python
from strands.models.bedrock import BedrockModel
from ai_functions import ai_function

model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")

@ai_function(model=model)
def classify_severity(log_entry: str) -> LogLevel:
    ...
```

## Deploy en AWS (serverless)

La carpeta `aws-deploy/` contiene infraestructura CDK para desplegar todo en AWS con un solo comando:

```
CloudWatch Log Groups → Lambda (AI pipeline) → DynamoDB
                                                  ↑
                          API Gateway → Lambda (REST API)
                                                  
S3 Static Site ← Dashboard HTML
```

### Componentes

| Recurso | Descripción |
|---------|-------------|
| **DynamoDB** (x2) | Tablas `log-analyzer-logs` y `log-analyzer-incidents` |
| **Lambda: processor** | Recibe eventos de CloudWatch, corre el pipeline AI, guarda en DynamoDB |
| **Lambda: api** | REST API para el dashboard (logs, stats, correlate, incidents) |
| **API Gateway** | Expone la Lambda API como REST endpoint |
| **S3 Bucket** | Dashboard estático accesible por browser |
| **CloudWatch Subscription** | Conecta log groups al processor Lambda (configurable) |

### Deploy

```powershell
cd aws-deploy
.\deploy.ps1
```

Con log groups de CloudWatch:

```powershell
.\deploy.ps1 -LogGroups '["/aws/lambda/my-fn","/ecs/my-service"]'
```

### Destroy

```powershell
cd aws-deploy
.\destroy.ps1
```

### Requisitos AWS

1. **AWS CLI configurado con credenciales**
   ```powershell
   aws configure
   ```
   Necesitás `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y una región (ej: `us-east-1`).
   Verificar con:
   ```powershell
   aws sts get-caller-identity
   ```

2. **Bedrock habilitado en la región**
   En la consola de AWS → **Amazon Bedrock** → **Model access** → habilitar **Claude** (Anthropic).
   Regiones recomendadas: `us-east-1` o `us-west-2` (no todas las regiones tienen Bedrock).

3. **Python 3.12+** para el build de la Lambda Layer.

4. **Node.js** (requerido por CDK CLI):
   ```powershell
   winget install OpenJS.NodeJS.LTS
   ```

5. **CDK CLI** instalado globalmente:
   ```powershell
   npm install -g aws-cdk
   cdk --version
   ```

6. **CDK Bootstrap** (primera vez por cuenta/región) — el script lo intenta automáticamente, pero si falla:
   ```powershell
   cdk bootstrap aws://ACCOUNT_ID/REGION
   ```

### Permisos IAM necesarios

La cuenta o rol AWS necesita poder crear: CloudFormation stacks, DynamoDB tables, Lambda functions + IAM roles, API Gateway REST APIs, S3 buckets (con website hosting público), CloudWatch Logs subscription filters e IAM policies (para Bedrock).

- Con **AdministratorAccess** no hay restricciones.
- Mínimo recomendado: **PowerUserAccess** + **IAMFullAccess**.

### Después del deploy

El script imprime dos URLs al finalizar:
- **API Gateway URL** — copiar y pegar en el campo "API" del dashboard
- **Dashboard URL** — abrir en el browser para ver el dashboard

Cuando termines de usar la cuenta de prueba, destruí toda la infraestructura con `.\destroy.ps1`.
