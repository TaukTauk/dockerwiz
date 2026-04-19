"""Screen 2 — Language and Framework."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, RadioButton, RadioSet, Select

from dockerwiz.stacks import frameworks_for_language

_LANGUAGES = ["python", "go", "node"]
_LANGUAGE_LABELS = {"python": "Python", "go": "Go", "node": "Node.js"}


class LanguageScreen(Screen[None]):
    """Collects language, framework, and base image version."""

    STEP = "Step 2 of 6"

    def compose(self) -> ComposeResult:
        partial  = self.app.partial  # type: ignore[attr-defined]
        cur_lang = partial.language or "python"
        cur_fw   = partial.framework

        lang_radios = [
            RadioButton(_LANGUAGE_LABELS[lang], value=(lang == cur_lang), id=f"lang-{lang}")
            for lang in _LANGUAGES
        ]
        fw_options = self._fw_options(cur_lang)
        image_options = self._image_options(cur_lang)

        yield Container(
            Label("Language and Framework", classes="screen-title"),
            Label("─" * 44, classes="divider"),

            Horizontal(
                Container(
                    Label("Language", classes="field-label"),
                    RadioSet(*lang_radios, id="lang-radio"),
                ),
                Container(
                    Label("Framework", classes="field-label"),
                    RadioSet(
                        *[RadioButton(label, value=(fw == cur_fw), id=f"fw-{fw}")
                          for fw, label in fw_options],
                        id="fw-radio",
                    ),
                ),
            ),

            Label("Base image", classes="field-label"),
            Select(
                options=[(tag, tag) for tag in image_options],
                value=partial.base_image or (image_options[0] if image_options else Select.BLANK),
                id="base-image-select",
            ),
            Label("", id="image-source-label", classes="hint-msg"),

            Container(
                Button("< Back", id="btn-back"),
                Button("Next >", variant="primary", id="btn-next"),
                classes="button-row",
            ),
            classes="screen-content",
        )

    def on_mount(self) -> None:
        self.sub_title = self.STEP
        is_live = self.app.is_live  # type: ignore[attr-defined]
        src_label = self.query_one("#image-source-label", Label)
        if is_live:
            src_label.update("Fetched from Docker Hub")
        else:
            src_label.update("Showing cached defaults — could not reach Docker Hub")
        self._refresh_next_button()

    def _fw_options(self, language: str) -> list[tuple[str, str]]:
        return [(s.framework, s.label) for s in frameworks_for_language(language)]

    def _image_options(self, language: str) -> list[str]:
        versions: dict[str, list[str]] = self.app.available_versions  # type: ignore[attr-defined]
        # map language to cache key
        key_map = {"python": "python", "go": "golang", "node": "node"}
        key  = key_map.get(language, language)
        tags = versions.get(key, [])
        return tags if tags else [f"{language}:latest"]

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "lang-radio":
            language  = _LANGUAGES[event.index]
            fw_radio  = self.query_one("#fw-radio", RadioSet)
            fw_options = self._fw_options(language)
            fw_radio.remove_children()
            for i, (fw, label) in enumerate(fw_options):
                fw_radio.mount(RadioButton(label, value=(i == 0), id=f"fw-{fw}"))

            # Update image dropdown
            sel = self.query_one("#base-image-select", Select)
            new_options = self._image_options(language)
            sel.set_options([(t, t) for t in new_options])
            if new_options:
                sel.value = new_options[0]

        self._refresh_next_button()

    def _refresh_next_button(self) -> None:
        lang_radio = self.query_one("#lang-radio", RadioSet)
        fw_radio   = self.query_one("#fw-radio", RadioSet)
        self.query_one("#btn-next", Button).disabled = (
            lang_radio.pressed_index is None or fw_radio.pressed_index is None
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-next":
            self._advance()

    def _advance(self) -> None:
        lang_radio = self.query_one("#lang-radio", RadioSet)
        fw_radio   = self.query_one("#fw-radio", RadioSet)
        sel        = self.query_one("#base-image-select", Select)

        if lang_radio.pressed_index is None or fw_radio.pressed_index is None:
            return

        language   = _LANGUAGES[lang_radio.pressed_index]
        fw_options = self._fw_options(language)
        framework  = fw_options[fw_radio.pressed_index][0]
        base_image = (
            str(sel.value) if sel.value != Select.BLANK else self._image_options(language)[0]
        )

        # Resolve default port from stacks
        from dockerwiz.stacks import get_stack  # noqa: PLC0415
        stack = get_stack(language, framework)
        default_port = stack.default_port if stack else 8000

        partial = self.app.partial  # type: ignore[attr-defined]
        self.app.partial = partial.model_copy(update={  # type: ignore[attr-defined]
            "language":   language,
            "framework":  framework,
            "base_image": base_image,
            "app_port":   partial.app_port or default_port,
        })

        from dockerwiz.tui.screens.services import ServicesScreen  # noqa: PLC0415
        self.app.push_screen(ServicesScreen())
