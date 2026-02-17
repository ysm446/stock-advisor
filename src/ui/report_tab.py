"""Individual stock report tab UI."""
import gradio as gr

from src.core.report_generator import ReportGenerator


def build_report_tab(yahoo_client, llm_client) -> None:
    """Build the stock report tab."""
    gr.Markdown("## 📋 銘柄レポート")
    gr.Markdown("ティッカーを入力して個別銘柄の財務分析レポートを生成します。")

    with gr.Row():
        ticker_input = gr.Textbox(
            label="ティッカー",
            placeholder="例: 7203.T または AAPL",
            scale=3,
        )
        run_btn = gr.Button("📋 レポート生成", variant="primary", scale=1)

    report_output = gr.Markdown("*ティッカーを入力して実行してください。*")

    generator = ReportGenerator(yahoo_client, llm_client)

    def generate_report(ticker: str) -> str:
        ticker = ticker.strip()
        if not ticker:
            return "⚠️ ティッカーを入力してください。"
        data = generator.generate(ticker)
        return generator.format_markdown(data)

    def on_run(ticker: str):
        yield "⏳ データを取得中..."
        result = generate_report(ticker)
        yield result

    run_btn.click(on_run, inputs=[ticker_input], outputs=[report_output])
    ticker_input.submit(on_run, inputs=[ticker_input], outputs=[report_output])
