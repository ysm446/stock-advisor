"""Model management tab for loading/unloading Hugging Face Transformers models."""
import threading
from typing import TYPE_CHECKING

import gradio as gr

if TYPE_CHECKING:
    from src.data.llm_client import LLMClient


def _get_status_text(llm_client: "LLMClient") -> str:
    """Return a human-readable status string for the model."""
    status = llm_client.get_status()
    if status["loading"]:
        model_id = status["current_model_id"] or "..."
        return f"読み込み中: {model_id}"
    if status["available"]:
        vram_alloc = status["vram_allocated_gb"]
        vram_total = status["vram_total_gb"]
        lines = [f"読み込み済: {status['current_model_id']}"]
        if vram_total > 0:
            lines.append(f"VRAM: {vram_alloc:.1f} GB / {vram_total:.1f} GB")
        return "\n".join(lines)
    if status["load_error"]:
        return f"エラー: {status['load_error']}"
    return "モデル未読み込み — 「読み込み」ボタンを押してください。"


def _get_vram_bar(llm_client: "LLMClient") -> str:
    """Return a Markdown VRAM usage bar."""
    status = llm_client.get_status()
    total = status["vram_total_gb"]
    if total <= 0:
        return "GPU: 未検出 (CPU モードで動作)"
    alloc = status["vram_allocated_gb"]
    pct = min(alloc / total, 1.0)
    filled = int(round(pct * 20))
    bar = "█" * filled + "░" * (20 - filled)
    return f"VRAM `{bar}` {alloc:.1f} / {total:.1f} GB ({pct * 100:.0f}%)"


def build_model_tab(llm_client: "LLMClient") -> None:
    """Build the model management tab UI.

    Args:
        llm_client: The shared LLMClient instance (mutable, owned by app.py).
    """
    from src.data.llm_client import LLMClient  # noqa: PLC0415

    gr.Markdown("## モデル管理")
    gr.Markdown(
        "Hugging Face Transformers モデルをローカルで読み込みます。  \n"
        "モデルファイルは `models/` フォルダにキャッシュされます。"
        "初回はダウンロードが発生します (Qwen3-8B: 約 5 GB)。"
    )

    # Resolve initial dropdown value from persisted model
    _last_model_id = llm_client.get_last_persisted_model()
    _initial_model_name = "Qwen3-8B"
    if _last_model_id:
        for _name, _mid in LLMClient.SUPPORTED_MODELS.items():
            if _mid == _last_model_id:
                _initial_model_name = _name
                break

    with gr.Row():
        # --- Left column: status ---
        with gr.Column(scale=1):
            gr.Markdown("### 現在の状態")
            status_box = gr.Textbox(
                label="モデル状態",
                value=_get_status_text(llm_client),
                interactive=False,
                lines=3,
            )
            vram_md = gr.Markdown(_get_vram_bar(llm_client))

        # --- Right column: controls ---
        with gr.Column(scale=2):
            gr.Markdown("### モデル選択")
            gr.Markdown(
                "| モデル | VRAM 目安 |\n"
                "|--------|----------|\n"
                "| Qwen3-8B  | ~6 GB |\n"
                "| Qwen3-14B | ~10 GB |\n"
                "| Qwen3-32B | ~22 GB (Q4相当) |"
            )
            with gr.Row():
                model_dd = gr.Dropdown(
                    choices=list(LLMClient.SUPPORTED_MODELS.keys()),
                    value=_initial_model_name,
                    label="モデル",
                    scale=3,
                )
                load_btn = gr.Button("読み込み", variant="primary", scale=1)
                unload_btn = gr.Button("アンロード", scale=1)

            log_box = gr.Textbox(
                label="ログ",
                value="",
                interactive=False,
                lines=6,
                max_lines=6,
            )

    # Auto-refresh timer: polls every 2 seconds
    timer = gr.Timer(value=2.0, active=True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_load(model_name: str):
        model_id = LLMClient.SUPPORTED_MODELS.get(model_name)
        if not model_id:
            return (
                f"不明なモデル名: {model_name}",
                _get_status_text(llm_client),
                _get_vram_bar(llm_client),
            )
        if llm_client.is_loading():
            return (
                "既に読み込み中です。完了をお待ちください。",
                _get_status_text(llm_client),
                _get_vram_bar(llm_client),
            )

        def progress_callback(msg: str) -> None:
            llm_client._load_log = msg

        thread = threading.Thread(
            target=llm_client.load_model,
            args=(model_id,),
            kwargs={"on_progress": progress_callback},
            daemon=True,
        )
        thread.start()

        initial_log = f"読み込みを開始しました: {model_id}"
        llm_client._load_log = initial_log
        return initial_log, _get_status_text(llm_client), _get_vram_bar(llm_client)

    load_btn.click(
        on_load,
        inputs=[model_dd],
        outputs=[log_box, status_box, vram_md],
    )

    def on_unload():
        llm_client.unload_model()
        msg = "モデルをアンロードしました。"
        llm_client._load_log = msg
        return msg, _get_status_text(llm_client), _get_vram_bar(llm_client)

    unload_btn.click(
        on_unload,
        outputs=[log_box, status_box, vram_md],
    )

    def poll_status():
        return (
            llm_client._load_log or "",
            _get_status_text(llm_client),
            _get_vram_bar(llm_client),
        )

    timer.tick(poll_status, outputs=[log_box, status_box, vram_md])
