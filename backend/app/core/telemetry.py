from langfuse.langchain import CallbackHandler  # v4.x: moved from langfuse.callback to langfuse.langchain
from app.config import settings
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

def get_langfuse_handler():
    """
    Initializes and returns the Langfuse CallbackHandler using credentials from config.
    
    To attach this to an agent's .invoke() call, pass it via the config parameter:
    agent.invoke(
        {"messages": [...]}, 
        config={"callbacks": [get_langfuse_handler()]}
    )
    """
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        print("\n[Telemetry] Warning: LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set. Skipping Langfuse initialization to prevent terminal spam.")
        return None
    
    # The Langfuse CallbackHandler automatically picks up the LANGFUSE_PUBLIC_KEY, 
    # LANGFUSE_SECRET_KEY, and LANGFUSE_HOST directly from your environment variables!
    langfuse_handler = CallbackHandler()
    return langfuse_handler

import os
import atexit

def setup_opentelemetry():
    """
    Sets up a basic OpenTelemetry TracerProvider that exports spans directly 
    to a local log file ('otel_traces.log') to keep terminal clean.
    """
    provider = TracerProvider()
    
    # Dump spans to a dedicated file instead of polluting terminal output
    log_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "otel_traces.log"))
    file_stream = open(log_file_path, "a", encoding="utf-8")
    processor = BatchSpanProcessor(ConsoleSpanExporter(out=file_stream))
    provider.add_span_processor(processor)
    
    # Flush and close cleanly on exit
    atexit.register(provider.shutdown)
    
    # Register this provider globally
    trace.set_tracer_provider(provider)
    
    # Return a tracer instance
    return trace.get_tracer(__name__)

# Initialize OTel globally for the app and expose the tracer
tracer = setup_opentelemetry()
