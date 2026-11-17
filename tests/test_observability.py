import os
from unittest.mock import patch, MagicMock
import pytest
from veritas.core.observability import get_observability_callbacks

def test_observability_callbacks_empty_by_default(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    
    callbacks = get_observability_callbacks()
    assert callbacks == []

def test_observability_callbacks_langfuse_active(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-mock123")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-mock456")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    with patch("langfuse.langchain.CallbackHandler") as MockHandler:
        mock_instance = MagicMock()
        MockHandler.return_value = mock_instance
        
        callbacks = get_observability_callbacks()
        assert len(callbacks) == 1
        assert callbacks[0] == mock_instance
        MockHandler.assert_called_once_with(
            public_key="pk-lf-mock123",
            secret_key="sk-lf-mock456",
            host="https://cloud.langfuse.com"
        )

def test_observability_langsmith_logging(monkeypatch, caplog):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_pt_mock987")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")
    
    with caplog.at_level("INFO"):
        callbacks = get_observability_callbacks()
        assert "LangSmith Tracing active for project: 'test-project'" in caplog.text
