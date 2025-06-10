import os
import sys
import types
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a minimal stub for streamlit so utils can be imported without the
# actual package installed.
for mod in [
    "streamlit",
    "numpy",
    "faiss",
    "networkx",
    "sentence_transformers",
]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

if "numpy" in sys.modules:
    sys.modules["numpy"].ndarray = object

# Provide minimal attribute so importing utils doesn't fail when accessing
# SentenceTransformer.
if "sentence_transformers" in sys.modules:
    sys.modules["sentence_transformers"].SentenceTransformer = object

from utils import read_file_content, write_file_content, create_folder_if_not_exists, get_project_structure


def test_write_and_read_file(tmp_path):
    file_path = tmp_path / "test.txt"
    assert write_file_content(str(file_path), "hello world")
    assert file_path.exists()
    assert read_file_content(str(file_path)) == "hello world"


def test_create_folder_if_not_exists(tmp_path):
    folder_path = tmp_path / "newfolder"
    assert create_folder_if_not_exists(str(folder_path))
    assert folder_path.is_dir()


def test_get_project_structure(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file1.txt").write_text("a")
    (tmp_path / "subdir" / "file2.txt").write_text("b")

    structure = get_project_structure(str(tmp_path))
    assert structure["name"] == tmp_path.name
    names = sorted(child["name"] for child in structure["children"])
    assert names == ["file1.txt", "subdir"]
    subdir_node = next(c for c in structure["children"] if c["name"] == "subdir")
    assert any(child["name"] == "file2.txt" for child in subdir_node["children"])
