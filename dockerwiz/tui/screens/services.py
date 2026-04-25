"""Screen 3 — Services."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Label

from dockerwiz.services import SERVICES, ServiceDefinition, get_mutex_conflicts


class ServicesScreen(Screen[None]):
    """Collects the list of services to include."""

    STEP = "Step 3 of 6"

    def compose(self) -> ComposeResult:
        partial  = self.app.partial  # type: ignore[attr-defined]
        selected = set(partial.services)

        # Group services by category
        categories: dict[str, list[ServiceDefinition]] = {}
        for svc in SERVICES:
            categories.setdefault(svc.category, []).append(svc)

        widgets: list[Widget] = [
            Label("Services", classes="screen-title"),
            Label("─" * 44, classes="divider"),
            Label("Select the services your project needs.", classes="hint-msg"),
        ]

        for category, svcs in categories.items():
            widgets.append(Label(category, classes="field-label"))
            for svc in svcs:
                row = Container(
                    Checkbox(
                        f"{svc.label}",
                        value=(svc.name in selected),
                        id=f"svc-{svc.name}",
                    ),
                    Label(f"{svc.image}  port {svc.default_port}", classes="hint-msg"),
                    classes="service-row",
                )
                widgets.append(row)

        widgets += [
            Label("", id="mutex-error", classes="error-msg"),
            Container(
                Button("< Back", id="btn-back"),
                Button("Next >", variant="primary", id="btn-next"),
                classes="button-row",
            ),
        ]

        yield VerticalScroll(*widgets, classes="screen-content")

    def on_mount(self) -> None:
        self.sub_title = self.STEP

    def on_checkbox_changed(self, _event: Checkbox.Changed) -> None:
        self._validate()

    def _selected_services(self) -> list[str]:
        return [
            svc.name
            for svc in SERVICES
            if self.query_one(f"#svc-{svc.name}", Checkbox).value
        ]

    def _validate(self) -> None:
        selected   = self._selected_services()
        conflicts  = get_mutex_conflicts(selected)
        err_label  = self.query_one("#mutex-error", Label)
        next_btn   = self.query_one("#btn-next", Button)

        if conflicts:
            a, b = conflicts[0]
            err_label.update(f"! Select either {a} or {b}, not both.")
            next_btn.disabled = True
        else:
            err_label.update("")
            next_btn.disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-next":
            self._advance()

    def _advance(self) -> None:
        selected  = self._selected_services()
        conflicts = get_mutex_conflicts(selected)
        if conflicts:
            return

        partial = self.app.partial  # type: ignore[attr-defined]
        self.app.partial = partial.model_copy(update={"services": selected})  # type: ignore[attr-defined]

        from dockerwiz.tui.screens.configure import ConfigureScreen  # noqa: PLC0415
        self.app.push_screen(ConfigureScreen())
