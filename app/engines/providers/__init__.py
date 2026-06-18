"""External API provider implementations for unified-web-skill."""
from .jina_reader import JinaReaderEngine
from .firecrawl import FirecrawlEngine

__all__ = ["JinaReaderEngine", "FirecrawlEngine"]
