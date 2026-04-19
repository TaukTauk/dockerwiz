"""Screen 4 — Configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Input, Label


class ConfigureScreen(Screen[None]):
    """Collects app port and optional database credentials."""

    STEP = "Step 4 of 6"

    def compose(self) -> ComposeResult:
        partial  = self.app.partial  # type: ignore[attr-defined]
        has_db   = "postgres" in partial.services or "mysql" in partial.services
        db_label = "PostgreSQL" if "postgres" in partial.services else "MySQL"

        widgets: list[Widget] = [
            Label("Configuration", classes="screen-title"),
            Label("─" * 44, classes="divider"),

            Label("Application", classes="field-label"),
            Label("App port", classes="field-label"),
            Input(
                value=str(partial.app_port or ""),
                placeholder="8000",
                id="app-port",
            ),
            Label("", id="port-error", classes="error-msg"),
        ]

        if has_db:
            widgets += [
                Label(db_label, classes="field-label"),
                Horizontal(
                    Container(
                        Label("DB user"),
                        Input(value=partial.db_user or "myuser", id="db-user"),
                    ),
                    Container(
                        Label("DB password"),
                        Input(
                            value=partial.db_password or "",
                            password=True,
                            id="db-password",
                        ),
                        Button("show", id="btn-toggle-pw", variant="default"),
                    ),
                    Container(
                        Label("DB name"),
                        Input(value=partial.db_name or "mydb", id="db-name"),
                    ),
                ),
                Label("", id="db-error", classes="error-msg"),
            ]

        widgets.append(
            Container(
                Button("< Back", id="btn-back"),
                Button("Next >", variant="primary", id="btn-next"),
                classes="button-row",
            )
        )

        yield Container(*widgets, classes="screen-content")

    def on_mount(self) -> None:
        self.sub_title = self.STEP

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-next":
            self._advance()
        elif event.button.id == "btn-toggle-pw":
            pw_input = self.query_one("#db-password", Input)
            pw_input.password = not pw_input.password

    def _advance(self) -> None:
        partial  = self.app.partial  # type: ignore[attr-defined]
        has_db   = "postgres" in partial.services or "mysql" in partial.services

        # Validate port
        port_str = self.query_one("#app-port", Input).value.strip()
        port_err = self.query_one("#port-error", Label)
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
            port_err.update("")
        except ValueError:
            port_err.update("App port must be a number between 1 and 65535.")
            return

        db_user     = None
        db_password = None
        db_name     = None
        db_port     = None

        if has_db:
            db_user  = self.query_one("#db-user", Input).value.strip()
            db_name  = self.query_one("#db-name", Input).value.strip()
            db_password = self.query_one("#db-password", Input).value

            db_err = self.query_one("#db-error", Label)
            if not db_user:
                db_err.update("DB user cannot be empty.")
                return
            if not db_name:
                db_err.update("DB name cannot be empty.")
                return
            db_err.update("")
            db_port = 5432 if "postgres" in partial.services else 3306

        self.app.partial = partial.model_copy(update={  # type: ignore[attr-defined]
            "app_port":    port,
            "db_user":     db_user,
            "db_password": db_password,
            "db_name":     db_name,
            "db_port":     db_port,
        })

        from dockerwiz.tui.screens.review import ReviewScreen  # noqa: PLC0415
        self.app.push_screen(ReviewScreen())
