# Mia — Model Intelligence Assistant (CLI)

Mia is a Python-first CLI for BIM/CAD/IFC automation and LLM-assisted workflows.

## Install (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Quickstart

```bash
mia --help
mia config show
mia config set llm.provider=gemini
mia ifc info --path /path/to/model.ifc
```

## Notes
- `ifc info` uses `ifcopenshell`. If not installed, Mia will show an install hint.
- Config is stored in `~/.mia/config.toml`.
- More tools and providers coming next (Gemini/OpenAI/Ollama).