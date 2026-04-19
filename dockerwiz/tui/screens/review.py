"""Screen 5 — Review Summary."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Label


def _files_to_generate(partial: object) -> list[str]:
    files = ["Dockerfile", "docker-compose.yml", ".dockerignore", ".env.example", "Makefile"]
    if getattr(partial, "environment", "dev") == "dev":
        files.insert(2, "docker-compose.override.yml")
    if "nginx" in getattr(partial, "services", []):
        files.append("nginx.conf")
    return files


class ReviewScreen(Screen[None]):
    """Read-only summary of all wizard choices before generation."""

    STEP = "Step 5 of 6"

    def compose(self) -> ComposeResult:
        partial  = self.app.partial  # type: ignore[attr-defined]
        services = ", ".join(partial.services) if partial.services else "(none)"
        out_path = f"{partial.output_directory}/{partial.name}"
        files    = _files_to_generate(partial)

        yield Container(
            Label("Review", classes="screen-title"),
            Label("─" * 44, classes="divider"),

            Label(f"Project       {partial.name}"),
            Label(f"Output        {out_path}"),
            Label(f"Environment   {partial.environment}"),
            Label(f"Language      {partial.language} / {partial.framework}"),
            Label(f"Base image    {partial.base_image}"),
            Label(f"Services      {services}"),
            Label(f"App port      {partial.app_port}"),
            *(
                [
                    Label(f"DB user       {partial.db_user}"),
                    Label(f"DB name       {partial.db_name}"),
                ]
                if partial.db_user else []
            ),

            Label(""),
            Label("Files to be generated", classes="field-label"),
            Label("─" * 22, classes="divider"),
            *[Label(f"  {f}") for f in files],

            Label("", id="conflict-label", classes="warn-msg"),

            Container(
                Button("< Back", id="btn-back"),
                Button("Generate", variant="success", id="btn-generate"),
                classes="button-row",
            ),
            classes="screen-content",
        )

    def on_mount(self) -> None:
        self.sub_title = self.STEP
        self._check_output_conflict()

    def _check_output_conflict(self) -> None:
        partial  = self.app.partial  # type: ignore[attr-defined]
        out_path = Path(partial.output_directory) / (partial.name or "")
        if out_path.exists() and any(out_path.iterdir()):
            self.query_one("#conflict-label", Label).update(
                f"! {out_path} already exists and is not empty."
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-generate":
            self._generate()

    def _generate(self) -> None:
        from pydantic import ValidationError  # noqa: PLC0415

        partial = self.app.partial  # type: ignore[attr-defined]
        try:
            config = partial.to_config()
        except ValidationError as exc:
            self.query_one("#conflict-label", Label).update(
                f"Validation error: {exc.errors()[0]['msg']}"
            )
            return

        from dockerwiz.tui.screens.generate import GenerateScreen  # noqa: PLC0415
        self.app.push_screen(GenerateScreen(config=config))
