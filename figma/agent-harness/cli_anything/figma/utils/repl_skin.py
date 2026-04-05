"""REPL UI: banner, prompt, input loop styling."""
from __future__ import annotations

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False

FIGMA_PURPLE = "\033[38;5;99m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


class ReplSkin:
    def __init__(self, name: str = "figma", version: str = "1.0.0") -> None:
        self.name = name
        self.version = version
        self._context: str | None = None
        if _HAS_PROMPT_TOOLKIT:
            self._ps = PromptSession(history=InMemoryHistory())
        else:
            self._ps = None

    def set_context(self, context: str | None) -> None:
        self._context = context

    def print_banner(self) -> None:
        print(f"{FIGMA_PURPLE}{BOLD}")
        print("  ███████╗██╗ ██████╗ ███╗   ███╗ █████╗ ")
        print("  ██╔════╝██║██╔════╝ ████╗ ████║██╔══██╗")
        print("  █████╗  ██║██║  ███╗██╔████╔██║███████║")
        print("  ██╔══╝  ██║██║   ██║██║╚██╔╝██║██╔══██║")
        print("  ██║     ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║")
        print("  ╚═╝     ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝")
        print(f"{RESET}{DIM}  CLI-Anything for Figma  v{self.version}{RESET}")
        print()
        print(f"{DIM}  Commands: config · file · export · component · style · comment · project · user · session{RESET}")
        print(f"{DIM}  Type 'exit' or Ctrl-D to quit.{RESET}")
        print()

    def _prompt_str(self) -> str:
        ctx = f" [{self._context}]" if self._context else ""
        return f"{FIGMA_PURPLE}figma{ctx}>{RESET} "

    def get_input(self) -> str:
        if self._ps is not None:
            from prompt_toolkit.formatted_text import ANSI
            try:
                return self._ps.prompt(ANSI(self._prompt_str()))
            except KeyboardInterrupt:
                return ""
        try:
            return input(self._prompt_str())
        except EOFError:
            raise

    def print_error(self, msg: str) -> None:
        print(f"\033[31mError:\033[0m {msg}")

    def print_success(self, msg: str) -> None:
        print(f"\033[32m✓\033[0m {msg}")

    def print_info(self, msg: str) -> None:
        print(f"{DIM}{msg}{RESET}")
