"""Interactive Terminal TUI Time-Travel Scrubber for PyRewind traces."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pyrewind.trace_model import Trace, TraceStep
from pyrewind.diagnostics.anomaly import AnomalyDetector
from pyrewind.diagnostics.explainer import RootCauseExplainer
from pyrewind.diagnostics.report import format_diagnostic_report


class TerminalScrubber:
    """Terminal-based interactive time-travel execution scrubber."""

    def __init__(self, trace: Trace, source_code: Optional[str] = None) -> None:
        self.trace = trace
        self.current_step_idx: int = 0
        self.source_code: Optional[str] = source_code
        self.source_lines: List[str] = []
        self._load_source()

        # Cache diagnostics
        self.detector = AnomalyDetector()
        self.anomalies = self.detector.detect_all(trace) if trace.steps else []
        self.explainer = RootCauseExplainer()
        self.report = self.explainer.explain(trace) if trace.steps else None

    def _load_source(self) -> None:
        """Load source code from file or string."""
        if self.source_code:
            self.source_lines = self.source_code.splitlines()
            return

        if self.trace.steps:
            filename = self.trace.steps[0].filename
            if filename and Path(filename).exists():
                try:
                    self.source_lines = Path(filename).read_text(encoding="utf-8").splitlines()
                except Exception:
                    self.source_lines = []

    def set_step(self, step_idx: int) -> None:
        """Set current step with bounds clamping."""
        if not self.trace.steps:
            self.current_step_idx = 0
            return
        self.current_step_idx = max(0, min(step_idx, len(self.trace.steps) - 1))

    def next_step(self) -> None:
        self.set_step(self.current_step_idx + 1)

    def prev_step(self) -> None:
        self.set_step(self.current_step_idx - 1)

    def jump_to_start(self) -> None:
        self.set_step(0)

    def jump_to_end(self) -> None:
        if self.trace.steps:
            self.set_step(len(self.trace.steps) - 1)

    def jump_to_exception(self) -> None:
        if self.trace.exception and self.trace.steps:
            self.jump_to_end()

    def render_step_frame(self, step_idx: Optional[int] = None, color: bool = True) -> str:
        """Render the complete text frame for the current step."""
        if step_idx is not None:
            self.set_step(step_idx)

        if not self.trace.steps:
            return "No recorded steps in trace."

        step = self.trace.steps[self.current_step_idx]
        total_steps = len(self.trace.steps)

        c_red = "\033[91m" if color else ""
        c_green = "\033[92m" if color else ""
        c_yellow = "\033[93m" if color else ""
        c_cyan = "\033[96m" if color else ""
        c_magenta = "\033[95m" if color else ""
        c_bold = "\033[1m" if color else ""
        c_dim = "\033[2m" if color else ""
        c_reset = "\033[0m" if color else ""

        out: List[str] = []

        # 1. Header Bar
        exc_badge = f" {c_red}[CRASH: {self.trace.exception.type_name}]{c_reset}" if self.trace.exception else f" {c_green}[OK]{c_reset}"
        out.append(f"{c_bold}{c_cyan}=== PyRewind Time-Travel Terminal Scrubber ==={c_reset}")
        out.append(f"Function: {c_bold}{self.trace.qualname}(){c_reset} in {self.trace.module}{exc_badge}")
        
        # 2. Scrubber Progress Bar
        bar_len = 30
        pos = int((self.current_step_idx / max(1, total_steps - 1)) * (bar_len - 1)) if total_steps > 1 else 0
        bar = "".join("#" if i == pos else "=" for i in range(bar_len))
        pct = int(((self.current_step_idx + 1) / total_steps) * 100)
        out.append(f"Progress: [{c_cyan}{bar}{c_reset}] Step {c_bold}{self.current_step_idx + 1}/{total_steps}{c_reset} ({pct}%) | Line {step.line_no}")
        out.append("-" * 65)

        # 3. Source Code Snippet
        out.append(f"{c_bold}{c_yellow}[ SOURCE CODE ]{c_reset} (Line {step.line_no}):")
        if self.source_lines and 1 <= step.line_no <= len(self.source_lines):
            start_ln = max(1, step.line_no - 2)
            end_ln = min(len(self.source_lines), step.line_no + 2)
            for ln in range(start_ln, end_ln + 1):
                code = self.source_lines[ln - 1]
                if ln == step.line_no:
                    out.append(f"  {c_bold}{c_green}>> {ln:3d} | {code}{c_reset}")
                else:
                    out.append(f"  {c_dim}   {ln:3d} | {code}{c_reset}")
        else:
            out.append(f"  {c_dim}   {step.line_no:3d} | [Source file unavailable]{c_reset}")

        out.append("-" * 65)

        # 4. Local Variables Table
        out.append(f"{c_bold}{c_cyan}[ LOCAL VARIABLES ]{c_reset} ({len(step.locals_snapshot)} in scope):")
        
        # Determine variable diff status relative to previous step
        prev_locals = self.trace.steps[self.current_step_idx - 1].locals_snapshot if self.current_step_idx > 0 else {}
        
        if step.locals_snapshot:
            out.append(f"  {'Variable':<18} {'Type':<10} {'State':<12} {'Value'}")
            out.append(f"  {'-'*16} {'-'*8} {'-'*10} {'-'*25}")
            for var_name, val in step.locals_snapshot.items():
                v_repr = repr(val)
                v_type = type(val).__name__

                if var_name not in prev_locals:
                    state_badge = f"{c_green}[NEW]{c_reset}"
                elif prev_locals[var_name] != val:
                    state_badge = f"{c_yellow}[MUTATED]{c_reset}"
                else:
                    state_badge = f"{c_dim}[SAME]{c_reset}"

                if len(v_repr) > 40:
                    v_repr = v_repr[:37] + "..."

                out.append(f"  {c_bold}{var_name:<18}{c_reset} {v_type:<10} {state_badge:<21} {v_repr}")
        else:
            out.append(f"  {c_dim}(No local variables in scope){c_reset}")

        # 5. Anomalies Alert on current step if any
        current_anomalies = [a for a in self.anomalies if a.step_id == step.step_id]
        if current_anomalies:
            out.append("-" * 65)
            for a in current_anomalies:
                out.append(f"  {c_bold}{c_red}[ANOMALY: {a.anomaly_type.value}]{c_reset} {a.message}")

        # 6. Controls Footer
        out.append("=" * 65)
        out.append(f"{c_dim}Controls:{c_reset} [←/h] Prev  [→/l] Next  [0] Start  [$] End  [e] Exception  [d] Diagnose  [q] Quit")
        return "\n".join(out)

    def interactive_loop(self) -> None:
        """Launch the interactive terminal event loop."""
        print("\033[?25l", end="") # Hide cursor
        try:
            while True:
                # Clear terminal and render current frame
                os.system("cls" if os.name == "nt" else "clear")
                frame = self.render_step_frame()
                print(frame)

                # Read single character without enter
                ch = self._get_key()
                if ch in ("q", "Q", "\x1b", "\x03"): # q, Esc, Ctrl+C
                    break
                elif ch in ("l", "L", "n", "N", "RIGHT", " "):
                    self.next_step()
                elif ch in ("h", "H", "p", "P", "LEFT"):
                    self.prev_step()
                elif ch in ("0", "HOME"):
                    self.jump_to_start()
                elif ch in ("$", "END"):
                    self.jump_to_end()
                elif ch in ("e", "E"):
                    self.jump_to_exception()
                elif ch in ("d", "D"):
                    os.system("cls" if os.name == "nt" else "clear")
                    if self.report:
                        print(format_diagnostic_report(self.trace, self.report, self.anomalies))
                    else:
                        print("No diagnostic report available.")
                    print("\nPress any key to return to scrubber...")
                    self._get_key()
        finally:
            print("\033[?25h", end="") # Restore cursor
            print("\nExited PyRewind TUI Scrubber.\n")

    def _get_key(self) -> str:
        """Cross-platform single keystroke reader."""
        if os.name == "nt":
            import msvcrt
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"): # Arrow key / Special
                ext = msvcrt.getch()
                if ext == b"K":
                    return "LEFT"
                elif ext == b"M":
                    return "RIGHT"
                elif ext == b"G":
                    return "HOME"
                elif ext == b"O":
                    return "END"
                return ""
            try:
                return ch.decode("utf-8", errors="ignore")
            except Exception:
                return ""
        else:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    # Escape sequence
                    seq = sys.stdin.read(2)
                    if seq == "[D":
                        return "LEFT"
                    elif seq == "[C":
                        return "RIGHT"
                    elif seq in ("[H", "[1~"):
                        return "HOME"
                    elif seq in ("[F", "[4~"):
                        return "END"
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def launch_tui(trace: Trace, source_code: Optional[str] = None) -> None:
    """Launch the interactive terminal scrubber TUI for a trace."""
    scrubber = TerminalScrubber(trace, source_code=source_code)
    scrubber.interactive_loop()