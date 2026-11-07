import argparse
import json
import logging

from voc_rag.config import ROOT, Settings
from voc_rag.indexing import ReviewIndexer, index_name
from voc_rag.pipeline import build_pipeline
from voc_rag.preparation import ReviewDataPreparer

EXAMPLES_PATH = ROOT / "examples" / "questions.json"
EXAMPLES_OUTPUT = ROOT / "docs" / "exemplos.md"


def run_examples(settings: Settings) -> None:
    from voc_rag.evaluation import normalized_conditions

    pipeline = build_pipeline(settings)
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    sections = [
        "# Exemplos de perguntas e respostas", "",
        f"Modelo de chat: `{settings.llm_provider}:{settings.chat_model}`. "
        f"Embeddings: `{settings.embedding_provider}:{settings.embedding_model}`. "
        f"Banco vetorial: `{settings.vector_store}`. Multi-query: {settings.use_multi_query}. BM25: {settings.use_bm25}. "
        f"Rerank: {settings.reranker if settings.use_rerank else False}.", "",
    ]
    for example in examples:
        result = pipeline.ask(example["question"])
        checks = []
        if "expected_status" in example:
            checks.append("status ok" if result.status.value == example["expected_status"] else f"status esperado: {example['expected_status']}")
        if "expected_filters" in example and result.filters is not None:
            same = normalized_conditions(result.filters.conditions()) == normalized_conditions(example["expected_filters"])
            checks.append("filtros ok" if same else f"filtros esperados: {example['expected_filters']}")
        sections += [f"## {example['type']}", "", result.to_markdown()]
        print(f"{example['type']}: {result.status.value} ({', '.join(checks) or 'sem conferência'})")
    EXAMPLES_OUTPUT.parent.mkdir(exist_ok=True)
    EXAMPLES_OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"Resultados salvos em {EXAMPLES_OUTPUT}")


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="voc_rag")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare", help="limpa as avaliações e gera os arquivos parquet")
    commands.add_parser("index", help="gera os embeddings e cria o índice no Chroma")
    ask = commands.add_parser("ask", help="faz uma pergunta pelo terminal")
    ask.add_argument("question")
    commands.add_parser("examples", help="roda as perguntas de exemplo e salva docs/exemplos.md")
    evaluate = commands.add_parser("evaluate", help="mede recuperação, recusas e fundamentação e salva docs/avaliacao.md")
    evaluate.add_argument("--judge", action="store_true", help="avalia a fundamentação dos insights com um LLM-juiz")
    evaluate.add_argument("--repeat", type=int, default=1, help="repetições das perguntas, para medir a variação")
    evaluate.add_argument("--configs", default="baseline,multi_query,hybrid,full", help="configurações separadas por vírgula")
    evaluate.add_argument("--split", choices=["dev", "test", "all"], default="all", help="perguntas avaliadas")
    evaluate.add_argument("--skip-retrieval", action="store_true", help="pula a precisão@10 da recuperação")
    args = parser.parse_args()

    settings = Settings()
    if args.command == "prepare":
        print(ReviewDataPreparer(settings).run())
    elif args.command == "index":
        print(f"{ReviewIndexer(settings).build()} documentos no índice {index_name(settings)}")
    elif args.command == "ask":
        print(build_pipeline(settings).ask(args.question).to_markdown())
    elif args.command == "examples":
        run_examples(settings)
    elif args.command == "evaluate":
        from voc_rag.evaluation import PIPELINE_CONFIGS, run_evaluation

        configs = [config.strip() for config in args.configs.split(",") if config.strip()]
        unknown = [config for config in configs if config not in PIPELINE_CONFIGS]
        if unknown:
            parser.error(f"configurações desconhecidas: {', '.join(unknown)}. Use {', '.join(PIPELINE_CONFIGS)}.")
        print(run_evaluation(settings, args.judge, args.repeat, configs, not args.skip_retrieval, args.split))


if __name__ == "__main__":
    main()
