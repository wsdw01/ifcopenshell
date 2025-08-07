from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .logo import LOGO
from .config import MiaConfig, load_config, save_config

app = typer.Typer(help="Mia — Model Intelligence Assistant CLI")
console = Console()


@app.callback()
def main_callback() -> None:
    """Print logo at startup."""
    console.print(LOGO)


@app.command()
def version() -> None:
    """Show Mia version."""
    console.print(f"Mia version: [bold]{__version__}[/bold]")


config_app = typer.Typer(help="Manage Mia configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    cfg = load_config()
    table = Table(title="Mia Config")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("llm_provider", cfg.llm_provider)
    table.add_row("api_keys.gemini", (cfg.api_keys.gemini or ""))
    table.add_row("api_keys.openai", (cfg.api_keys.openai or ""))
    table.add_row("api_keys.anthropic", (cfg.api_keys.anthropic or ""))
    table.add_row("api_keys.openrouter", (cfg.api_keys.openrouter or ""))
    table.add_row("api_keys.ollama", (cfg.api_keys.ollama or ""))
    console.print(table)


@config_app.command("set")
def config_set(key: str = typer.Argument(..., help="e.g. llm.provider=gemini or api_keys.gemini=KEY")) -> None:
    """Set a configuration value.

    Examples:
      mia config set llm.provider=gemini
      mia config set api_keys.gemini=YOUR_KEY
    """
    if "=" not in key:
        raise typer.BadParameter("Expected KEY=VALUE format")
    k, v = key.split("=", 1)
    cfg = load_config()
    if k in ("llm.provider", "llm_provider"):
        cfg.llm_provider = v.strip()
    elif k.startswith("api_keys."):
        sub = k.split(".", 1)[1]
        if sub == "gemini":
            cfg.api_keys.gemini = v.strip()
        elif sub == "openai":
            cfg.api_keys.openai = v.strip()
        elif sub == "anthropic":
            cfg.api_keys.anthropic = v.strip()
        elif sub == "openrouter":
            cfg.api_keys.openrouter = v.strip()
        elif sub == "ollama":
            cfg.api_keys.ollama = v.strip()
        else:
            raise typer.BadParameter(f"Unknown api key '{sub}'")
    else:
        raise typer.BadParameter(f"Unknown key '{k}'")
    save_config(cfg)
    console.print("[green]Saved.[/green]")


ifc_app = typer.Typer(help="IFC utilities (ifcopenshell)")
app.add_typer(ifc_app, name="ifc")


@ifc_app.command("info")
def ifc_info(path: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to IFC file")) -> None:
    """Print basic information and entity counts from an IFC file.

    Requires 'ifcopenshell' to be installed.
    """
    try:
        import ifcopenshell  # type: ignore
    except Exception:
        console.print("[red]ifcopenshell not found.[/red] Install with: \n  pip install ifcopenshell\n")
        raise typer.Exit(code=2)

    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:  # pragma: no cover
        console.print(f"[red]Failed to open IFC file:[/red] {exc}")
        raise typer.Exit(code=2)

    schema = getattr(model, "schema", None) or getattr(model, "schema_name", lambda: "?")()
    header = getattr(model, "header", None)

    # Count common classes
    classes = [
        "IfcProject",
        "IfcSite",
        "IfcBuilding",
        "IfcBuildingStorey",
        "IfcSpace",
        "IfcWall",
        "IfcSlab",
        "IfcBeam",
        "IfcColumn",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcDuctSegment",
    ]
    counts = {}
    for cls in classes:
        try:
            counts[cls] = len(model.by_type(cls))
        except Exception:
            counts[cls] = 0

    table = Table(title=f"IFC Info — {path.name}")
    table.add_column("Property")
    table.add_column("Value")
    table.add_row("Schema", str(schema))
    if header is not None:
        try:
            file_desc = getattr(header, "file_description", None)
            file_name = getattr(header, "file_name", None)
            table.add_row("Description", str(file_desc))
            table.add_row("FileName", str(file_name))
        except Exception:
            pass

    console.print(table)

    ct = Table(title="Entity counts (selected)")
    ct.add_column("Entity")
    ct.add_column("Count", justify="right")
    for k, v in counts.items():
        ct.add_row(k, str(v))
    console.print(ct)