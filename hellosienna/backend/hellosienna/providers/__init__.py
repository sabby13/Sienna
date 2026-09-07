"""Model providers behind two independent abstractions (LLMProvider, EmbeddingProvider).

Ollama implements both initially, but nothing may assume one object provides both.
M0 exercises only LLMProvider.generate + a reachability/model-status probe.
"""
