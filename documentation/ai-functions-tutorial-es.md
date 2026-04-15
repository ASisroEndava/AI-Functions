# Biblioteca AI Functions — Tutorial Completo

> **Biblioteca:** `strands-ai-functions` (importar como `ai_functions`)
> **GitHub:** [strands-labs/ai-functions](https://github.com/strands-labs/ai-functions)
> **Requiere:** Python 3.12+ (3.14+ recomendado para todas las funcionalidades)

---

## Tabla de Contenidos

1. [¿Qué es AI Functions?](#1-qué-es-ai-functions)
2. [Instalación y Configuración](#2-instalación-y-configuración)
3. [Tu Primera AI Function](#3-tu-primera-ai-function)
4. [Cómo Funciona Internamente](#4-cómo-funciona-internamente)
5. [Tipos de Retorno — Desde Strings hasta Objetos Complejos](#5-tipos-de-retorno--desde-strings-hasta-objetos-complejos)
6. [Post-Condiciones — Haciendo la IA Confiable](#6-post-condiciones--haciendo-la-ia-confiable)
7. [Eligiendo un Proveedor de Modelo](#7-eligiendo-un-proveedor-de-modelo)
8. [Configuración y Configs Reutilizables](#8-configuración-y-configs-reutilizables)
9. [Modo de Ejecución de Código — Integración con Python](#9-modo-de-ejecución-de-código--integración-con-python)
10. [Herramientas — Dándole Superpoderes a tus Funciones](#10-herramientas--dándole-superpoderes-a-tus-funciones)
11. [Funciones Asíncronas y Flujos Paralelos](#11-funciones-asíncronas-y-flujos-paralelos)
12. [Memoria y Optimización](#12-memoria-y-optimización)
13. [Ejemplo Real: Pipeline del Log Analyzer](#13-ejemplo-real-pipeline-del-log-analyzer)
14. [Mejores Prácticas y Consejos](#14-mejores-prácticas-y-consejos)
15. [Solución de Problemas Comunes](#15-solución-de-problemas-comunes)
16. [Referencia Rápida](#16-referencia-rápida)

---

## 1. ¿Qué es AI Functions?

Imaginá que podés escribir una función en Python donde, en lugar de escribir la lógica vos mismo, describís **lo que querés que la función haga** en lenguaje natural — y un modelo de IA descubre cómo hacerlo. Eso es exactamente lo que hace la biblioteca `ai_functions`.

### La Idea Central

En la programación tradicional, escribís instrucciones explícitas:

```python
# Enfoque tradicional — escribís cada paso
def classify_sentiment(text: str) -> str:
    positive_words = ["good", "great", "excellent"]
    negative_words = ["bad", "terrible", "awful"]
    # ... mucha lógica manual
```

Con AI Functions, describís la **intención** y la IA se encarga del razonamiento:

```python
# Enfoque AI Functions — describís lo que querés
from ai_functions import ai_function

@ai_function
def classify_sentiment(text: str) -> str:
    """Classify the sentiment of the following text as 'positive', 'negative', or 'neutral'.
    
    Text: {text}
    """
```

Ambas funciones se llaman de la misma manera: `classify_sentiment("This movie was great!")`. La diferencia es que la AI Function envía tu descripción a un Modelo de Lenguaje Grande (LLM), el cual analiza el texto y devuelve el resultado.

### ¿Por Qué No Llamar Directamente a una API de IA?

Podrías llamar directamente a un modelo de IA usando su API, pero AI Functions te dan varias ventajas:

- **Seguridad de tipos** — La biblioteca asegura que la IA devuelva datos en el tipo exacto que especificaste (`str`, `int`, modelo Pydantic, etc.)
- **Post-condiciones** — Podés definir reglas que la salida de la IA debe cumplir. Si fallan, la IA reintenta automáticamente.
- **Composabilidad** — Las AI Functions son funciones regulares de Python. Podés encadenarlas, pasar resultados entre ellas y construir pipelines complejos.
- **Independencia de proveedor** — Cambiá entre Amazon Bedrock, OpenAI u otros proveedores con solo modificar una línea.

---

## 2. Instalación y Configuración

### Instalar la Biblioteca

```bash
# Usando pip
pip install strands-ai-functions

# Usando uv (recomendado)
uv add strands-ai-functions
```

### Configurar Credenciales

AI Functions necesitan acceso a un proveedor de modelos de IA. El proveedor por defecto es **Amazon Bedrock**.

**Para Amazon Bedrock:**
1. Instalá y configurá el AWS CLI
2. Asegurate de que tus credenciales de AWS estén configuradas (vía `~/.aws/credentials`, variables de entorno, o rol IAM)
3. Habilitá el modelo deseado en la consola de Bedrock

**Para OpenAI:**
1. Obtené una API key en [platform.openai.com](https://platform.openai.com)
2. Pasala al configurar el modelo (ver [Sección 7](#7-eligiendo-un-proveedor-de-modelo))

### Verificar que Funciona

```python
from ai_functions import ai_function

@ai_function
def say_hello(name: str) -> str:
    """Say hello to {name} in a creative way."""

print(say_hello("World"))
# Salida: algo como "Greetings, World! May your day be filled with wonder!"
```

Si esto se ejecuta sin errores, tu configuración está completa.

---

## 3. Tu Primera AI Function

Construyamos un traductor simple para entender los conceptos básicos.

### Paso 1: Importar el Decorador

```python
from ai_functions import ai_function
```

### Paso 2: Definir tu Función

```python
@ai_function
def translate_text(text: str, lang: str) -> str:
    """
    Translate the text below to the following language: {lang}.
    ---
    {text}
    """
```

Analicemos esto:

| Elemento | Propósito |
|----------|-----------|
| `@ai_function` | Le dice a la biblioteca que esta función está potenciada por IA |
| `text: str, lang: str` | Parámetros regulares de Python — las entradas |
| `-> str` | El tipo de retorno — la IA debe devolver un string |
| El docstring | El **prompt** enviado al modelo de IA. `{text}` y `{lang}` se reemplazan con los valores reales de los argumentos |

### Paso 3: Llamarla Como Cualquier Función

```python
result = translate_text("Hello, how are you?", lang="Spanish")
print(result)
# Salida: "Hola, ¿cómo estás?"
```

**Observación clave:** Desde la perspectiva de quien llama, `translate_text` es simplemente una función normal. No necesitás saber que está potenciada por IA. Esto es lo que hace a las AI Functions tan poderosas — se integran naturalmente en cualquier código.

### El Docstring Es Tu Prompt

El docstring es la parte más importante. Le dice a la IA qué hacer. La biblioteca:

1. Toma tu docstring
2. Reemplaza los marcadores `{nombre_parametro}` con los valores reales de los argumentos
3. Envía el texto resultante al modelo de IA
4. Parsea la respuesta de la IA al tipo de retorno declarado
5. Devuelve el resultado

**Consejos para escribir buenos docstrings/prompts:**

- Sé específico sobre lo que querés
- Mencioná las restricciones explícitamente (ej: "Return ONLY the category name, nothing else")
- Usá ejemplos cuando la tarea sea ambigua
- Estructurá prompts complejos con viñetas o listas numeradas

---

## 4. Cómo Funciona Internamente

Cuando llamás a una AI Function, esto es lo que pasa paso a paso:

```
Tu Código                    Biblioteca AI Functions           Modelo de IA (ej: Bedrock)
─────────                    ──────────────────────            ──────────────────────────
                                                              
classify("error log")  ──►   1. Leer el docstring             
                             2. Reemplazar {log_entry}         
                                con "error log"                
                             3. Construir prompt         ──►   4. La IA lee el prompt
                                completo                       5. La IA genera respuesta
                             6. Recibir respuesta de IA  ◄──   
                             7. Parsear al tipo de retorno     
                             8. Verificar post-condiciones     
                             9. Si falló → reintentar con      
                                feedback del error       ──►   10. La IA corrige respuesta
                            11. Devolver resultado final ◄──   
result = "ERROR"       ◄──                                    
```

### El Bucle de Auto-Corrección

Esto es lo que diferencia a AI Functions de las llamadas directas a APIs. Si definís post-condiciones (reglas que la salida debe cumplir), la biblioteca:

1. Verifica cada post-condición contra la salida
2. Si alguna falla, envía los mensajes de error de vuelta a la IA
3. La IA intenta de nuevo, sabiendo qué salió mal
4. Repite hasta que todas las condiciones pasen o se alcance `max_attempts`

Esto significa que tu pipeline no produce silenciosamente resultados incorrectos — o te da una respuesta correcta o te dice que no pudo.

---

## 5. Tipos de Retorno — Desde Strings hasta Objetos Complejos

Las AI Functions pueden devolver virtualmente cualquier tipo de Python. La biblioteca maneja la conversión automáticamente.

### Tipos Primitivos

```python
@ai_function
def count_words(text: str) -> int:
    """Count the number of words in: {text}"""

@ai_function
def is_question(text: str) -> bool:
    """Determine if the following text is a question: {text}"""

@ai_function
def estimate_reading_time(text: str) -> float:
    """Estimate the reading time in minutes for: {text}"""
```

### Tipos Literal (Opciones Restringidas)

Cuando querés que la IA elija de un conjunto fijo de opciones, usá `Literal`:

```python
from typing import Literal

@ai_function
def classify_severity(log_entry: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Classify the severity level of this log entry.
    
    Log entry: {log_entry}
    """
```

La IA **debe** devolver uno de esos valores exactos. Si intenta devolver algo diferente (como "WARN" o "High"), la biblioteca le pedirá que corrija la respuesta.

### Modelos Pydantic (Salida Estructurada)

Aquí es donde las AI Functions realmente brillan. Podés definir salidas estructuradas complejas usando Pydantic:

```python
from pydantic import BaseModel

class LogAnalysis(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    summary: str
    suggestion: str
    category: str
    confidence: Literal["high", "medium", "low"]

@ai_function
def analyze_log(log_entry: str) -> LogAnalysis:
    """Analyze this log entry and provide a structured analysis.
    
    Log entry: {log_entry}
    """
```

La IA devuelve un objeto `LogAnalysis` completamente poblado con todos los campos rellenados. Luego podés acceder a ellos como cualquier objeto de Python:

```python
result = analyze_log("Connection refused to database at 10.0.2.15:5432")
print(result.log_level)    # "ERROR"
print(result.summary)      # "Database connection failure on port 5432"
print(result.suggestion)   # "Check database server status and network connectivity"
```

### Modelos Anidados Complejos

```python
class IncidentReport(BaseModel):
    title: str
    root_cause: str
    affected_services: list[str]
    severity: Literal["low", "medium", "high", "critical"]
    recommended_actions: list[str]
    related_log_lines: list[int]
```

La IA poblará cada campo, incluyendo listas de strings y enteros.

### Objetos Nativos de Python (con Ejecución de Código)

Con el modo de ejecución de código habilitado (ver [Sección 9](#9-modo-de-ejecución-de-código--integración-con-python)), las AI Functions pueden devolver objetos nativos de Python como `pandas.DataFrame`, arrays de `numpy`, o cualquier otro tipo.

---

## 6. Post-Condiciones — Haciendo la IA Confiable

Las post-condiciones son la **innovación clave** de AI Functions. Transforman salidas de IA poco confiables en resultados validados y confiables.

### El Problema que Resuelven

Los modelos de IA son no determinísticos — pueden:
- Devolver un resumen demasiado largo
- Olvidar incluir campos requeridos
- Dar sugerencias vagas en lugar de específicas

Sin post-condiciones, estos errores se propagan silenciosamente por tu pipeline. Con post-condiciones, se detectan y corrigen automáticamente.

### Método 1: Funciones Python (Verificaciones Determinísticas)

La post-condición más simple es una función regular de Python que lanza un `AssertionError` si la salida es inválida:

```python
def check_summary_length(summary: str):
    """Post-condition: summary must be at most 30 words."""
    word_count = len(summary.split())
    assert word_count <= 30, f"Summary has {word_count} words, max is 30"

@ai_function(post_conditions=[check_summary_length], max_attempts=3)
def summarize_log(log_entry: str) -> str:
    """Summarize this log entry in a single sentence of at most 30 words.
    
    Log entry: {log_entry}
    """
```

Qué pasa cuando llamás a `summarize_log`:

1. La IA genera un resumen
2. `check_summary_length` cuenta las palabras
3. Si la cantidad excede 30, la aserción falla
4. La biblioteca envía el mensaje de error de vuelta a la IA: *"Summary has 45 words, max is 30"*
5. La IA intenta de nuevo, esta vez manteniéndolo más corto
6. Esto se repite hasta `max_attempts=3` veces

### Método 2: Devolver PostConditionResult

En lugar de aserciones, podés devolver un objeto `PostConditionResult` para más control:

```python
from ai_functions.types import PostConditionResult

def check_summary_length(summary: str) -> PostConditionResult:
    word_count = len(summary.split())
    if word_count > 30:
        return PostConditionResult(
            passed=False,
            message=f"Summary has {word_count} words, max is 30"
        )
    return PostConditionResult(passed=True)
```

### Método 3: Post-Condiciones Potenciadas por IA

Acá está la parte realmente poderosa — tus post-condiciones pueden ser, a su vez, AI Functions. Esto te permite validar cosas que son difíciles de verificar con código, como "¿Es esta sugerencia específica y accionable?"

```python
@ai_function
def check_suggestion_quality(result: LogAnalysis) -> PostConditionResult:
    """Evaluate whether this fix suggestion is actionable and specific.

    Log level: {result.log_level}
    Summary: {result.summary}
    Suggestion: {result.suggestion}

    A good suggestion should mention specific steps, tools, or configurations.
    Return passed=True if the suggestion is specific enough, or passed=False 
    with feedback explaining what's missing."""
```

Esta post-condición de IA evalúa la calidad de la salida de otra IA. Si la sugerencia es demasiado vaga, proporciona feedback que ayuda a la IA original a mejorar.

### Combinando Múltiples Post-Condiciones

Podés aplicar múltiples post-condiciones a una sola función. Todas se verifican en paralelo, y todos los fallos se reportan a la IA de una vez:

```python
@ai_function(
    post_conditions=[check_length, check_format, check_quality],
    max_attempts=5
)
def generate_report(data: str) -> Report:
    """Generate a report from the following data: {data}"""
```

### Post-Condiciones que Acceden a las Entradas Originales

Las post-condiciones pueden solicitar los argumentos originales de la función por nombre:

```python
def run_tests(_answer, feature: FeatureRequest):
    """Ignora la respuesta de la IA, valida ejecutando tests reales."""
    retcode = pytest.main(feature.test_files)
    if retcode:
        raise RuntimeError("Tests failed")

@ai_function(post_conditions=[run_tests])
def implement_feature(feature: FeatureRequest) -> str:
    """Implement the following feature: {feature.description}"""
```

El parámetro `_answer` recibe la salida de la IA, y `feature` recibe el argumento de entrada original. Este patrón es útil cuando la validación depende de estado externo (como ejecutar tests).

---

## 7. Eligiendo un Proveedor de Modelo

AI Functions soportan múltiples proveedores de modelos de IA. Configurás el proveedor una vez y lo pasás a tus funciones.

### Amazon Bedrock (Por Defecto)

```python
from strands.models.bedrock import BedrockModel

# Claude Sonnet 4 en Bedrock
model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

# Amazon Nova Micro (rápido, bajo costo)
model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")

@ai_function(model=model)
def my_function(text: str) -> str:
    """Process: {text}"""
```

**Notas sobre los IDs de modelo de Bedrock:**
- El prefijo `us.` habilita la **inferencia cross-region** — AWS enruta tu solicitud a cualquier región US disponible
- Sin el prefijo (ej: `anthropic.claude-sonnet-4-20250514-v1:0`), la solicitud va solo a tu región configurada
- Bedrock requiere credenciales de AWS y que el acceso al modelo esté habilitado en tu cuenta

### OpenAI

```python
from strands.models.openai import OpenAIModel

model = OpenAIModel(
    client_args={"api_key": "sk-..."},
    model_id="gpt-4o"
)

@ai_function(model=model)
def my_function(text: str) -> str:
    """Process: {text}"""
```

### Sin Modelo Especificado (Por Defecto de la Biblioteca)

Si no especificás un modelo, la biblioteca usa su valor por defecto (Amazon Bedrock con un modelo predeterminado):

```python
@ai_function  # o @ai_function()
def my_function(text: str) -> str:
    """Process: {text}"""
```

---

## 8. Configuración y Configs Reutilizables

Cuando tenés muchas AI Functions, no querés repetir la misma configuración en cada una. El objeto `AIFunctionConfig` te permite definir configuraciones reutilizables.

### Definiendo Configs

```python
from ai_functions import ai_function, AIFunctionConfig

class Configs:
    FAST = AIFunctionConfig(
        model="global.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    DATA_ANALYSIS = AIFunctionConfig(
        code_execution_mode="local",
        code_executor_additional_imports=["pandas.*", "numpy.*"],
    )
```

### Usando Configs

```python
@ai_function(config=Configs.FAST)
def quick_classify(text: str) -> str:
    """Classify: {text}"""

@ai_function(config=Configs.DATA_ANALYSIS)
def process_data(data: str) -> "pd.DataFrame":
    """Load and process: {data}"""
```

### Sobrescribiendo Configuraciones

Podés sobrescribir configuraciones específicas para una función particular:

```python
@ai_function(config=Configs.FAST, tools=[web_search])
def research(topic: str) -> str:
    """Research: {topic}"""
```

---

## 9. Modo de Ejecución de Código — Integración con Python

Por defecto, las AI Functions trabajan con texto: envían un prompt y parsean la respuesta textual. Pero a veces necesitás que la IA realmente **escriba y ejecute código** — por ejemplo, para procesar un DataFrame o crear un gráfico.

### Habilitando la Ejecución de Código

```python
@ai_function(
    code_execution_mode="local",
    code_executor_additional_imports=["pandas.*", "numpy.*"]
)
def analyze_data(path: str) -> "pd.DataFrame":
    """
    Load the file at {path}, inspect its contents, and return
    a DataFrame with columns: [date, amount, category]
    """
```

Cuando el modo de ejecución de código es `"local"`:

1. La IA genera código Python para resolver la tarea
2. La biblioteca ejecuta ese código en un entorno local de Python
3. El resultado se devuelve como un objeto nativo de Python

### El Parámetro `code_executor_additional_imports`

Esto controla qué bibliotecas puede usar la IA en su código generado. Usá patrones glob:

```python
code_executor_additional_imports=["pandas.*", "plotly.*", "sqlite3", "json"]
```

### Advertencia de Seguridad

> **Precaución:** La ejecución local de código ejecuta código Python en tu máquina sin sandboxing completo. La biblioteca valida el código usando análisis AST y restringe las importaciones, pero no es un sandbox de seguridad. Para uso en producción, ejecutá dentro de un contenedor Docker u otro entorno aislado.

### Deshabilitando la Ejecución de Código

Establecé `code_execution_mode="disabled"` para evitar que la IA genere código. Esto se recomienda para entradas no confiables.

---

## 10. Herramientas — Dándole Superpoderes a tus Funciones

Las AI Functions pueden usar **herramientas** — capacidades externas que el agente de IA puede invocar durante la ejecución. Este es el mismo concepto que "function calling" o "tool use" en las APIs de LLMs.

### Usando Herramientas de Strands

```python
from strands_tools import file_read, file_write
from typing import Literal

@ai_function(tools=[file_read, file_write])
def summarize_file(path: str, output_path: str) -> Literal["done"]:
    """
    Read the file {path} and write a summary to {output_path}.
    """
```

La IA puede llamar a `file_read` para leer el contenido del archivo y `file_write` para guardar el resumen.

### AI Functions como Herramientas de Otras AI Functions

Uno de los patrones más poderosos es usar AI Functions como herramientas de otras AI Functions. Esto crea sistemas multi-agente:

```python
@ai_function(tools=[web_search])
def websearch(query: str) -> str:
    """Search the web for: {query} and return a summary of findings."""

@ai_function(tools=[websearch])
def report_writer(topic: str) -> str:
    """Research the following topic and write a report: {topic}"""
```

En este ejemplo:
- `report_writer` es un agente de IA con acceso a `websearch` como herramienta
- Cuando `report_writer` necesita información, llama a `websearch`
- `websearch` es a su vez un agente de IA que usa `web_search` para buscar datos
- El resultado fluye de vuelta a `report_writer` para completar el reporte

---

## 11. Funciones Asíncronas y Flujos Paralelos

Las AI Functions pueden ser asíncronas, habilitando la ejecución paralela — crítico para el rendimiento cuando necesitás hacer múltiples llamadas a la IA.

### Definiendo AI Functions Asíncronas

```python
@ai_function
async def research_news(stock: str) -> str:
    """Research and summarize current news about: {stock}"""

@ai_function
async def research_price(stock: str) -> str:
    """Get the current price information for: {stock}"""
```

### Ejecutando en Paralelo

```python
import asyncio

async def stock_research(stock: str):
    # Ejecutar ambas funciones de investigación simultáneamente
    news, price = await asyncio.gather(
        research_news(stock),
        research_price(stock)
    )
    return {"news": news, "price": price}

# Ejecutar el flujo asíncrono
result = asyncio.run(stock_research("AAPL"))
```

Sin async, estas dos llamadas se ejecutarían secuencialmente (una después de la otra). Con async y `asyncio.gather`, se ejecutan al mismo tiempo — reduciendo el tiempo total aproximadamente a la mitad.

### Combinando Sync y Async

Podés mezclar funciones sincrónicas y asíncronas en un flujo de trabajo. Las funciones sync bloquean hasta completarse; las funciones async pueden ejecutarse concurrentemente:

```python
@ai_function
async def research_news(stock: str) -> str:
    """Research news for: {stock}"""

@ai_function  # sync — se ejecuta después de que todo el trabajo async se complete
def write_report(stock: str, news: str, prices: str) -> str:
    """Write a report for {stock} using: {news} and {prices}"""

async def workflow(stock: str):
    news, prices = await asyncio.gather(
        research_news(stock),
        research_price(stock)
    )
    # Llamada sync — ensamblaje final
    report = write_report(stock, news, prices)
    return report
```

---

## 12. Memoria y Optimización

AI Functions incluyen un sistema avanzado para **memoria persistente** y **optimización de flujos de trabajo**. Esto permite que tus flujos de IA aprendan y mejoren con el tiempo basándose en feedback.

### Los Tres Componentes

| Componente | Qué Hace |
|------------|----------|
| **Backend de Memoria** | Almacena parámetros con nombre (fragmentos de prompt, reglas, código) |
| **Grafo de Computación** | Registra qué parámetros contribuyeron a cada salida |
| **Optimizador** | Propaga feedback hacia atrás a través del grafo para actualizar parámetros |

Pensalo como machine learning, pero en lugar de ajustar pesos numéricos, el optimizador ajusta **parámetros basados en texto** usando feedback en lenguaje natural.

### Ejemplo Rápido

```python
from pydantic import BaseModel, Field
from ai_functions import ai_function, Result
from ai_functions.memory import JSONMemoryBackend
from ai_functions.optimizer import TextGradOptimizer

# 1. Definir una función que usa un parámetro de guía
@ai_function
def write_summary(text: str, tone_guidelines: str) -> str:
    """Summarize the following text:
    {text}

    Follow these tone guidelines:
    {tone_guidelines}
    """

# 2. Definir el esquema de memoria
class WritingMemory(BaseModel):
    tone_guidelines: str = Field(
        "No specific guidelines yet.",
        description="Guidelines for the tone of the writing"
    )

# 3. Crear backend de memoria y optimizador
memory = JSONMemoryBackend(WritingMemory, actor_id="user-1", path="memory.json")
optimizer = TextGradOptimizer()

# 4. Usar .trace() para construir el grafo de computación
guidelines = memory.recall("tone_guidelines")
result: Result[str] = write_summary.trace("some long document...", tone_guidelines=guidelines)
print(result.value)  # La salida real

# 5. Proveer feedback y optimizar
optimizer.backward(result, "The summary should be more concise and use bullet points.")
optimizer.consolidate(result)

# ¡La próxima vez que ejecutes esto, `memory.recall("tone_guidelines")` devolverá
# guías actualizadas que incorporan el feedback!
memory.close()
```

### Tipos de Parámetros de Memoria

| Tipo | Descripción |
|------|-------------|
| `str` | Un parámetro de texto (fragmento de prompt, reglas, etc.) |
| `list[str]` | Una lista de entradas (cada una es una pieza separada de conocimiento) |
| `Procedural` | Almacena código Python reutilizable que el optimizador puede generar y refinar |
| `Frozen[str]` | Un parámetro que se lee pero nunca es modificado por el optimizador |

### Métodos de Recuperación

```python
# Recall completo — devuelve el valor completo del parámetro
guidelines = memory.recall("tone_guidelines")

# Búsqueda — devuelve las top-k entradas coincidentes (para parámetros tipo lista)
matches = memory.search("learned_rules", query="date formatting", k=3)

# Consulta — responde una pregunta usando el contenido del parámetro
answer = memory.query("learned_rules", query="What do we know about date formatting?")
```

### Memoria como Herramientas de Agente

Los backends de memoria pueden exponer sus parámetros como herramientas, dejando que la IA decida cuándo recuperar información:

```python
tools = memory.tool_provider("preferences", "visited")

@ai_function(tools=[tools])
def travel_assistant(request: str) -> str:
    """You are a travel planning assistant with access to memory.
    User request: {request}"""
```

---

## 13. Ejemplo Real: Pipeline del Log Analyzer

Este proyecto (Log Analyzer) demuestra un uso de grado producción de AI Functions. Así es como funciona el pipeline de análisis:

### Las AI Functions

```python
from typing import Literal
from pydantic import BaseModel
from ai_functions import ai_function
from ai_functions.types import PostConditionResult
from strands.models.bedrock import BedrockModel

# Configurar modelo — compartido entre todas las funciones
_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

# Paso 1: Clasificar severidad
@ai_function(model=_MODEL)
def classify_severity(log_entry: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Classify the severity level of this log entry.

    Log entry: {log_entry}

    Analyze the log message and determine its severity level.
    Consider error indicators, warning signs, and the overall tone."""

# Paso 2: Categorizar
@ai_function(model=_MODEL)
def categorize_log(log_entry: str) -> str:
    """Categorize this log entry into exactly one category.

    Log entry: {log_entry}

    Available categories: authentication, networking, database, filesystem,
    performance, security, configuration, application, deployment

    Return ONLY the category name, nothing else."""

# Paso 3: Resumir (con post-condición)
def check_summary_length(summary: str):
    word_count = len(summary.split())
    assert word_count <= 30, f"Summary has {word_count} words, max is 30"

@ai_function(model=_MODEL, post_conditions=[check_summary_length], max_attempts=3)
def summarize_log(log_entry: str, severity: str, category: str) -> str:
    """Summarize this log entry in a single sentence of at most 30 words.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}"""

# Paso 4: Sugerir corrección
@ai_function(model=_MODEL)
def suggest_fix(log_entry: str, severity: str, category: str, summary: str) -> str:
    """Suggest an actionable fix for this log entry.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}
    Summary: {summary}

    Mention concrete steps, tools, or configurations an engineer should use."""

# Paso 5: Validación potenciada por IA
@ai_function(model=_MODEL)
def validate_suggestion_quality(result: "LogAnalysis") -> PostConditionResult:
    """Evaluate whether this fix suggestion is actionable and specific.

    Suggestion: {result.suggestion}
    Category: {result.category}

    A good suggestion should mention specific steps, tools, or configurations."""
```

### La Orquestación del Pipeline

```python
def analyze_log(log_entry: str) -> LogAnalysis:
    """Ejecuta el pipeline completo de análisis de IA en una entrada de log."""

    # Encadenar las AI functions — cada resultado alimenta al siguiente
    severity = classify_severity(log_entry)
    category = categorize_log(log_entry)
    summary = summarize_log(log_entry, severity, category)

    if severity in ("WARNING", "ERROR", "CRITICAL"):
        suggestion = suggest_fix(log_entry, severity, category, summary)
        result = LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion=suggestion,
            category=category,
            confidence="high",
        )
        # Validar y reintentar si es necesario
        for _attempt in range(2):
            validation = validate_suggestion_quality(result)
            if validation.passed:
                break
            suggestion = suggest_fix(log_entry, severity, category, summary)
            result = LogAnalysis(
                log_level=severity, summary=summary,
                suggestion=suggestion, category=category, confidence="high",
            )
        else:
            result = result.model_copy(update={"confidence": "low"})
        return result
    else:
        return LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion="N/A",
            category=category,
            confidence="high",
        )
```

### Patrones Clave Demostrados

1. **Funciones encadenadas** — La salida de cada paso alimenta al siguiente (`severity` → `summarize_log`)
2. **Lógica condicional** — Sugerencias de corrección solo para severidad WARNING+
3. **Post-condiciones programáticas** — `check_summary_length` impone el límite de 30 palabras
4. **Post-condiciones de IA** — `validate_suggestion_quality` usa IA para evaluar calidad
5. **Reintento con degradación** — Si la validación falla dos veces, la confianza se degrada a `"low"` en lugar de fallar por completo
6. **Modelo compartido** — Todas las funciones usan la misma instancia `_MODEL`

---

## 14. Mejores Prácticas y Consejos

### Escribiendo Buenos Prompts

- **Sé específico:** "Classify as one of: DEBUG, INFO, WARNING, ERROR, CRITICAL" es mejor que "Classify the log level"
- **Incluí restricciones en el prompt Y como post-condiciones:** La IA es mejor siguiendo reglas cuando se le recuerda de ambas formas
- **Usá marcadores `{parameter}`:** Hacen el prompt dinámico y legible
- **Estructurá prompts complejos:** Usá listas numeradas, etiquetas estilo XML, o formato markdown

### Diseñando Post-Condiciones

- **Empezá con verificaciones determinísticas:** Conteo de palabras, validación de formato, campos requeridos
- **Agregá verificaciones de IA para calidad:** "¿Es esta sugerencia accionable?" — cosas que el código no puede verificar fácilmente
- **Establecé `max_attempts` razonable:** 3 es un buen valor por defecto. Demasiados desperdicia tokens; muy pocos puede no converger.
- **Escribí mensajes de error claros:** La IA usa tu mensaje de aserción para entender qué salió mal

### Consideraciones de Rendimiento

- **Usá modelos más rápidos para tareas simples:** Clasificación y categorización pueden usar modelos más pequeños/baratos (como Haiku o Nova Micro), mientras que análisis complejos pueden necesitar un modelo más grande (como Sonnet)
- **Usá async para tareas independientes:** Si dos AI Functions no dependen una de la otra, ejecutalas en paralelo con `asyncio.gather`
- **Minimizá reintentos de post-condiciones:** Buenos prompts reducen la necesidad de reintentos

### Compartiendo Configuraciones

```python
# Definir configs una vez, reutilizar en todas partes
class ModelConfig:
    FAST = AIFunctionConfig(model="us.amazon.nova-micro-v1:0")
    QUALITY = AIFunctionConfig(model="us.anthropic.claude-sonnet-4-20250514-v1:0")
```

### Manejo de Errores

Las AI Functions pueden lanzar excepciones (errores de red, errores de modelo, reintentos agotados). Siempre manejalos de forma elegante:

```python
try:
    result = classify_severity(log_entry)
except Exception as e:
    logger.error(f"AI analysis failed: {e}")
    result = "UNKNOWN"
```

---

## 15. Solución de Problemas Comunes

### "Unable to resolve AWS account"

- Asegurate de que `AWS_PROFILE` esté configurado o las credenciales de AWS estén configuradas
- Para Bedrock, verificá que tengas el acceso al modelo habilitado en la consola de AWS

### "AccessDeniedException" en Bedrock

- El modelo puede requerir permisos de AWS Marketplace. Probá los modelos Amazon Nova (propios de Amazon, sin necesidad de marketplace)
- Algunos modelos están marcados como `LEGACY` en ciertas regiones — usá un modelo activo o una región diferente

### La post-condición nunca pasa

- Verificá que `max_attempts` sea suficientemente alto (al menos 3)
- Asegurate de que tus mensajes de error sean claros — la IA necesita entender qué está mal
- Considerá relajar la restricción si es demasiado estricta para la capacidad del modelo

### La función devuelve el tipo incorrecto

- Verificá que la anotación del tipo de retorno sea correcta
- Para tipos `Literal`, asegurate de que los valores exactos coincidan con lo que la IA produciría naturalmente
- Para modelos Pydantic, asegurate de que todos los campos requeridos estén definidos

### Ejecución lenta

- Cada llamada a una AI Function es un viaje de ida y vuelta al proveedor del modelo — minimizá la cantidad de llamadas
- Usá async + `asyncio.gather` para llamadas independientes
- Considerá usar modelos más pequeños/rápidos para tareas simples

---

## 16. Referencia Rápida

### Parámetros del Decorador

```python
@ai_function(
    model=...,                          # Instancia del proveedor de modelo
    config=...,                         # AIFunctionConfig para configuraciones compartidas
    post_conditions=[fn1, fn2],         # Lista de funciones de validación
    max_attempts=3,                     # Máximo de reintentos por fallo de post-condición
    tools=[tool1, tool2],               # Herramientas externas que la IA puede usar
    code_execution_mode="local",        # Habilitar ejecución de código Python
    code_executor_additional_imports=[], # Imports permitidos para ejecución de código
    system_prompt="...",                 # Prompt de sistema personalizado
    description="...",                  # Descripción cuando se usa como herramienta
)
def my_function(arg: str) -> ReturnType:
    """Template de prompt con marcadores {arg}."""
```

### Hoja de Referencia de Imports

```python
# Core
from ai_functions import ai_function, AIFunctionConfig, Result

# Tipo de resultado de post-condición
from ai_functions.types import PostConditionResult

# Sistema de memoria
from ai_functions.memory import JSONMemoryBackend
from ai_functions.memory import Procedural, Frozen
from ai_functions.optimizer import TextGradOptimizer
from ai_functions.utils import show_graph

# Proveedores de modelo (de strands-agents)
from strands.models.bedrock import BedrockModel
from strands.models.openai import OpenAIModel
```

### Patrones de Post-Condiciones

```python
# Patrón 1: Assert (lanza excepción al fallar)
def check_length(output: str):
    assert len(output.split()) <= 50, "Too long"

# Patrón 2: Devolver PostConditionResult
def check_format(output: str) -> PostConditionResult:
    if not output.startswith("##"):
        return PostConditionResult(passed=False, message="Must start with ##")
    return PostConditionResult(passed=True)

# Patrón 3: Validación potenciada por IA
@ai_function
def check_quality(output: str) -> PostConditionResult:
    """Is this output high quality? {output}"""

# Patrón 4: Acceder a entradas originales
def validate(_answer, original_input: str):
    assert original_input in _answer, "Must reference the input"
```

### Proporcionando Prompts

```python
# Método 1: Template en docstring (el más simple)
@ai_function
def my_func(text: str) -> str:
    """Translate {text} to French."""

# Método 2: Devolver un string desde el cuerpo de la función (más control)
@ai_function
def my_func(text: str) -> str:
    assert text, "text cannot be empty"
    return f"Translate the following to French: {text}"

# Método 3: Devolver un t-string template (Python 3.14+, ideal para multi-línea)
@ai_function
def my_func(text: str) -> str:
    return t"""
    Translate the following to French:
    {text}
    """
```

---

## Lecturas Adicionales

- **Repositorio Oficial:** [github.com/strands-labs/ai-functions](https://github.com/strands-labs/ai-functions)
- **Tutorial Oficial:** [docs/tutorial.md](https://github.com/strands-labs/ai-functions/blob/main/docs/tutorial.md)
- **Ejemplos:** [examples/](https://github.com/strands-labs/ai-functions/tree/main/examples)
- **SDK de Strands Agents:** [strandsagents.com](https://strandsagents.com)
- **Este Proyecto (Log Analyzer):** Ver `documentation/design.md` y `documentation/architecture.md` para una implementación real usando AI Functions
