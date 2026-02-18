"""Individual stock report tab UI."""
import re

import gradio as gr

from src.core.report_generator import ReportGenerator

# Pattern that a valid ticker symbol matches (e.g. 7203.T, AAPL, 285A.T, BRK.B)
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,7}(\.[A-Z]{1,2})?$")

# 4–5 digit bare number → assume Tokyo Stock Exchange ticker (append .T)
_BARE_JP_NUMBER_RE = re.compile(r"^\d{4,5}$")

# Unicode ranges covering Hiragana, Katakana, and CJK Unified Ideographs
_JAPANESE_RE = re.compile(r"[\u3040-\u9fff]")

_AI_HEADER = (
    "### AI アシスタントの分析\n"
    "> *以下は AI による情報提供です。投資助言ではありません。*\n\n"
)


def _looks_like_ticker(text: str) -> bool:
    """Return True if text appears to be a ticker symbol rather than a company name."""
    return bool(_TICKER_RE.match(text.strip().upper()))


def _normalize_ticker(query: str) -> tuple[str, str]:
    """Normalize a ticker query, returning (ticker, note).

    If query is a bare 4-5 digit number, append '.T' to treat it as a
    Tokyo Stock Exchange ticker.  note is a human-readable explanation
    of the correction, or an empty string when no correction was made.
    """
    if _BARE_JP_NUMBER_RE.match(query):
        return query + ".T", f"`{query}` → `{query}.T` (東証ティッカーとして補正)"
    return query.upper(), ""


def _has_japanese(text: str) -> bool:
    """Return True if text contains Japanese characters."""
    return bool(_JAPANESE_RE.search(text))


def _llm_translate_to_english(company_name: str, llm_client) -> str:
    """Ask LLM to translate a Japanese company name to English for Yahoo Finance search.

    Returns empty string if LLM is unavailable or returns an empty response.
    """
    prompt = (
        f"以下の企業名を Yahoo Finance で検索できる英語の正式名称に変換してください。"
        f"企業名のみを出力し、説明や句読点は一切出力しないでください。\n企業名: {company_name}"
    )
    raw = llm_client.generate(prompt, temperature=0.0)
    # Strip potential <think>...</think> tags from reasoning models
    translated = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    return translated


def build_report_tab(yahoo_client, llm_client) -> None:
    """Build the stock report tab."""
    gr.Markdown("## 銘柄レポート")
    gr.Markdown("ティッカーまたは会社名を入力して個別銘柄の財務分析レポートを生成します。")

    with gr.Row():
        with gr.Column(scale=1, min_width=200):
            ticker_input = gr.Textbox(
                label="ティッカー / 会社名",
                placeholder="例: 7203.T、AAPL、三菱重工、Toyota",
            )
            run_btn = gr.Button("レポート生成", variant="primary")
        with gr.Column(scale=3):
            pass

    resolved_md = gr.Markdown(visible=False)

    # Three-column report layout
    with gr.Row():
        with gr.Column(scale=3):
            left_output = gr.Markdown(
                "*ティッカーまたは会社名を入力して実行してください。*"
            )
        with gr.Column(scale=2):
            mid_output = gr.Markdown("")
        with gr.Column(scale=2):
            right_output = gr.Markdown("")

    generator = ReportGenerator(yahoo_client, llm_client)

    def on_run(query: str):
        query = query.strip()
        if not query:
            yield gr.update(visible=False), "ティッカーまたは会社名を入力してください。", "", ""
            return

        yield gr.update(visible=False), "データを取得中...", "", ""

        # --- Ticker resolution ---
        if _looks_like_ticker(query):
            ticker, norm_note = _normalize_ticker(query)
            if norm_note:
                resolved_note = gr.update(value=f"**{norm_note}**", visible=True)
                yield resolved_note, "データを取得中...", "", ""
            else:
                resolved_note = gr.update(visible=False)
        else:
            is_japanese = _has_japanese(query)
            search_query = query
            translation_note = ""

            if is_japanese:
                if llm_client.is_available():
                    yield gr.update(visible=False), f"「{query}」を検索中...", "", ""
                    english_name = _llm_translate_to_english(query, llm_client)
                    if english_name:
                        search_query = english_name
                        translation_note = f" (英語名: {english_name})"
                else:
                    yield gr.update(visible=False), (
                        f"「{query}」は日本語の会社名のようですが、LLM が未読み込みのため英語変換できません。"
                        "ティッカー記号 (例: 7011.T) を直接入力してください。"
                    ), "", ""
                    return

            candidates = yahoo_client.search_tickers(
                search_query, max_results=5, prefer_jpx=is_japanese
            )
            if not candidates:
                yield gr.update(visible=False), (
                    f"「{query}」に対応するティッカーが見つかりませんでした。"
                    "ティッカー記号を直接入力してください。"
                ), "", ""
                return

            ticker = candidates[0]
            info = yahoo_client.get_ticker_info(ticker)
            display_name = info.get("longName") or info.get("shortName") or ticker

            note_lines = [f"**「{query}」→ `{ticker}` ({display_name}){translation_note} として検索します**"]
            if len(candidates) > 1:
                others = "、".join(f"`{c}`" for c in candidates[1:])
                note_lines.append(f"他の候補: {others}")

            resolved_note = gr.update(value="\n\n".join(note_lines), visible=True)
            yield resolved_note, "データを取得中...", "", ""

        # Generate report data without LLM (stream AI analysis into right column)
        data = generator.generate(ticker, skip_llm=True)
        left_md, mid_md, right_md = generator.format_columns(data)

        if data.get("error"):
            yield gr.update(visible=False), left_md, "", ""
            return

        # Show static report first; right column starts with news only
        yield resolved_note, left_md, mid_md, right_md

        # Stream AI analysis into the right column (above news)
        if not llm_client.is_available():
            return

        llm_input = data.get("llm_stock_input")
        if not llm_input:
            return

        # Separator between AI analysis and news
        news_section = ("\n\n---\n\n" + right_md) if right_md.strip() else ""

        accumulated = ""
        for chunk in llm_client.stream_analyze_stock(llm_input):
            accumulated = chunk
            # Use gr.update() for unchanged columns to avoid unnecessary re-renders
            yield (
                gr.update(),
                gr.update(),
                gr.update(),
                _AI_HEADER + accumulated + "▋" + news_section,
            )

        if accumulated:
            yield gr.update(), gr.update(), gr.update(), _AI_HEADER + accumulated + news_section

    run_btn.click(
        on_run,
        inputs=[ticker_input],
        outputs=[resolved_md, left_output, mid_output, right_output],
    )
    ticker_input.submit(
        on_run,
        inputs=[ticker_input],
        outputs=[resolved_md, left_output, mid_output, right_output],
    )
