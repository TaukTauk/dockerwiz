"""Screen 4 — Configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Input, Label


class ConfigureScreen(Screen[None]):
    """Collects app port, optional database credentials, and host port overrides."""

    STEP = "Step 4 of 6"

    def compose(self) -> ComposeResult:
        partial  = self.app.partial  # type: ignore[attr-defined]
        has_db   = "postgres" in partial.services or "mysql" in partial.services
        has_redis = "redis" in partial.services
        has_nginx = "nginx" in partial.services
        has_mongo = "mongo" in partial.services
        db_label = "PostgreSQL" if "postgres" in partial.services else "MySQL"
        default_db_port = 5432 if "postgres" in partial.services else 3306

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
                    classes="config_box"
                ),
                Label("", id="db-error", classes="error-msg"),
            ]

        # Host port overrides
        host_port_widgets: list[Widget] = []
        if has_db:
            host_port_widgets.append(
                Container(
                    Label(f"{db_label} host port"),
                    Input(
                        value=str(partial.host_db_port or default_db_port),
                        placeholder=str(default_db_port),
                        id="host-db-port",
                    ),
                )
            )
        if has_redis:
            host_port_widgets.append(
                Container(
                    Label("Redis host port"),
                    Input(
                        value=str(partial.host_redis_port or 6379),
                        placeholder="6379",
                        id="host-redis-port",
                    ),
                )
            )
        if has_nginx:
            host_port_widgets.append(
                Container(
                    Label("Nginx host port"),
                    Input(
                        value=str(partial.host_nginx_port or 80),
                        placeholder="80",
                        id="host-nginx-port",
                    ),
                )
            )
        if has_mongo:
            host_port_widgets.append(
                Container(
                    Label("MongoDB host port"),
                    Input(
                        value=str(partial.host_mongo_port or 27017),
                        placeholder="27017",
                        id="host-mongo-port",
                    ),
                )
            )

        if host_port_widgets:
            widgets += [
                Label("Host port overrides", classes="field-label"),
                Horizontal(*host_port_widgets, classes="config_box"),
                Label("", id="host-port-error", classes="error-msg"),
            ]

        widgets.append(
            Container(
                Button("< Back", id="btn-back"),
                Button("Next >", variant="primary", id="btn-next"),
                classes="button-row",
            )
        )

        yield VerticalScroll(*widgets, classes="screen-content")

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

    def _read_host_port(self, input_id: str, label: str, default: int) -> int | None:
        """Read an optional host-port input. Returns None if the widget doesn't exist."""
        try:
            widget = self.query_one(f"#{input_id}", Input)
        except Exception:
            return None
        raw = widget.value.strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if not (1 <= val <= 65535):
                raise ValueError
            return val
        except ValueError:
            err = self.query_one("#host-port-error", Label)
            err.update(f"{label} host port must be a number between 1 and 65535.")
            return None

    def _advance(self) -> None:
        partial  = self.app.partial  # type: ignore[attr-defined]
        has_db   = "postgres" in partial.services or "mysql" in partial.services

        # Validate app port
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

        # Read host port overrides
        default_db_port = 5432 if "postgres" in partial.services else 3306
        host_db_port    = self._read_host_port("host-db-port",    "DB",      default_db_port)
        host_redis_port = self._read_host_port("host-redis-port", "Redis",   6379)
        host_nginx_port = self._read_host_port("host-nginx-port", "Nginx",   80)
        host_mongo_port = self._read_host_port("host-mongo-port", "MongoDB", 27017)

        # If any host port read returned None it means a validation error was shown
        if has_db and host_db_port is None:
            return
        if "redis" in partial.services and host_redis_port is None:
            return
        if "nginx" in partial.services and host_nginx_port is None:
            return
        if "mongo" in partial.services and host_mongo_port is None:
            return

        self.app.partial = partial.model_copy(update={  # type: ignore[attr-defined]
            "app_port":       port,
            "db_user":        db_user,
            "db_password":    db_password,
            "db_name":        db_name,
            "db_port":        db_port,
            "host_db_port":   host_db_port,
            "host_redis_port": host_redis_port,
            "host_nginx_port": host_nginx_port,
            "host_mongo_port": host_mongo_port,
        })

        from dockerwiz.tui.screens.review import ReviewScreen  # noqa: PLC0415
        self.app.push_screen(ReviewScreen())
