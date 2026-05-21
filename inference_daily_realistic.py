#!/usr/bin/env python3
"""Final daily diary inference CLI for the realistic_daily KoBART model.

This script is meant to be the GitHub-friendly entry point:

    python inference_daily_realistic.py --input data/one_line_texts.txt
    python inference_daily_realistic.py --one-line "왕관 쓰고 신난 하루" --one-line "다 같이 스트레칭"
    python inference_daily_realistic.py --jsonl inputs.jsonl --output outputs/preds.jsonl

The model was trained with a prefixed source format:

    [문장수: 3~5문장]
    [한줄일기]
    - ...
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


DEFAULT_MODEL_PATH = (
    "generated/aiary_v3_realistic_daily_20260509/"
    "models/kobart_student_round5_realistic_daily"
)
DEFAULT_OUTPUT_JSON = "outputs/generated_diary_realistic.json"
DEFAULT_OUTPUT_TXT = "outputs/generated_diary_realistic.txt"

TIME_MARKERS = [
    "아침",
    "오전",
    "점심",
    "낮",
    "낮잠",
    "오후",
    "저녁",
    "밤",
    "하원",
    "등원",
    "집에 와",
    "집에 돌아",
    "돌아와",
    "돌아오",
    "씻고",
    "잠들기 전",
    "일어나",
]
CLICHE_PATTERNS = [
    "소소한 순간",
    "작은 순간들이 모여",
    "마음이 놓였다",
    "마음이 놓이는",
    "행복한 하루",
    "즐거운 시간을 보냈다",
    "즐거운 하루",
    "앞으로도",
    "참 소중",
    "소중한 기억",
    "뿌듯했다",
    "흐뭇했다",
    "특별한 하루",
    "특별하게 느껴졌다",
    "오래 기억에 남는 날",
]
STOPWORDS = {"오늘", "아이", "아기", "우리", "모습", "하루", "시간", "정말", "조금"}
WORD_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}|[0-9]+")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")


@dataclass(frozen=True)
class DecodeConfig:
    name: str
    max_new_tokens: int
    min_new_tokens: int
    num_beams: int
    no_repeat_ngram_size: int
    repetition_penalty: float
    length_penalty: float


def normalize_space(text: Any) -> str:
    text = str(text or "").replace("\u200b", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_one_line(text: Any) -> str:
    text = normalize_space(text)
    return text.strip(" -•\t")


def dedupe_keep_order(items: Iterable[Any], max_items: int = 10) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = clean_one_line(item)
        key = re.sub(r"\s+", "", text)
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max_items:
            break
    return out


def sentence_hint(count: int) -> str:
    if count <= 2:
        return "2~3문장"
    if count <= 5:
        return "3~5문장"
    if count <= 8:
        return "5~7문장"
    return "6~9문장"


def sentence_bounds(count: int) -> Dict[str, int]:
    if count <= 2:
        return {"target_min": 2, "target_max": 3, "hard_max": 4}
    if count <= 5:
        return {"target_min": 3, "target_max": 5, "hard_max": 6}
    if count <= 8:
        return {"target_min": 5, "target_max": 7, "hard_max": 8}
    return {"target_min": 6, "target_max": 9, "hard_max": 10}


def build_model_input(one_lines: List[str]) -> str:
    lines = dedupe_keep_order(one_lines)
    bullets = "\n".join(f"- {line}" for line in lines)
    return f"[문장수: {sentence_hint(len(lines))}]\n[한줄일기]\n{bullets}"


def split_sentences(text: str) -> List[str]:
    text = normalize_space(text)
    return [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


def ensure_sentence_end(text: str) -> str:
    text = normalize_space(text)
    if not text:
        return ""
    if re.search(r"[.!?。！？]\s*$", text):
        return text
    last = max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind("。"), text.rfind("！"), text.rfind("？"))
    if last >= 20:
        return text[: last + 1].strip()
    return text + "."


def fix_model_artifacts(text: str) -> str:
    text = normalize_space(text)
    text = text.replace("내가관", "왕관")
    text = text.replace("주토피아와 주토피아", "주토피아")
    text = text.replace("반짝 반짝", "반짝반짝")
    return text


def norm_sentence_for_dup(sentence: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", sentence or "")


def cut_after_duplicate_sentence(text: str) -> str:
    seen = set()
    kept = []
    for sentence in split_sentences(text):
        key = norm_sentence_for_dup(sentence)
        if len(key) >= 8 and key in seen:
            break
        if len(key) >= 8:
            seen.add(key)
        kept.append(sentence)
    return ensure_sentence_end(" ".join(kept))


def has_repeated_ngram(sentence: str, n: int = 4, min_repeats: int = 2) -> bool:
    toks = WORD_RE.findall(sentence or "")
    if len(toks) < n * 2:
        return False
    counts: Dict[Any, int] = {}
    for i in range(len(toks) - n + 1):
        gram = tuple(toks[i : i + n])
        counts[gram] = counts.get(gram, 0) + 1
        if counts[gram] >= min_repeats:
            return True
    return False


def drop_sentences_with_repeated_ngram(text: str) -> str:
    kept = [s for s in split_sentences(text) if not has_repeated_ngram(s)]
    return ensure_sentence_end(" ".join(kept))


def drop_cliche_sentences(text: str, one_line_count: int) -> str:
    bounds = sentence_bounds(one_line_count)
    sentences = split_sentences(text)
    kept = [s for s in sentences if not has_cliche(s)]
    if len(kept) >= bounds["target_min"]:
        return ensure_sentence_end(" ".join(kept))
    return ensure_sentence_end(" ".join(sentences))


def postprocess_output(text: str, one_line_count: int) -> str:
    bounds = sentence_bounds(one_line_count)
    text = fix_model_artifacts(text)
    text = ensure_sentence_end(text)
    text = drop_sentences_with_repeated_ngram(text)
    text = cut_after_duplicate_sentence(text)
    text = drop_cliche_sentences(text, one_line_count)
    text = " ".join(split_sentences(text)[: bounds["hard_max"]])
    return ensure_sentence_end(text)


def ko_words(text: str) -> List[str]:
    return re.findall(r"[가-힣]{2,}", text or "")


def content_words(text: str) -> List[str]:
    out = []
    seen = set()
    for word in ko_words(text):
        if word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        out.append(word)
    return out


def coverage_score(one_lines: List[str], diary: str) -> float:
    if not one_lines:
        return 0.0
    hit = 0
    for line in one_lines:
        kws = content_words(line)[:8]
        if not kws or any(k in diary for k in kws):
            hit += 1
    return hit / max(1, len(one_lines))


def repeated_ngram_ratio(text: str, n: int = 4) -> float:
    toks = WORD_RE.findall(text or "")
    if len(toks) < n * 2:
        return 0.0
    grams = [tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)]
    return 1.0 - (len(set(grams)) / max(1, len(grams)))


def duplicate_sentence_ratio(text: str) -> float:
    sents = [norm_sentence_for_dup(s) for s in split_sentences(text)]
    sents = [s for s in sents if len(s) >= 8]
    if not sents:
        return 0.0
    return 1.0 - (len(set(sents)) / len(sents))


def unsupported_time_markers(one_lines: List[str], diary: str) -> List[str]:
    source = " ".join(one_lines)
    return [marker for marker in TIME_MARKERS if marker in diary and marker not in source]


def has_cliche(text: str) -> bool:
    return any(pattern in (text or "") for pattern in CLICHE_PATTERNS)


def score_output(one_lines: List[str], diary: str) -> Dict[str, Any]:
    unsupported = unsupported_time_markers(one_lines, diary)
    return {
        "sent_count": count_sentences(diary),
        "coverage": round(coverage_score(one_lines, diary), 4),
        "has_cliche": has_cliche(diary),
        "repeated_ngram_ratio": round(repeated_ngram_ratio(diary), 4),
        "duplicate_sentence_ratio": round(duplicate_sentence_ratio(diary), 4),
        "unsupported_time_markers": unsupported,
        "unsupported_time_count": len(unsupported),
    }


def candidate_score(one_lines: List[str], text: str) -> float:
    metrics = score_output(one_lines, text)
    bounds = sentence_bounds(len(one_lines))
    score = 100.0
    score -= (1.0 - metrics["coverage"]) * 35.0
    score -= metrics["repeated_ngram_ratio"] * 40.0
    score -= metrics["duplicate_sentence_ratio"] * 45.0
    score -= metrics["unsupported_time_count"] * 30.0
    if metrics["has_cliche"]:
        score -= 24.0
    if metrics["sent_count"] < bounds["target_min"]:
        score -= (bounds["target_min"] - metrics["sent_count"]) * 8.0
    if metrics["sent_count"] > bounds["target_max"]:
        score -= (metrics["sent_count"] - bounds["target_max"]) * 7.0
    if not text:
        score -= 100.0
    return round(score, 4)


def grounded_short_config(one_line_count: int, args: argparse.Namespace) -> DecodeConfig:
    bounds = sentence_bounds(one_line_count)
    token_floor = max(args.min_new_tokens, bounds["target_min"] * 18)
    token_mid = max(args.max_new_tokens, bounds["hard_max"] * 42)
    return DecodeConfig("grounded_short", max(token_mid - 35, token_floor + 30), token_floor, max(3, args.num_beams), args.no_repeat_ngram_size, max(args.repetition_penalty, 1.20), 0.58)


def select_device(name: str) -> torch.device:
    if name == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested, but torch.backends.mps.is_available() is False.")
        return torch.device("mps")
    if name == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is False.")
        return torch.device("cuda")
    if name == "cpu":
        return torch.device("cpu")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def generate_with_config(model: Any, tokenizer: Any, model_input: str, device: torch.device, cfg: DecodeConfig, args: argparse.Namespace) -> str:
    enc = tokenizer(model_input, return_tensors="pt", truncation=True, max_length=args.max_src_len)
    enc = {k: v.to(device) for k, v in enc.items() if k != "token_type_ids"}
    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=cfg.max_new_tokens,
            min_new_tokens=cfg.min_new_tokens,
            num_beams=cfg.num_beams,
            no_repeat_ngram_size=cfg.no_repeat_ngram_size,
            repetition_penalty=cfg.repetition_penalty,
            length_penalty=cfg.length_penalty,
            early_stopping=True,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    return normalize_space(tokenizer.decode(out[0], skip_special_tokens=True))


def generate_best(model: Any, tokenizer: Any, one_lines: List[str], device: torch.device, args: argparse.Namespace) -> Dict[str, Any]:
    lines = dedupe_keep_order(one_lines)
    if not lines:
        raise ValueError("one_lines is empty")
    model_input = build_model_input(lines)
    cfg = grounded_short_config(len(lines), args)
    raw = generate_with_config(model, tokenizer, model_input, device, cfg, args)
    text = postprocess_output(raw, len(lines))
    best = {
        "decode_config": cfg.name,
        "decode_args": asdict(cfg),
        "text": text,
        "score": candidate_score(lines, text),
        "metrics": score_output(lines, text),
    }
    return {
        "one_lines": lines,
        "model_input": model_input,
        "diary": best["text"],
        "best": best,
        "candidates": [best],
    }


def load_txt(path: Path) -> List[str]:
    return dedupe_keep_order(path.read_text(encoding="utf-8").splitlines())


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def one_lines_from_row(row: Dict[str, Any]) -> List[str]:
    if isinstance(row.get("one_lines"), list):
        return dedupe_keep_order(row["one_lines"])
    if row.get("one_line"):
        return [clean_one_line(row["one_line"])]
    if row.get("src"):
        lines = []
        for raw in str(row["src"]).splitlines():
            raw = raw.strip()
            if raw.startswith("- "):
                lines.append(raw[2:].strip())
        if lines:
            return dedupe_keep_order(lines)
    raise ValueError("JSONL row must contain one_lines, one_line, or prefixed src")


def save_single_result(result: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("[INPUT ONE_LINES]\n")
        for line in result["one_lines"]:
            f.write(f"- {line}\n")
        f.write("\n[GENERATED DIARY]\n")
        f.write(result["diary"] + "\n")
        f.write("\n[METRICS]\n")
        f.write(json.dumps(result["best"]["metrics"], ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a realistic Korean daily diary from one-line photo captions.")
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL_PATH))
    parser.add_argument("--input", type=Path, help="Text file with one one-line diary per line.")
    parser.add_argument("--one-line", action="append", default=[], help="One-line diary text. Can be passed multiple times.")
    parser.add_argument("--jsonl", type=Path, help="Batch JSONL. Each row needs one_lines, one_line, or prefixed src.")
    parser.add_argument("--output", type=Path, help="Batch output JSONL path when --jsonl is used.")
    parser.add_argument("--output-json", type=Path, default=Path(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-txt", type=Path, default=Path(DEFAULT_OUTPUT_TXT))
    parser.add_argument("--device", choices=["auto", "mps", "cuda", "cpu"], default="auto")
    parser.add_argument("--max-src-len", type=int, default=768)
    parser.add_argument("--max-new-tokens", type=int, default=300)
    parser.add_argument("--min-new-tokens", type=int, default=20)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--no-repeat-ngram-size", type=int, default=4)
    parser.add_argument("--repetition-penalty", type=float, default=1.18)
    parser.add_argument("--print-candidates", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.model.exists():
        raise FileNotFoundError(f"Model path does not exist: {args.model}")
    if not args.jsonl and not args.input and not args.one_line:
        raise SystemExit("Provide --input, --one-line, or --jsonl.")

    device = select_device(args.device)
    print(f"[DEVICE] {device}")
    print(f"[MODEL] {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    model.eval()

    if args.jsonl:
        rows = load_jsonl(args.jsonl)
        out_path = args.output or args.output_json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for idx, row in enumerate(rows):
                result = generate_best(model, tokenizer, one_lines_from_row(row), device, args)
                output_row = {
                    "id": row.get("id", f"row_{idx:04d}"),
                    "one_lines": result["one_lines"],
                    "diary": result["diary"],
                    "best": result["best"],
                }
                f.write(json.dumps(output_row, ensure_ascii=False) + "\n")
                print(f"[{idx + 1}/{len(rows)}] {output_row['id']} score={result['best']['score']}")
        print(f"[SAVE] {out_path}")
        return

    one_lines = args.one_line or load_txt(args.input)
    result = generate_best(model, tokenizer, one_lines, device, args)
    save_single_result(result, args.output_json, args.output_txt)

    print("\n[GENERATED DIARY]")
    print(result["diary"])
    print("\n[METRICS]")
    print(json.dumps(result["best"]["metrics"], ensure_ascii=False, indent=2))
    if args.print_candidates:
        print("\n[CANDIDATES]")
        for cand in result["candidates"]:
            print(json.dumps({k: v for k, v in cand.items() if k != "text"}, ensure_ascii=False))
            print(cand["text"])


if __name__ == "__main__":
    main()
