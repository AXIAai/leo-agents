"""
UX Review Agent — analysiert Frontend-Code aus Nutzerperspektive.
"""
import os
from pathlib import Path
from typing import Optional
import anthropic

SYSTEM_PROMPT = """Du bist ein erfahrener UX Engineer und Product Designer, spezialisiert auf
Web-Applikationen (React, Vue, HTML/CSS). Du analysierst Frontend-Code aus der Perspektive
des Endnutzers, nicht des Entwicklers.

Analysiere nach diesen Kriterien:

1. **Usability** — Ist die Interaktion intuitiv? Gibt es verwirrende Flows?
2. **Feedback & Fehlerbehandlung** — Bekommt der User klares Feedback? (Loading-States, Fehlermeldungen)
3. **Accessibility (a11y)** — ARIA-Labels, Keyboard-Navigation, Kontrast
4. **Mobile & Responsiveness** — Funktioniert es auf kleinen Screens?
5. **Performance-Wahrnehmung** — Ladezeiten, Skeleton Screens, Optimistic Updates
6. **Konsistenz** — Einheitliche Sprache, Icons, Abstände, Farben

Für jeden Punkt:
- Konkretes Problem benennen (mit Komponente/Zeile)
- Konkreten Fix vorschlagen (Code-Snippet wenn hilfreich)
- Priorisierung: 🔴 Kritisch | 🟡 Wichtig | 🟢 Nice-to-have

Schreibe auf Deutsch. Sei direkt und nutzerorientiert — denke wie ein frustrierter User."""

FRONTEND_EXTENSIONS = {".jsx", ".tsx", ".vue", ".html", ".css", ".scss", ".svelte"}


def _read_frontend_files(paths: list[Path]) -> list[dict]:
    files = []
    for p in paths:
        if p.is_dir():
            for ext in FRONTEND_EXTENSIONS:
                for f in p.rglob(f"*{ext}"):
                    if any(part.startswith(".") or part in ("node_modules", "dist", "build")
                           for part in f.parts):
                        continue
                    try:
                        files.append({"name": str(f), "content": f.read_text(encoding="utf-8")})
                    except Exception:
                        pass
        elif p.is_file() and p.suffix in FRONTEND_EXTENSIONS:
            try:
                files.append({"name": str(p), "content": p.read_text(encoding="utf-8")})
            except Exception:
                pass
    return files


def review_ux(
    paths: list[str],
    context: Optional[str] = None,
    model: str = "claude-opus-4-7",
) -> str:
    """UX-Review für Frontend-Dateien oder Verzeichnisse."""
    file_paths = [Path(p) for p in paths]
    files = _read_frontend_files(file_paths)

    if not files:
        return "Keine Frontend-Dateien (.jsx, .tsx, .vue, .html, .css) gefunden."

    code_blocks = []
    total_chars = 0
    for f in files:
        if total_chars + len(f["content"]) > 120_000:
            code_blocks.append(f"[{f['name']} — zu groß, übersprungen]")
            continue
        code_blocks.append(f"### {f['name']}\n```\n{f['content']}\n```")
        total_chars += len(f["content"])

    user_message = "Führe einen UX-Review dieser Frontend-Dateien durch:\n\n" + "\n\n".join(code_blocks)
    if context:
        user_message += f"\n\n**Kontext zur App:** {context}"

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        result = stream.get_final_text()

    return result
