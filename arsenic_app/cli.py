from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .banner import ARSENIC_BANNER
from .generator import create_document, list_templates
from .tester import probe_rag

console = Console()


def _banner() -> None:
    console.print(f"[bold green]{ARSENIC_BANNER}[/bold green]")


class BannerGroup(click.Group):
    def get_help(self, ctx: click.Context) -> str:
        _banner()
        return super().get_help(ctx)


@click.group(cls=BannerGroup)
def main() -> None:
    """MAD RAG poison kit."""


@main.command("templates")
def templates_cmd() -> None:
    for item in list_templates():
        console.print(item)


@main.command("new")
@click.option("--type", "doc_type", required=True, type=click.Choice(["md", "html", "pdf"]))
@click.option("--strategy", default="comment", show_default=True)
def new_cmd(doc_type: str, strategy: str) -> None:
    """Сгенерировать документ-приманку с канарейкой в скрытом векторе."""
    path, c = create_document(doc_type, strategy)
    console.print(f"[green]Created[/green] {path}  (канарейка {c})")


@main.command("probe")
@click.argument("index_url")
@click.argument("query_url")
@click.option("--json", "as_json", type=click.Path(), default=None,
              help="сохранить JSON-находки (контракт пайплайна)")
def probe_cmd(index_url: str, query_url: str, as_json: str | None) -> None:
    """Проверить RAG: выполнит ли он инструкцию из отравленного документа."""
    d = probe_rag(index_url, query_url)
    if as_json:
        Path(as_json).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    if d["verdict"] == "НЕ ПРОВЕРЕНО":
        console.print(f"[yellow]НЕ ПРОВЕРЕНО[/yellow]: {d['not_proven']}")
        raise SystemExit(2)
    t = Table(title=f"arsenic: {index_url}  ·  векторов: {d['векторов']}")
    t.add_column("вектор"); t.add_column("вердикт"); t.add_column("почему")
    for f in d["findings"]:
        цвет = {"ПРОВАЛ": "red", "НЕ ПРОВЕРЕНО": "yellow"}.get(f["вердикт"], "green")
        t.add_row(f["вектор"], f"[{цвет}]{f['вердикт']}[/{цвет}]", f["почему"])
    console.print(t)
    цвет = "red" if d["verdict"] == "ПРОВАЛ" else "green"
    console.print(f"Вердикт: [{цвет}]{d['verdict']}[/{цвет}] — {d['почему']}")
    raise SystemExit(1 if d["verdict"] == "ПРОВАЛ" else 0)


@main.command("preview")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def preview_cmd(file: Path) -> None:
    console.print(file.read_text(encoding="utf-8", errors="replace")[:4000])


if __name__ == "__main__":
    main()
