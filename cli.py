#!/usr/bin/env python3
"""
AXIA Agents CLI
Verwendung:
  python cli.py review src/                        # Code-Review eines Verzeichnisses
  python cli.py review app.py main.py              # Code-Review einzelner Dateien
  python cli.py review src/ --focus "Sicherheit"   # Mit Fokus-Thema
  python cli.py ux src/pages/                      # UX-Review
  python cli.py ux src/ --context "B2B SaaS App"  # Mit App-Kontext
"""
import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Fehler: ANTHROPIC_API_KEY nicht gesetzt. Bitte .env Datei anlegen.")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from agents.code_reviewer import review
from agents.ux_reviewer import review_ux


def main():
    parser = argparse.ArgumentParser(description="AXIA Code & UX Review Agents")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- code review ---
    r = sub.add_parser("review", help="Professioneller Code-Review")
    r.add_argument("paths", nargs="+", help="Dateien oder Verzeichnisse")
    r.add_argument("--focus", "-f", help="Fokus-Thema, z.B. 'Sicherheit' oder 'Performance'")
    r.add_argument("--output", "-o", help="Ausgabe in Datei schreiben (optional)")
    r.add_argument("--model", default="claude-sonnet-4-6")

    # --- ux review ---
    u = sub.add_parser("ux", help="UX-Review für Frontend-Code")
    u.add_argument("paths", nargs="+", help="Dateien oder Verzeichnisse")
    u.add_argument("--context", "-c", help="Beschreibung der App für besseren Kontext")
    u.add_argument("--output", "-o", help="Ausgabe in Datei schreiben (optional)")
    u.add_argument("--model", default="claude-sonnet-4-6")

    args = parser.parse_args()

    print(f"Analysiere {args.paths}...\n")

    if args.command == "review":
        result = review(args.paths, focus=getattr(args, "focus", None), model=args.model)
    else:
        result = review_ux(args.paths, context=getattr(args, "context", None), model=args.model)

    print(result)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"\n→ Gespeichert in {args.output}")


if __name__ == "__main__":
    main()
