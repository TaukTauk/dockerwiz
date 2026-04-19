"""Screen 6 — Generating."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Label, ProgressBar

from dockerwiz.models import ProjectConfig


class GenerateScreen(Screen[None]):
    """Writes files to disk and shows per-file progress."""

    STEP = "Step 6 of 6"

    def __init__(self, config: ProjectConfig) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:

        self._files = self._compute_files()
        total    = len(self._files)
        out_path = f"{self._config.output_directory}/{self._config.name}"

        file_rows = [
            Container(
                Label(fname, id=f"file-{i}"),
                Label("pending", id=f"status-{i}", classes="hint-msg"),
                classes="file-row",
            )
            for i, fname in enumerate(self._files)
        ]

        yield Container(
            Label("Generating", classes="screen-title"),
            Label("─" * 44, classes="divider"),
            Label(f"Writing files to {out_path}", classes="hint-msg"),
            Label(""),
            *file_rows,
            Label(""),
            ProgressBar(total=total, show_eta=False, id="progress"),
            Label("", id="status-msg"),
            Label("", id="next-steps"),
            Container(id="action-row", classes="button-row"),
            classes="screen-content",
        )

    def _compute_files(self) -> list[str]:
        files = ["Dockerfile", "docker-compose.yml", ".dockerignore", ".env.example", "Makefile"]
        if self._config.is_dev:
            files.insert(2, "docker-compose.override.yml")
        if self._config.has_nginx:
            files.append("nginx.conf")
        return files

    def on_mount(self) -> None:
        self.sub_title = self.STEP
        self.run_worker(self._generate_files, exclusive=True)

    async def _generate_files(self) -> None:
        from dockerwiz.generator import (  # noqa: PLC0415
            build_context,
            build_jinja_env,
            render_templates,
        )

        try:
            env     = build_jinja_env(self._config.language, self._config.framework)
            context = build_context(self._config)
            rendered = render_templates(env, context, self._config)
            output_dir = Path(self._config.output_directory) / self._config.name
            output_dir.mkdir(parents=True, exist_ok=True)

            import shutil
            import tempfile  # noqa: E401, PLC0415
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                for i, fname in enumerate(self._files):
                    self._set_status(i, "writing...")
                    content = rendered.get(fname, "")
                    (tmp_dir / fname).write_text(content, encoding="utf-8")
                    shutil.copy2(tmp_dir / fname, output_dir / fname)
                    self._set_status(i, "done")
                    self.query_one("#progress", ProgressBar).advance(1)

            self._on_success()
        except Exception as exc:  # noqa: BLE001
            self._on_failure(str(exc))

    def _set_status(self, index: int, text: str) -> None:
        self.query_one(f"#status-{index}", Label).update(text)

    def _on_success(self) -> None:
        name = self._config.name
        out  = self._config.output_directory
        self.query_one("#status-msg", Label).update(
            f"Generated {len(self._files)} files in {out}/{name}"
        )
        self.query_one("#next-steps", Label).update(
            f"\nNext steps:\n  cd {name}\n  cp .env.example .env\n  make up"
        )
        row = self.query_one("#action-row", Container)
        row.mount(Button("Exit", variant="primary", id="btn-exit"))

    def _on_failure(self, message: str) -> None:
        self.query_one("#status-msg", Label).update(f"Error: {message}")
        row = self.query_one("#action-row", Container)
        row.mount(Button("< Back", id="btn-back"))
        row.mount(Button("Exit", variant="error", id="btn-exit"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-exit":
            self.app.exit()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
