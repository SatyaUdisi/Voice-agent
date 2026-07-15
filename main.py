"""Voice Agent entrypoint.

Usage:
    python main.py            # launch the desktop GUI (default)
    python main.py --server   # run the FastAPI backend only
    python main.py --cli      # simple text REPL (no GUI, great for testing)
"""

from __future__ import annotations

import argparse
import sys


def _run_cli() -> int:
    """A minimal text REPL against the agent core (no GUI required)."""
    from assistant import build_assistant

    assistant = build_assistant()
    assistant.set_confirm_fn(lambda prompt: input(f"{prompt} [y/N] ").strip().lower() == "y")
    print(f"Voice Agent CLI  |  online={assistant.llm.online}  tools={len(assistant.registry.all())}")
    print("Type 'exit' to quit.\n")
    try:
        while True:
            text = input("you > ").strip()
            if text.lower() in {"exit", "quit"}:
                break
            if not text:
                continue
            reply = assistant.handle_text(text)
            print(f"jarvis > {reply}\n")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        assistant.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Voice Agent")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--server", action="store_true", help="Run the FastAPI backend only.")
    group.add_argument("--cli", action="store_true", help="Run a text REPL (no GUI).")
    args = parser.parse_args(argv)

    if args.server:
        from server import run_server

        run_server()
        return 0
    if args.cli:
        return _run_cli()

    # Default: desktop GUI.
    try:
        from gui import run_gui
    except Exception as exc:  # noqa: BLE001 - GUI deps / display may be missing
        print(f"Could not start GUI ({exc}). Falling back to CLI. Use --server for headless.")
        return _run_cli()
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
