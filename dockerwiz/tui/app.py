"""Textual Application — manages screen transitions and partial wizard state."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from dockerwiz.config import UserConfig
from dockerwiz.models import PartialProjectConfig
from dockerwiz.tui.screens.project import ProjectScreen


class DockerWizApp(App[None]):
    """The dockerwiz TUI wizard application."""

    TITLE = "dockerwiz"
    CSS = """
    Screen {
        align: center top;
    }

    .screen-content {
        width: 1fr;
        max-width: 80;
        height: 1fr;
        padding: 1 2;
    }

    .screen-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .divider {
        color: $panel;
        margin-bottom: 1;
    }

    .field-label {
        margin-top: 1;
    }

    .error-msg {
        color: $error;
    }

    .warn-msg {
        color: $warning;
    }

    .hint-msg {
        color: $text-muted;
    }

    .button-row {
        margin-top: 2;
        layout: horizontal;
        align-horizontal: right;
        height: auto;
    }

    .button-row-split {
        margin-top: 2;
        layout: horizontal;
        height: auto;
    }

    Button {
        margin-left: 1;
    }

    .lang_box {
        height: 10;
    }

    .config_box {
        height: 15;
    }

    .service-row {
        height: 5;
    }
    """

    def __init__(
        self,
        user_config: UserConfig,
        available_versions: dict[str, list[str]],
        is_live: bool = True,
    ) -> None:
        super().__init__()
        self.user_config        = user_config
        self.available_versions = available_versions
        self.is_live            = is_live
        self.partial            = PartialProjectConfig(
            language    = user_config.defaults.language,
            framework   = user_config.defaults.framework,
            environment = user_config.defaults.environment or "dev",
        )

    def on_mount(self) -> None:
        self.push_screen(ProjectScreen())

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
