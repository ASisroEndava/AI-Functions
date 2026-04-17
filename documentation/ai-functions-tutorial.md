# AI Functions Library — Complete Tutorial

> **Library:** `strands-ai-functions` (import as `ai_functions`)
> **GitHub:** [strands-labs/ai-functions](https://github.com/strands-labs/ai-functions)
> **Requires:** Python 3.12+ (3.14+ recommended for all features)

---

## Table of Contents

1. [What Is AI Functions?](#1-what-is-ai-functions)
2. [Installation and Setup](#2-installation-and-setup)
3. [Your First AI Function](#3-your-first-ai-function)
4. [How It Works Under the Hood](#4-how-it-works-under-the-hood)
5. [Return Types — From Strings to Complex Objects](#5-return-types--from-strings-to-complex-objects)
6. [Post-Conditions — Making AI Reliable](#6-post-conditions--making-ai-reliable)
7. [Choosing a Model Provider](#7-choosing-a-model-provider)
8. [Configuration and Reusable Configs](#8-configuration-and-reusable-configs)
9. [Code Execution Mode — Python Integration](#9-code-execution-mode--python-integration)
10. [Tools — Giving Your Functions Superpowers](#10-tools--giving-your-functions-superpowers)
11. [Async Functions and Parallel Workflows](#11-async-functions-and-parallel-workflows)
12. [Memory and Optimization](#12-memory-and-optimization)
13. [Real-World Example: Log Analyzer Pipeline](#13-real-world-example-log-analyzer-pipeline)
14. [Best Practices and Tips](#14-best-practices-and-tips)
15. [Troubleshooting Common Issues](#15-troubleshooting-common-issues)
16. [Quick Reference](#16-quick-reference)

---

## 1. What Is AI Functions?

Imagine you could write a Python function where, instead of writing the logic yourself, you describe **what you want the function to do** in plain English — and an AI model figures out how to do it. That is exactly what the `ai_functions` library does.

### The Core Idea

In traditional programming, you write explicit instructions:

```python
# Traditional approach — you write every step
def classify_sentiment(text: str) -> str:
    positive_words = ["good", "great", "excellent"]
    negative_words = ["bad", "terrible", "awful"]
    # ... lots of manual logic
```

With AI Functions, you describe the **intent** and the AI handles the reasoning:

```python
# AI Functions approach — you describe what you want
from ai_functions import ai_function

@ai_function
def classify_sentiment(text: str) -> str:
    """Classify the sentiment of the following text as 'positive', 'negative', or 'neutral'.
    
    Text: {text}
    """
```

Both functions are called the same way: `classify_sentiment("This movie was great!")`. The difference is that the AI Function sends your description to a Large Language Model (LLM), which analyzes the text and returns the result.

### Why Not Just Call an AI API Directly?

You could call an AI model directly using its API, but AI Functions give you several advantages:

- **Type safety** — The library ensures the AI returns data in the exact type you specified (`str`, `int`, Pydantic model, etc.)
- **Post-conditions** — You can define rules that the AI's output must satisfy. If they fail, the AI automatically retries.
- **Composability** — AI Functions are regular Python functions. You can chain them, pass results between them, and build complex pipelines.
- **Provider independence** — Switch between Amazon Bedrock, OpenAI, or other providers by changing one line.

---

## 2. Installation and Setup

### Install the Library

```bash
# Using pip
pip install strands-ai-functions

# Using uv (recommended)
uv add strands-ai-functions
```

### Configure Credentials

AI Functions need access to an AI model provider. The default provider is **Amazon Bedrock**.

**For Amazon Bedrock:**
1. Install and configure the AWS CLI
2. Ensure your AWS credentials are set (via `~/.aws/credentials`, environment variables, or IAM role)
3. Enable the desired model in the Bedrock console

**For OpenAI:**
1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. Pass it when configuring the model (see [Section 7](#7-choosing-a-model-provider))

### Verify It Works

```python
from ai_functions import ai_function

@ai_function
def say_hello(name: str) -> str:
    """Say hello to {name} in a creative way."""

print(say_hello("World"))
# Output: something like "Greetings, World! May your day be filled with wonder!"
```

If this runs without errors, your setup is complete.

---

## 3. Your First AI Function

Let's build a simple translator to understand the basics.

### Step 1: Import the Decorator

```python
from ai_functions import ai_function
```

### Step 2: Define Your Function

```python
@ai_function
def translate_text(text: str, lang: str) -> str:
    """
    Translate the text below to the following language: {lang}.
    ---
    {text}
    """
```

Let's break this down:

| Element | Purpose |
|---------|---------|
| `@ai_function` | Tells the library this function is powered by AI |
| `text: str, lang: str` | Regular Python parameters — the inputs |
| `-> str` | The return type — the AI must return a string |
| The docstring | The **prompt** sent to the AI model. `{text}` and `{lang}` are replaced with the actual argument values |

### Step 3: Call It Like Any Function

```python
result = translate_text("Hello, how are you?", lang="Spanish")
print(result)
# Output: "Hola, ¿cómo estás?"
```

**Key insight:** From the caller's perspective, `translate_text` is just a normal function. You don't need to know it's powered by AI. This is what makes AI Functions so powerful — they fit naturally into any codebase.

### The Docstring Is Your Prompt

The docstring is the most important part. It tells the AI what to do. The library:

1. Takes your docstring
2. Replaces `{parameter_name}` placeholders with the actual argument values
3. Sends the resulting text to the AI model
4. Parses the AI's response into the declared return type
5. Returns the result

**Tips for writing good docstrings/prompts:**

- Be specific about what you want
- Mention constraints explicitly (e.g., "Return ONLY the category name, nothing else")
- Use examples when the task is ambiguous
- Structure complex prompts with bullet points or numbered lists

---

## 4. How It Works Under the Hood

When you call an AI Function, here is what happens step by step:

```
Your Code                    AI Functions Library              AI Model (e.g., Bedrock)
─────────                    ────────────────────              ──────────────────────────
                                                              
classify("error log")  ──►   1. Read the docstring            
                             2. Replace {log_entry}            
                                with "error log"               
                             3. Build the full prompt    ──►   4. AI reads the prompt
                                                               5. AI generates response
                             6. Receive AI response     ◄──   
                             7. Parse into return type         
                             8. Check post-conditions          
                             9. If failed → retry with         
                                error feedback          ──►   10. AI corrects response
                            11. Return final result     ◄──   
result = "ERROR"       ◄──                                    
```

### The Self-Correcting Loop

This is what makes AI Functions different from raw API calls. If you define post-conditions (rules the output must follow), the library:

1. Checks every post-condition against the output
2. If any fail, sends the error messages back to the AI
3. The AI tries again, knowing what went wrong
4. Repeats until all conditions pass or `max_attempts` is reached

This means your pipeline doesn't silently produce wrong results — it either gives you a correct answer or tells you it couldn't.

---

## 5. Return Types — From Strings to Complex Objects

AI Functions can return virtually any Python type. The library handles the conversion automatically.

### Primitive Types

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

### Literal Types (Constrained Choices)

When you want the AI to choose from a fixed set of options, use `Literal`:

```python
from typing import Literal

@ai_function
def classify_severity(log_entry: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Classify the severity level of this log entry.
    
    Log entry: {log_entry}
    """
```

The AI **must** return one of those exact values. If it tries to return something else (like "WARN" or "High"), the library will prompt it to correct the answer.

### Pydantic Models (Structured Output)

This is where AI Functions really shine. You can define complex structured outputs using Pydantic:

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

The AI returns a fully populated `LogAnalysis` object with all fields filled in. You can then access them like any Python object:

```python
result = analyze_log("Connection refused to database at 10.0.2.15:5432")
print(result.log_level)    # "ERROR"
print(result.summary)      # "Database connection failure on port 5432"
print(result.suggestion)   # "Check database server status and network connectivity"
```

### Complex Nested Models

```python
class IncidentReport(BaseModel):
    title: str
    root_cause: str
    affected_services: list[str]
    severity: Literal["low", "medium", "high", "critical"]
    recommended_actions: list[str]
    related_log_lines: list[int]
```

The AI will populate every field, including lists of strings and integers.

### Native Python Objects (with Code Execution)

With code execution mode enabled (see [Section 9](#9-code-execution-mode--python-integration)), AI Functions can return native Python objects like `pandas.DataFrame`, `numpy` arrays, or any other type.

---

## 6. Post-Conditions — Making AI Reliable

Post-conditions are the **key innovation** of AI Functions. They transform unreliable AI outputs into reliable, validated results.

### The Problem They Solve

AI models are non-deterministic — they might:
- Return a summary that's too long
- Forget to include required fields
- Give vague suggestions instead of specific ones

Without post-conditions, these errors silently propagate through your pipeline. With post-conditions, they are caught and corrected automatically.

### Method 1: Python Functions (Deterministic Checks)

The simplest post-condition is a regular Python function that raises an `AssertionError` if the output is invalid:

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

What happens when you call `summarize_log`:

1. The AI generates a summary
2. `check_summary_length` counts the words
3. If the count exceeds 30, the assertion fails
4. The library sends the error message back to the AI: *"Summary has 45 words, max is 30"*
5. The AI tries again, this time keeping it shorter
6. This repeats up to `max_attempts=3` times

### Method 2: Return PostConditionResult

Instead of assertions, you can return a `PostConditionResult` object for more control:

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

### Method 3: AI-Powered Post-Conditions

Here's the truly powerful part — your post-conditions can themselves be AI Functions. This lets you validate things that are hard to check with code, like "Is this suggestion specific and actionable?"

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

This AI post-condition evaluates the quality of another AI's output. If the suggestion is too vague, it provides feedback that helps the original AI improve.

### Combining Multiple Post-Conditions

You can apply multiple post-conditions to a single function. They are all checked in parallel, and all failures are reported to the AI at once:

```python
@ai_function(
    post_conditions=[check_length, check_format, check_quality],
    max_attempts=5
)
def generate_report(data: str) -> Report:
    """Generate a report from the following data: {data}"""
```

### Post-Conditions That Access Original Inputs

Post-conditions can request the original function arguments by name:

```python
def run_tests(_answer, feature: FeatureRequest):
    """Ignores the AI answer, validates by running actual tests."""
    retcode = pytest.main(feature.test_files)
    if retcode:
        raise RuntimeError("Tests failed")

@ai_function(post_conditions=[run_tests])
def implement_feature(feature: FeatureRequest) -> str:
    """Implement the following feature: {feature.description}"""
```

The `_answer` parameter receives the AI's output, and `feature` receives the original input argument. This pattern is useful when validation depends on external state (like running tests).

---

## 7. Choosing a Model Provider

AI Functions support multiple AI model providers. You configure the provider once and pass it to your functions.

### Amazon Bedrock (Default)

```python
from strands.models.bedrock import BedrockModel

# Claude Sonnet 4 on Bedrock
model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

# Amazon Nova Micro (fast, low cost)
model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")

@ai_function(model=model)
def my_function(text: str) -> str:
    """Process: {text}"""
```

**Notes on Bedrock model IDs:**
- The `us.` prefix enables **cross-region inference** — AWS routes your request to any available US region
- Without the prefix (e.g., `anthropic.claude-sonnet-4-20250514-v1:0`), the request goes to your configured region only
- Bedrock requires AWS credentials and model access to be enabled in your account

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

### No Model Specified (Library Default)

If you don't specify a model, the library uses its default (Amazon Bedrock with a default model):

```python
@ai_function  # or @ai_function()
def my_function(text: str) -> str:
    """Process: {text}"""
```

---

## 8. Configuration and Reusable Configs

When you have many AI Functions, you don't want to repeat the same settings on each one. The `AIFunctionConfig` object lets you define reusable configurations.

### Defining Configs

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

### Using Configs

```python
@ai_function(config=Configs.FAST)
def quick_classify(text: str) -> str:
    """Classify: {text}"""

@ai_function(config=Configs.DATA_ANALYSIS)
def process_data(data: str) -> "pd.DataFrame":
    """Load and process: {data}"""
```

### Overriding Config Settings

You can override specific settings for a particular function:

```python
@ai_function(config=Configs.FAST, tools=[web_search])
def research(topic: str) -> str:
    """Research: {topic}"""
```

---

## 9. Code Execution Mode — Python Integration

By default, AI Functions work with text: they send a prompt and parse the text response. But sometimes you need the AI to actually **write and run code** — for example, to process a DataFrame or create a chart.

### Enabling Code Execution

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

When code execution mode is `"local"`:

1. The AI generates Python code to solve the task
2. The library executes that code in a local Python environment
3. The result is returned as a native Python object

### The `code_executor_additional_imports` Parameter

This controls which libraries the AI can use in its generated code. Use glob patterns:

```python
code_executor_additional_imports=["pandas.*", "plotly.*", "sqlite3", "json"]
```

### Security Warning

> **Caution:** Local code execution runs Python code on your machine without full sandboxing. The library validates the code using AST analysis and restricts imports, but it is not a security sandbox. For production use, run inside a Docker container or other isolated environment.

### Disabling Code Execution

Set `code_execution_mode="disabled"` to prevent the AI from generating code. This is recommended for untrusted inputs.

---

## 10. Tools — Giving Your Functions Superpowers

AI Functions can use **tools** — external capabilities that the AI agent can invoke during execution. This is the same concept as "function calling" or "tool use" in LLM APIs.

### Using Strands Tools

```python
from strands_tools import file_read, file_write
from typing import Literal

@ai_function(tools=[file_read, file_write])
def summarize_file(path: str, output_path: str) -> Literal["done"]:
    """
    Read the file {path} and write a summary to {output_path}.
    """
```

The AI can call `file_read` to read the file contents and `file_write` to save the summary.

### AI Functions as Tools for Other AI Functions

One of the most powerful patterns is using AI Functions as tools for other AI Functions. This creates multi-agent systems:

```python
@ai_function(tools=[web_search])
def websearch(query: str) -> str:
    """Search the web for: {query} and return a summary of findings."""

@ai_function(tools=[websearch])
def report_writer(topic: str) -> str:
    """Research the following topic and write a report: {topic}"""
```

In this example:
- `report_writer` is an AI agent with access to `websearch` as a tool
- When `report_writer` needs information, it calls `websearch`
- `websearch` is itself an AI agent that uses `web_search` to find data
- The result flows back to `report_writer` to complete the report

---

## 11. Async Functions and Parallel Workflows

AI Functions can be asynchronous, enabling parallel execution — critical for performance when you need to make multiple AI calls.

### Defining Async AI Functions

```python
@ai_function
async def research_news(stock: str) -> str:
    """Research and summarize current news about: {stock}"""

@ai_function
async def research_price(stock: str) -> str:
    """Get the current price information for: {stock}"""
```

### Running in Parallel

```python
import asyncio

async def stock_research(stock: str):
    # Run both research functions simultaneously
    news, price = await asyncio.gather(
        research_news(stock),
        research_price(stock)
    )
    return {"news": news, "price": price}

# Run the async workflow
result = asyncio.run(stock_research("AAPL"))
```

Without async, these two calls would run sequentially (one after the other). With async and `asyncio.gather`, they run at the same time — cutting the total time roughly in half.

### Combining Sync and Async

You can mix sync and async functions in a workflow. Sync functions block until they complete; async functions can run concurrently:

```python
@ai_function
async def research_news(stock: str) -> str:
    """Research news for: {stock}"""

@ai_function  # sync — runs after all async work completes
def write_report(stock: str, news: str, prices: str) -> str:
    """Write a report for {stock} using: {news} and {prices}"""

async def workflow(stock: str):
    news, prices = await asyncio.gather(
        research_news(stock),
        research_price(stock)
    )
    # Sync call — final assembly
    report = write_report(stock, news, prices)
    return report
```

---

## 12. Memory and Optimization

AI Functions include an advanced system for **persistent memory** and **workflow optimization**. This allows your AI workflows to learn and improve over time based on feedback.

### The Three Components

| Component | What It Does |
|-----------|-------------|
| **Memory Backend** | Stores named parameters (prompt fragments, rules, code) |
| **Computation Graph** | Tracks which parameters contributed to each output |
| **Optimizer** | Propagates feedback backward through the graph to update parameters |

Think of it like machine learning, but instead of adjusting numerical weights, the optimizer adjusts **text-based parameters** using natural language feedback.

### Quick Example

```python
from pydantic import BaseModel, Field
from ai_functions import ai_function, Result
from ai_functions.memory import JSONMemoryBackend
from ai_functions.optimizer import TextGradOptimizer

# 1. Define a function that uses a guideline parameter
@ai_function
def write_summary(text: str, tone_guidelines: str) -> str:
    """Summarize the following text:
    {text}

    Follow these tone guidelines:
    {tone_guidelines}
    """

# 2. Define the memory schema
class WritingMemory(BaseModel):
    tone_guidelines: str = Field(
        "No specific guidelines yet.",
        description="Guidelines for the tone of the writing"
    )

# 3. Create memory backend and optimizer
memory = JSONMemoryBackend(WritingMemory, actor_id="user-1", path="memory.json")
optimizer = TextGradOptimizer()

# 4. Use .trace() to build the computation graph
guidelines = memory.recall("tone_guidelines")
result: Result[str] = write_summary.trace("some long document...", tone_guidelines=guidelines)
print(result.value)  # The actual output

# 5. Provide feedback and optimize
optimizer.backward(result, "The summary should be more concise and use bullet points.")
optimizer.consolidate(result)

# Next time you run this, `memory.recall("tone_guidelines")` will return
# updated guidelines that incorporate the feedback!
memory.close()
```

### Memory Parameter Types

| Type | Description |
|------|-------------|
| `str` | A text parameter (prompt fragment, rules, etc.) |
| `list[str]` | A list of entries (each is a separate piece of knowledge) |
| `Procedural` | Stores reusable Python code that the optimizer can generate and refine |
| `Frozen[str]` | A parameter that is read but never modified by the optimizer |

### Retrieval Methods

```python
# Full recall — returns the entire parameter value
guidelines = memory.recall("tone_guidelines")

# Search — returns top-k matching entries (for list parameters)
matches = memory.search("learned_rules", query="date formatting", k=3)

# Query — answers a question using the parameter content
answer = memory.query("learned_rules", query="What do we know about date formatting?")
```

### Memory as Agent Tools

Memory backends can expose their parameters as tools, letting the AI decide when to retrieve information:

```python
tools = memory.tool_provider("preferences", "visited")

@ai_function(tools=[tools])
def travel_assistant(request: str) -> str:
    """You are a travel planning assistant with access to memory.
    User request: {request}"""
```

---

## 13. Real-World Example: Log Analyzer Pipeline

This project (Log Analyzer) demonstrates a production-grade use of AI Functions. Here is how the analysis pipeline works:

### The AI Functions

```python
from typing import Literal
from pydantic import BaseModel
from ai_functions import ai_function
from ai_functions.types import PostConditionResult
from strands.models.bedrock import BedrockModel

# Configure model — shared across all functions
_MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

# Step 1: Classify severity
@ai_function(model=_MODEL)
def classify_severity(log_entry: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Classify the severity level of this log entry.

    Log entry: {log_entry}

    Analyze the log message and determine its severity level.
    Consider error indicators, warning signs, and the overall tone."""

# Step 2: Categorize
@ai_function(model=_MODEL)
def categorize_log(log_entry: str) -> str:
    """Categorize this log entry into exactly one category.

    Log entry: {log_entry}

    Available categories: authentication, networking, database, filesystem,
    performance, security, configuration, application, deployment

    Return ONLY the category name, nothing else."""

# Step 3: Summarize (with post-condition)
def check_summary_length(summary: str):
    word_count = len(summary.split())
    assert word_count <= 30, f"Summary has {word_count} words, max is 30"

@ai_function(model=_MODEL, post_conditions=[check_summary_length], max_attempts=3)
def summarize_log(log_entry: str, severity: str, category: str) -> str:
    """Summarize this log entry in a single sentence of at most 30 words.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}"""

# Step 4: Suggest fix
@ai_function(model=_MODEL)
def suggest_fix(log_entry: str, severity: str, category: str, summary: str) -> str:
    """Suggest an actionable fix for this log entry.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}
    Summary: {summary}

    Mention concrete steps, tools, or configurations an engineer should use."""

# Step 5: AI-powered validation
@ai_function(model=_MODEL)
def validate_suggestion_quality(result: "LogAnalysis") -> PostConditionResult:
    """Evaluate whether this fix suggestion is actionable and specific.

    Suggestion: {result.suggestion}
    Category: {result.category}

    A good suggestion should mention specific steps, tools, or configurations."""
```

### The Pipeline Orchestration

```python
def analyze_log(log_entry: str) -> LogAnalysis:
    """Run the full AI analysis pipeline on a single log entry."""

    # Chain the AI functions — each result feeds into the next
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
        # Validate and retry if needed
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

### Key Patterns Demonstrated

1. **Chained functions** — Each step's output feeds into the next (`severity` → `summarize_log`)
2. **Conditional logic** — Fix suggestions only for WARNING+ severity
3. **Programmatic post-conditions** — `check_summary_length` enforces the 30-word limit
4. **AI post-conditions** — `validate_suggestion_quality` uses AI to evaluate quality
5. **Retry with degradation** — If validation fails twice, confidence is downgraded to `"low"` instead of failing entirely
6. **Shared model** — All functions use the same `_MODEL` instance

---

## 14. Best Practices and Tips

### Writing Good Prompts

- **Be specific:** "Classify as one of: DEBUG, INFO, WARNING, ERROR, CRITICAL" is better than "Classify the log level"
- **Include constraints in the prompt AND as post-conditions:** AI is better at following rules when reminded in both ways
- **Use `{parameter}` placeholders:** They make the prompt dynamic and readable
- **Structure complex prompts:** Use numbered lists, XML-style tags, or markdown formatting

### Designing Post-Conditions

- **Start with deterministic checks:** Word count, format validation, required fields
- **Add AI checks for quality:** "Is this suggestion actionable?" — things code can't easily verify
- **Set reasonable `max_attempts`:** 3 is a good default. Too many wastes tokens; too few may not converge.
- **Write clear error messages:** The AI uses your assertion message to understand what went wrong

### Performance Considerations

- **Use faster models for simple tasks:** Classification and categorization can use smaller/cheaper models (like Haiku or Nova Micro), while complex analysis might need a larger model (like Sonnet)
- **Use async for independent tasks:** If two AI Functions don't depend on each other, run them in parallel with `asyncio.gather`
- **Minimize post-condition retries:** Good prompts reduce the need for retries

### Sharing Configurations

```python
# Define configs once, reuse everywhere
class ModelConfig:
    FAST = AIFunctionConfig(model="us.amazon.nova-micro-v1:0")
    QUALITY = AIFunctionConfig(model="us.anthropic.claude-sonnet-4-20250514-v1:0")
```

### Error Handling

AI Functions can raise exceptions (network errors, model errors, exhausted retries). Always handle them gracefully:

```python
try:
    result = classify_severity(log_entry)
except Exception as e:
    logger.error(f"AI analysis failed: {e}")
    result = "UNKNOWN"
```

---

## 15. Troubleshooting Common Issues

### "Unable to resolve AWS account"

- Ensure `AWS_PROFILE` is set or AWS credentials are configured
- For Bedrock, verify you have model access enabled in the AWS console

### "AccessDeniedException" on Bedrock

- The model may require AWS Marketplace permissions. Try Amazon Nova models (first-party, no marketplace needed)
- Some models are marked `LEGACY` in certain regions — use an active model or a different region

### Post-condition never passes

- Check that `max_attempts` is high enough (at least 3)
- Ensure your error messages are clear — the AI needs to understand what's wrong
- Consider relaxing the constraint if it's too strict for the model's capability

### Function returns wrong type

- Verify the return type annotation is correct
- For `Literal` types, ensure the exact values match what the AI would naturally produce
- For Pydantic models, ensure all required fields are defined

### Slow execution

- Each AI Function call is a round-trip to the model provider — minimize the number of calls
- Use async + `asyncio.gather` for independent calls
- Consider using smaller/faster models for simple tasks

---

## 16. Quick Reference

### Decorator Parameters

```python
@ai_function(
    model=...,                          # Model provider instance
    config=...,                         # AIFunctionConfig for shared settings
    post_conditions=[fn1, fn2],         # List of validation functions
    max_attempts=3,                     # Max retries on post-condition failure
    tools=[tool1, tool2],               # External tools the AI can use
    code_execution_mode="local",        # Enable Python code execution
    code_executor_additional_imports=[], # Allowed imports for code execution
    system_prompt="...",                 # Custom system prompt
    description="...",                  # Description when used as a tool
)
def my_function(arg: str) -> ReturnType:
    """Prompt template with {arg} placeholders."""
```

### Import Cheat Sheet

```python
# Core
from ai_functions import ai_function, AIFunctionConfig, Result

# Post-condition result type
from ai_functions.types import PostConditionResult

# Memory system
from ai_functions.memory import JSONMemoryBackend
from ai_functions.memory import Procedural, Frozen
from ai_functions.optimizer import TextGradOptimizer
from ai_functions.utils import show_graph

# Model providers (from strands-agents)
from strands.models.bedrock import BedrockModel
from strands.models.openai import OpenAIModel
```

### Post-Condition Patterns

```python
# Pattern 1: Assert (raise on failure)
def check_length(output: str):
    assert len(output.split()) <= 50, "Too long"

# Pattern 2: Return PostConditionResult
def check_format(output: str) -> PostConditionResult:
    if not output.startswith("##"):
        return PostConditionResult(passed=False, message="Must start with ##")
    return PostConditionResult(passed=True)

# Pattern 3: AI-powered validation
@ai_function
def check_quality(output: str) -> PostConditionResult:
    """Is this output high quality? {output}"""

# Pattern 4: Access original inputs
def validate(_answer, original_input: str):
    assert original_input in _answer, "Must reference the input"
```

### Providing Prompts

```python
# Method 1: Docstring template (simplest)
@ai_function
def my_func(text: str) -> str:
    """Translate {text} to French."""

# Method 2: Return a string from the function body (more control)
@ai_function
def my_func(text: str) -> str:
    assert text, "text cannot be empty"
    return f"Translate the following to French: {text}"

# Method 3: Return a t-string template (Python 3.14+, best for multi-line)
@ai_function
def my_func(text: str) -> str:
    return t"""
    Translate the following to French:
    {text}
    """
```

---

## Further Reading

- **Official Repository:** [github.com/strands-labs/ai-functions](https://github.com/strands-labs/ai-functions)
- **Official Tutorial:** [docs/tutorial.md](https://github.com/strands-labs/ai-functions/blob/main/docs/tutorial.md)
- **Examples:** [examples/](https://github.com/strands-labs/ai-functions/tree/main/examples)
- **Strands Agents SDK:** [strandsagents.com](https://strandsagents.com)
- **This Project (Log Analyzer):** See `documentation/design.md` and `documentation/architecture.md` for a real-world implementation using AI Functions
