
# 🤖 Aiary Model Collection

이 폴더는 **모델 학습 노트북 / 데이터셋 / 모델 다운로드 안내**를 담고 있습니다.
학습된 모델은 용량이 커서 GitHub에 직접 포함할 수 없습니다.

---

## 📦 Google Drive 모델 다운로드 링크

👉 [https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl](https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl)

---

## 📂 배치 위치

다운로드 후 다음 경로에 복사:

```
backend/models/day_diary_from_summary_v2/
```

모델 파일 목록 예시:

* config.json
* generation_config.json
* model.safetensors
* tokenizer.json
* tokenizer_config.json
* special_tokens_map.json

---

## 📘 포함된 Jupyter 노트북

```
하루일기_inference.ipynb        # 하루 줄글 일기 추론
KoBART_synthetic_v2.ipynb       # 팀 모델 담당의 학습 코드
```

---

## ▶ 빠른 추론 예시

```python
from backend.app.services.daily_diary_generator import generate_daily_diary

result = await generate_daily_diary([
    "오늘 아기가 웃으며 놀았다.",
    "바깥에서 신나게 뛰어놀았다."
])

print(result["generated_diary"])
```

---
