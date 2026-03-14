from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass

APP_VERSION = "0.3.0"
APP_VERSION_TAG = f"v{APP_VERSION}"

ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def ansi_fg(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"\x1b[38;2;{red};{green};{blue}m"


def ansi_bg(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"\x1b[48;2;{red};{green};{blue}m"


@dataclass(frozen=True)
class PulseColors:
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    accent: tuple[int, int, int]
    text_light: tuple[int, int, int]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = value.lstrip("#")
    return (
        int(normalized[0:2], 16),
        int(normalized[2:4], 16),
        int(normalized[4:6], 16),
    )


def get_pulse_colors() -> PulseColors:
    # Prefer the Pulse palette already present in the repo brief, but keep the CLI
    # palette local/static instead of parsing YAML at runtime.
    return PulseColors(
        primary=_hex_to_rgb("#13324A"),
        secondary=_hex_to_rgb("#214B67"),
        accent=_hex_to_rgb("#F4C542"),
        text_light=_hex_to_rgb("#F7F4ED"),
    )


ASCII_PULSE = [
    " ____  _   _ _     ____  _____   PULSE",
    "|  _ \\| | | | |   / ___|| ____|",
    "| |_) | | | | |   \\___ \\|  _|",
    "|  __/| |_| | |___ ___) | |___",
    "|_|    \\___/|_____|____/|_____|",
]


def render_pulse_header(
    *,
    version_tag: str = APP_VERSION_TAG,
    no_color: bool = False,
    term_width: int | None = None,
) -> str:
    colors = get_pulse_colors()
    width = term_width or shutil.get_terminal_size(fallback=(80, 20)).columns
    left = "Creative Supply Engine · PULSE Beverages"
    right = version_tag
    content_width = max(
        max(len(line) for line in ASCII_PULSE),
        len(left) + 1 + len(right),
    )
    subtitle_plain = (
        left + (" " * max(content_width - len(left) - len(right), 1)) + right
    )

    if no_color:
        lines = [*ASCII_PULSE, subtitle_plain]
    else:
        subtitle = (
            f"{ansi_fg(colors.text_light)}{left}{ANSI_RESET}"
            f"{' ' * max(content_width - len(left) - len(right), 1)}"
            f"{ANSI_BOLD}{ansi_fg(colors.accent)}{right}{ANSI_RESET}"
        )
        lines = [
            f"{ANSI_BOLD}{ansi_fg(colors.accent)}{line}{ANSI_RESET}"
            for line in ASCII_PULSE
        ]
        lines.append(subtitle)

    if width >= 60:
        visible_width = max(len(strip_ansi(line)) for line in lines)
        pad = max((width - visible_width) // 2, 0)
        lines = [(" " * pad) + line for line in lines]

    return "\n".join(lines)


def print_pulse_header(
    *,
    version_tag: str = APP_VERSION_TAG,
    no_color: bool = False,
    stream=None,
) -> None:
    stream = stream or sys.stdout
    print(
        render_pulse_header(
            version_tag=version_tag,
            no_color=no_color or not getattr(stream, "isatty", lambda: False)(),
        ),
        file=stream,
    )


def render_divider(*, no_color: bool = False, term_width: int | None = None) -> str:
    colors = get_pulse_colors()
    width = term_width or shutil.get_terminal_size(fallback=(80, 20)).columns
    line = "─" * max(min(width, 72), 24)
    if no_color:
        return line
    return f"{ansi_fg(colors.secondary)}{line}{ANSI_RESET}"


def render_section(title: str, *, no_color: bool = False) -> str:
    colors = get_pulse_colors()
    label = f"[ {title} ]"
    if no_color:
        return label
    return f"{ANSI_BOLD}{ansi_fg(colors.accent)}{label}{ANSI_RESET}"


def render_success(message: str, *, no_color: bool = False) -> str:
    colors = get_pulse_colors()
    label = f"OK  {message}"
    if no_color:
        return label
    return f"{ANSI_BOLD}{ansi_fg(colors.text_light)}{label}{ANSI_RESET}"


def render_warning(message: str, *, no_color: bool = False) -> str:
    colors = get_pulse_colors()
    label = f"WARN  {message}"
    if no_color:
        return label
    return (
        f"{ANSI_BOLD}{ansi_fg(colors.primary)}{ansi_bg(colors.accent)} {label} "
        f"{ANSI_RESET}"
    )


def render_error(message: str, *, no_color: bool = False) -> str:
    colors = get_pulse_colors()
    label = f"ERR  {message}"
    if no_color:
        return label
    return (
        f"{ANSI_BOLD}{ansi_fg(colors.text_light)}{ansi_bg(colors.primary)} {label} "
        f"{ANSI_RESET}"
    )
