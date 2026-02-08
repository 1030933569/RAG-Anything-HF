"""
Hugging Face Space entrypoint for RAG-Anything with Docling parser.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import gradio as gr
from dotenv import load_dotenv

from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from raganything import RAGAnything, RAGAnythingConfig


load_dotenv(dotenv_path=".env", override=False)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


BASE_DATA_DIR = Path(os.getenv("HF_DATA_DIR", "/data"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DATA_DIR / "upload_tmp")))
WORKING_DIR = Path(os.getenv("WORKING_DIR", str(BASE_DATA_DIR / "rag_storage")))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DATA_DIR / "output")))

for path in (UPLOAD_DIR, WORKING_DIR, OUTPUT_DIR):
    path.mkdir(parents=True, exist_ok=True)


LLM_BASE_URL = os.getenv("LLM_BINDING_HOST", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_BINDING_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o")

EMBED_BASE_URL = os.getenv("EMBEDDING_BINDING_HOST", LLM_BASE_URL)
EMBED_API_KEY = os.getenv("EMBEDDING_BINDING_API_KEY", LLM_API_KEY)
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBED_DIM = int(os.getenv("EMBEDDING_DIM", "3072"))


def llm_model_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[list] = None,
    **kwargs,
):
    return openai_complete_if_cache(
        model=LLM_MODEL,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        **kwargs,
    )


def vision_model_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[list] = None,
    image_data: Optional[str] = None,
    messages: Optional[list] = None,
    **kwargs,
):
    if messages:
        return openai_complete_if_cache(
            model=VISION_MODEL,
            prompt="",
            system_prompt=None,
            history_messages=[],
            messages=messages,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            **kwargs,
        )

    if image_data:
        request_messages = []
        if system_prompt:
            request_messages.append({"role": "system", "content": system_prompt})
        request_messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        )
        return openai_complete_if_cache(
            model=VISION_MODEL,
            prompt="",
            system_prompt=None,
            history_messages=[],
            messages=request_messages,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            **kwargs,
        )

    return llm_model_func(prompt, system_prompt, history_messages, **kwargs)


embedding_func = EmbeddingFunc(
    embedding_dim=EMBED_DIM,
    max_token_size=8192,
    func=lambda texts: openai_embed(
        texts=texts,
        model=EMBED_MODEL,
        api_key=EMBED_API_KEY,
        base_url=EMBED_BASE_URL,
    ),
)


config = RAGAnythingConfig(
    working_dir=str(WORKING_DIR),
    parser_output_dir=str(OUTPUT_DIR),
    parser="docling",
    parse_method=os.getenv("PARSE_METHOD", "auto"),
    display_content_stats=_env_bool("DISPLAY_CONTENT_STATS", True),
    enable_image_processing=_env_bool("ENABLE_IMAGE_PROCESSING", True),
    enable_table_processing=_env_bool("ENABLE_TABLE_PROCESSING", True),
    enable_equation_processing=_env_bool("ENABLE_EQUATION_PROCESSING", True),
)

rag = RAGAnything(
    config=config,
    llm_model_func=llm_model_func,
    vision_model_func=vision_model_func,
    embedding_func=embedding_func,
)


def _check_api_keys() -> Optional[str]:
    if not LLM_API_KEY:
        return "缺少 `LLM_BINDING_API_KEY`，请在 HF Space Secrets 中配置。"
    if not EMBED_API_KEY:
        return "缺少 `EMBEDDING_BINDING_API_KEY`，请在 HF Space Secrets 中配置。"
    return None


async def ingest_document(file_path: str, parse_method: str) -> str:
    error = _check_api_keys()
    if error:
        return error

    if not file_path:
        return "请先上传文档。"

    src = Path(file_path)
    if not src.exists():
        return f"文件不存在: {src}"

    dst = UPLOAD_DIR / src.name
    try:
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    except Exception:
        dst = src

    try:
        await rag.process_document_complete(
            file_path=str(dst),
            output_dir=str(OUTPUT_DIR),
            parse_method=parse_method,
        )
        return f"入库完成: {dst.name}\n解析器: docling\n工作目录: {WORKING_DIR}"
    except Exception as exc:
        return f"入库失败: {exc}"


async def ask_question(question: str, mode: str) -> str:
    error = _check_api_keys()
    if error:
        return error

    if not question or not question.strip():
        return "请输入问题。"

    try:
        result = await rag.aquery(question.strip(), mode=mode)
        return str(result)
    except Exception as exc:
        return f"查询失败: {exc}"


with gr.Blocks(title="RAG-Anything + Docling on HF") as demo:
    gr.Markdown(
        """
# RAG-Anything + Docling (HF Space)

流程：上传文档 -> Docling 解析并入库 -> 发起查询。  
解析器固定为 `docling`，无需本地 MinerU。
        """.strip()
    )

    with gr.Row():
        upload = gr.File(label="上传文档", type="filepath")
        parse_method = gr.Dropdown(
            label="解析模式",
            choices=["auto", "ocr", "txt"],
            value=os.getenv("PARSE_METHOD", "auto"),
        )

    ingest_btn = gr.Button("解析并入库", variant="primary")
    ingest_status = gr.Textbox(label="状态", lines=4, interactive=False)
    ingest_btn.click(
        fn=ingest_document,
        inputs=[upload, parse_method],
        outputs=[ingest_status],
    )

    question = gr.Textbox(label="问题", lines=3, placeholder="输入你的问题")
    query_mode = gr.Dropdown(
        label="检索模式",
        choices=["hybrid", "local", "global", "naive"],
        value="hybrid",
    )
    query_btn = gr.Button("查询", variant="primary")
    answer = gr.Markdown(label="回答")
    query_btn.click(fn=ask_question, inputs=[question, query_mode], outputs=[answer])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
    )
