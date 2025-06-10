import os
import sys
import types
import pytest
from fastapi import HTTPException

# Stub external dependencies so backend_api can be imported without them
for mod in [
    "google",
    "google.generativeai",
    "anthropic",
    "openai",
    "streamlit",
    "numpy",
    "faiss",
    "networkx",
    "sentence_transformers",
]:
    sys.modules.setdefault(mod, types.ModuleType(mod.split(".")[-1]))

if "numpy" in sys.modules:
    sys.modules["numpy"].ndarray = object
if "sentence_transformers" in sys.modules:
    sys.modules["sentence_transformers"].SentenceTransformer = object

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend_api import run_git_command


def test_run_git_command_without_project():
    with pytest.raises(HTTPException):
        run_git_command(["git", "status"], None)

