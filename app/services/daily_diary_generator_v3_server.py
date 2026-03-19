import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.config import settings

# ----------------------------
# 글로벌 캐시 (중요🔥)
# ----------------------------
_tokenizer = None
_model = None
_device = None


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return _tokenizer, _model, _device

    print("🔵 [v3] loading model...")

    _device = get_device()

    _tokenizer = AutoTokenizer.from_pretrained(
        settings.DAILY_DIARY_MODEL_DIR,
        use_fast=True
    )

    _model = AutoModelForSeq2SeqLM.from_pretrained(
        settings.DAILY_DIARY_MODEL_DIR
    ).to(_device)

    _model.eval()

    print("🟢 [v3] model loaded")

    return _tokenizer, _model, _device


def generate_diary(model, tok, device, one_lines, max_input_length=512):
    src = "\n".join([x.strip() for x in one_lines if x.strip()])

    enc = tok(
        src,
        return_tensors="pt",
        truncation=True,
        max_length=max_input_length
    )

    enc = {k: v.to(device) for k, v in enc.items()}
    enc.pop("token_type_ids", None)

    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=180,
            num_beams=2,
            do_sample=False,
            no_repeat_ngram_size=4,
            repetition_penalty=1.1,
            length_penalty=0.85,
            eos_token_id=tok.eos_token_id,
            pad_token_id=tok.pad_token_id
        )

    result = tok.decode(out[0], skip_special_tokens=True)
    return result.strip()


async def generate_daily_diary_v3(one_line_diaries: list[str]) -> dict:
    tok, model, device = load_model()

    diary = generate_diary(model, tok, device, one_line_diaries)

    return {
        "generated_diary": diary,
        "model_version": "v3"
    }
