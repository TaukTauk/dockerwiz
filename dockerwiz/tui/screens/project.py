"""Screen 1 — Project Setup."""

from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

_INVALID_NAME = re.compile(r"[^\w\-.]")


class ProjectScreen(Screen[None]):
    """Collects project name, output directory, and environment."""

    STEP = "Step 1 of 6"

    def compose(self) -> ComposeResult:
        partial = self.app.partial  # type: ignore[attr-defined]
        yield Container(
            Label("Project Setup", classes="screen-title"),
            Label("─" * 44, classes="divider"),

            Label("Project name", classes="field-label"),
            Input(
                value=partial.name or "",
                placeholder="my-api",
                id="project-name",
            ),
            Label("", id="name-error", classes="error-msg"),

            Label("Output directory", classes="field-label"),
            Input(
                value=partial.output_directory or ".",
                placeholder=".",
                id="output-dir",
            ),
            Label("Files will be written to: ./", id="resolved-path", classes="hint-msg"),

            Label("Environment", classes="field-label"),
            RadioSet(
                RadioButton("dev",  value=(partial.environment == "dev"),  id="env-dev"),
                RadioButton("prod", value=(partial.environment == "prod"), id="env-prod"),
                id="env-radio",
            ),

            Container(
                Button("Next >", variant="primary", id="btn-next", disabled=True),
                classes="button-row",
            ),
            classes="screen-content",
        )

    def on_mount(self) -> None:
        self.sub_title = self.STEP
        self._refresh_resolved()
        self._refresh_next_button()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in ("project-name", "output-dir"):
            self._refresh_resolved()
            self._refresh_next_button()

    def _refresh_resolved(self) -> None:
        name = self.query_one("#project-name", Input).value.strip()
        out  = self.query_one("#output-dir", Input).value.strip() or "."
        if name:
            resolved = f"Files will be written to: {out}/{name}"
        else:
            resolved = f"Files will be written to: {out}/"
        self.query_one("#resolved-path", Label).update(resolved)

    def _refresh_next_button(self) -> None:
        name = self.query_one("#project-name", Input).value.strip()
        self.query_one("#btn-next", Button).disabled = not name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self._advance()

    def _advance(self) -> None:
        name = self.query_one("#project-name", Input).value.strip()
        err  = self.query_one("#name-error", Label)

        if not name:
            err.update("Project name cannot be empty.")
            return
        if _INVALID_NAME.search(name):
            err.update("Project name contains invalid characters.")
            return
        err.update("")

        out_dir = self.query_one("#output-dir", Input).value.strip() or "."
        env_set = self.query_one("#env-radio", RadioSet)
        env     = "prod" if env_set.pressed_index == 1 else "dev"

        partial = self.app.partial  # type: ignore[attr-defined]
        self.app.partial = partial.model_copy(update={  # type: ignore[attr-defined]
            "name":             name,
            "output_directory": out_dir,
            "environment":      env,
        })

        from dockerwiz.tui.screens.language import LanguageScreen  # noqa: PLC0415
        self.app.push_screen(LanguageScreen())
