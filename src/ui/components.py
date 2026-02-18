"""Shared Gradio UI components."""
import gradio as gr


def llm_status_badge(is_available: bool) -> str:
    """Return a Markdown badge string indicating LLM model load status."""
    if is_available:
        return "**モデル読み込み済**"
    return "**モデル未読み込み** — 「モデル管理」タブでモデルを読み込んでください。"


def error_markdown(message: str) -> str:
    """Wrap an error message in Markdown."""
    return f"**エラー:** {message}"


def info_markdown(message: str) -> str:
    """Wrap an info message in Markdown."""
    return f"{message}"


def build_llm_status_row(llm_client) -> gr.Markdown:
    """Build a Markdown component showing current LLM status."""
    status = llm_status_badge(llm_client.is_available())
    return gr.Markdown(status)
