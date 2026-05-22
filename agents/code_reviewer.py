"""
Code Review Agent — analysiert Dateien mit Claude und gibt strukturiertes Feedback.
"""
import os
from pathlib import Path
from typing import Optional
import anthropic

SYSTEM_PROMPT = """Du bist ein erfahrener Senior Software Engineer mit 15+ Jahren Erfahrung
in Python, JavaScript/TypeScript, React und FastAPI. Du führst professionelle Code-Reviews durch.

Analysiere den vorgelegten Code nach diesen Kriterien:

1. **Bugs & Korrektheit** — logische Fehler, Edge Cases, falsche Annahmen
2. **Sicherheit** — SQL-Injection, XSS, unsichere Abhängigkeiten, offengelegte Secrets
3. **Performance** — unnötige Queries, fehlende Indizes, teure Operationen in Loops
4. **Wartbarkeit** — Komplexität, Lesbarkeit, fehlende/übermäßige Kommentare
5. **Best Practices** — SOLID-Prinzipien, DRY, Fehlerbehandlung

Ausgabeformat (Markdown):
- Beginne mit einer 1-Satz-Zusammenfassung (Gesamturteil)
- Kritische Probleme zuerst, dann Verbesserungen, dann Lob
- Für jeden Fund: Zeilennummer + konkreter Fix-Vorschlag
- Schreibe auf Deutsch

Sei direkt und konkret. Keine leeren Phrasen. Wenn der Code gut ist, sag es kurz."""

EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".go", ".java", ".cs"}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _read_files(paths: list[Path]) -> list[dict]:
    files = []
    for p in paths:
        if p.is_dir():
            for ext in EXTENSIONS:
                for f in p.rglob(f"*{ext}"):
                    if any(part.startswith(".") or part in ("node_modules", "__pycache__", "dist", "build")
                           for part in f.parts):
                        continue
                    try:
                        files.append({"name": str(f), "content": f.read_text(encoding="utf-8")})
                    except Exception:
                        pass
        elif p.is_file() and p.suffix in EXTENSIONS:
            try:
                files.append({"name": str(p), "content": p.read_text(encoding="utf-8")})
            except Exception:
                pass
    return files


def review(
    paths: list[str],
    focus: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
) -> str:
    """
    Hauptfunktion: Review für die gegebenen Pfade (Dateien oder Verzeichnisse).
    Gibt den Review-Text zurück.
    """
    file_paths = [Path(p) for p in paths]
    files = _read_files(file_paths)

    if not files:
        return "Keine unterstützten Dateien gefunden."

    code_blocks = []
    total_chars = 0
    for f in files:
        if total_chars + len(f["content"]) > 150_000:
            code_blocks.append(f"[{f['name']} — zu groß, übersprungen]")
            continue
        code_blocks.append(f"### {f['name']}\n```\n{f['content']}\n```")
        total_chars += len(f["content"])

    user_message = "Bitte führe einen vollständigen Code-Review durch:\n\n" + "\n\n".join(code_blocks)
    if focus:
        user_message += f"\n\n**Besonderer Fokus:** {focus}"

    with _get_client().messages.stream(
        model=model,
        max_tokens=4096,
        # System-Prompt wird gecacht — bei Folgeaufrufen nur 10% der Token-Kosten
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        return stream.get_final_text()
