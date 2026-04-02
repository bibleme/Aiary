# app/services/vision_analyzer.py
import os
import gc
import json
import cv2
import torch
import torch.nn.functional as F
from PIL import Image

# ML Models
from ultralytics import YOLO
import clip
from deepface import DeepFace
from transformers import AutoProcessor, AutoModel

# SQLAlchemy (비동기)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 새로 만든 DB 모델들 불러오기
from app.db.model import (
    VisionImage, 
    VisionPerson, 
    VisionObjectInstance, 
    VisionAppearance, 
    VisionInteraction
)

# ----------------------------
# 글로벌 캐시 (모델 재사용)
# ----------------------------
_models_dict = {}
_is_models_loaded = False
DEVICE = None

# 경로 설정 (필요시 app.config.settings 로 이동 권장)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
YOLO_POSE_MODEL = os.path.join(BASE_DIR, "models/yolo26m-pose.pt")
YOLO_OBJ_MODEL  = os.path.join(BASE_DIR, "models/yolo26m.pt")
REF_CHILD_IMG   = os.path.join(BASE_DIR, "data/my_child_ref.jpg")

# ----------------------------
# Device & Memory
# ----------------------------
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def cleanup_torch():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        try:
            torch.mps.empty_cache()
        except Exception:
            pass

# ----------------------------
# 모델 로드 (서버 켤 때 1번만 실행)
# ----------------------------
def load_vision_models():
    global _models_dict, _is_models_loaded, DEVICE

    if _is_models_loaded:
        return _models_dict

    cleanup_torch()
    DEVICE = get_device()
    print(f"🟢 [Vision AI] Loading models onto {DEVICE}...")

    model_yolo_pose = YOLO(YOLO_POSE_MODEL) if os.path.exists(YOLO_POSE_MODEL) else YOLO('yolov8n-pose.pt')
    model_yolo_obj = YOLO(YOLO_OBJ_MODEL) if os.path.exists(YOLO_OBJ_MODEL) else YOLO('yolov8n.pt')

    model_clip, preprocess_clip = clip.load("ViT-B/32", device=DEVICE)
    model_clip.eval()

    processor_siglip = AutoProcessor.from_pretrained("google/siglip-base-patch16-224")
    model_siglip = AutoModel.from_pretrained("google/siglip-base-patch16-224").to(DEVICE)
    model_siglip.eval()

    _models_dict = {
        'yolo_pose': model_yolo_pose,
        'yolo_obj': model_yolo_obj,
        'clip': model_clip,
        'clip_preprocess': preprocess_clip,
        'siglip': model_siglip,
        'siglip_processor': processor_siglip
    }
    _is_models_loaded = True
    print("🟢 [Vision AI] Models loaded successfully!")
    return _models_dict

# ----------------------------
# Util
# ----------------------------
def get_siglip_embedding(processor, model, img_pil, box):
    width, height = img_pil.size
    x_coords = [int(box[0]), int(box[2])]
    y_coords = [int(box[1]), int(box[3])]
    
    left, right = max(0, min(x_coords)), min(width, max(x_coords))
    upper, lower = max(0, min(y_coords)), min(height, max(y_coords))
    
    if right - left < 10:
        right = min(width, left + 10)
        left = max(0, right - 10)
    if lower - upper < 10:
        lower = min(height, upper + 10)
        upper = max(0, lower - 10)
        
    cropped_img = img_pil.crop((left, upper, right, lower))
    
    inputs = processor(images=cropped_img, return_tensors="pt").to(DEVICE)
    with torch.inference_mode():
        # 1. 텍스트 파트는 깨우지 말고, '이미지 특징'만 뽑아내라고 정확히 명령!
        outputs = model.get_image_features(**inputs)
        
        # 2. 허깅페이스 버전에 따라 상자에 담겨올 수도, 그냥 올 수도 있으므로 철저하게 대비 (안전한 상자깡)
        if hasattr(outputs, 'pooler_output'):
            embeds = outputs.pooler_output
        elif hasattr(outputs, 'image_embeds'):
            embeds = outputs.image_embeds
        elif isinstance(outputs, tuple) or isinstance(outputs, list):
            embeds = outputs[0]
        else:
            embeds = outputs  # 이미 알맹이(Tensor) 상태로 나온 경우
            
        # 3. 안전하게 꺼낸 알맹이에 대고 수학 계산(정규화) 수행
        features = F.normalize(embeds, dim=-1)
        
    return features.cpu().flatten()

def calculate_cosine_similarity(vec1, vec2):
    return F.cosine_similarity(vec1.unsqueeze(0), vec2.unsqueeze(0)).item()

def calculate_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

# ----------------------------
# Inference & Async DB Storage
# ----------------------------
async def process_vision_analysis(diary_id: int, image_path: str, db: AsyncSession):
    """
    FastAPI 라우터에서 호출할 공식 비전 분석 함수.
    """
    models = load_vision_models()
    
    # 모델 꺼내기
    model_yolo_pose = models['yolo_pose']
    model_yolo_obj = models['yolo_obj']
    model_clip = models['clip']
    preprocess_clip = models['clip_preprocess']
    model_siglip = models['siglip']
    processor_siglip = models['siglip_processor']

    print(f"[{os.path.basename(image_path)}] 비전 분석 시작...")

    # 1. CLIP: 장소 분석
    img_pil = Image.open(image_path).convert('RGB')
    img_tensor = preprocess_clip(img_pil).unsqueeze(0).to(DEVICE)
    text_inputs = clip.tokenize(["a photo of an indoor room", "a photo of an outdoor nature or street"]).to(DEVICE)
    
    with torch.inference_mode():
        image_features = model_clip.encode_image(img_tensor)
        text_features = model_clip.encode_text(text_inputs)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
        scene_result = "Indoor" if similarity[0][0].item() > 0.5 else "Outdoor"

    # [DB] Image 생성
    new_image = VisionImage(
        diary_id=diary_id, 
        file_name=os.path.basename(image_path), 
        predicted_scene=scene_result
    )
    db.add(new_image)
    await db.flush() # ID를 발급받기 위해 비동기 flush 실행

    img_cv2 = cv2.imread(image_path)
    persons_data, objects_data = [], []

    # 2. YOLO: 인물/Pose 및 사물 탐지
    res_pose = model_yolo_pose.predict(source=image_path, conf=0.50, imgsz=1024, verbose=False)
    for r in res_pose:
        if r.keypoints is not None and r.boxes is not None:
            for box, kpts in zip(r.boxes, r.keypoints):
                if int(box.cls[0]) == 0:
                    coords = box.xyxy[0].tolist()
                    keypoints_data = kpts.xy[0].tolist()
                    left_wrist = keypoints_data[9] if len(keypoints_data) > 9 else None
                    right_wrist = keypoints_data[10] if len(keypoints_data) > 10 else None
                    persons_data.append({"box": coords, "left_wrist": left_wrist, "right_wrist": right_wrist})

    res_obj = model_yolo_obj.predict(source=image_path, conf=0.25, imgsz=1024, verbose=False)
    for r in res_obj:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if cls_id != 0:
                objects_data.append({
                    "name": model_yolo_obj.names[cls_id], 
                    "box": box.xyxy[0].tolist(), 
                    "center": calculate_center(box.xyxy[0].tolist())
                })

    # 3. DeepFace: 인물 식별
    person_db_list = []
    target_child_found = False
    temp_persons = []

    for p_data in persons_data:
        box = p_data['box']
        x1, y1 = max(0, int(box[0])), max(0, int(box[1]))
        x2, y2 = min(img_cv2.shape[1], int(box[2])), min(img_cv2.shape[0], int(box[3]))
        person_crop = img_cv2[y1:y2, x1:x2]
        
        is_child, emotion_str = False, "Unknown"
        
        if person_crop.size > 0:
            # 1. 누구든 일단 감정부터 읽어봅니다.
            try:
                res_emo = DeepFace.analyze(img_path=person_crop, actions=['emotion'], enforce_detection=False, silent=True)
                emotion_str = res_emo[0]['dominant_emotion']
            except Exception as e:
                # 🚨 여기서 에러가 찍히면 얼굴이 너무 작거나 가중치 파일이 없는 겁니다.
                print(f"❌ Emotion Analysis Failed: {e}")
                emotion_str = "Hidden"

            # 2. 우리 아이인지 확인합니다.
            if os.path.exists(REF_CHILD_IMG):
                try:
                    res_verify = DeepFace.verify(img1_path=person_crop, img2_path=REF_CHILD_IMG, enforce_detection=False, silent=True)
                    if res_verify['verified']:
                        is_child = True
                except Exception as e:
                    print(f"⚠️ Verification Failed: {e}")
        
        if is_child: target_child_found = True
        temp_persons.append({"p_data": p_data, "box": box, "is_child": is_child, "emotion_str": emotion_str})
        
    for tp in temp_persons:
        # 3. 역할 배정 로직 (감정을 강제로 덮어쓰지 않도록 수정)
        if tp["is_child"]: 
            role_name = "Target_Child"
        elif not target_child_found: 
            role_name = "Assumed_Child" 
        else: 
            role_name = "Adult_Helper"
            tp["emotion_str"] = "Neutral" # 어른은 통계 방지용
                
        # [DB] Person & Appearance 저장
        new_person = VisionPerson(role=role_name, emotion=tp["emotion_str"])
        db.add(new_person)
        await db.flush()
        
        db.add(VisionAppearance(
            image_id=new_image.id, 
            entity_type='Person', 
            entity_id=new_person.id, 
            bounding_box=json.dumps(tp["box"])
        ))
        tp["p_data"]['db_id'] = new_person.id 
        person_db_list.append(tp["p_data"])

    # 4. SigLIP: 사물 Re-ID 및 상호작용
    for o_data in objects_data:
        current_vector = get_siglip_embedding(processor_siglip, model_siglip, img_pil, o_data['box'])
        matched_instance_id, max_sim = None, 0.0
        
        # [DB 비동기 조회] 같은 카테고리의 기존 사물 찾기
        result = await db.execute(select(VisionObjectInstance).filter_by(base_category=o_data['name']))
        existing_objects = result.scalars().all()
        
        for ext_obj in existing_objects:
            stored_vector = torch.tensor(json.loads(ext_obj.feature_vector))
            sim = calculate_cosine_similarity(current_vector, stored_vector)
            if sim > max_sim:
                max_sim, matched_instance_id = sim, ext_obj.id # 주의: model.py에서 id로 변경됨
        
        if max_sim > 0.75: 
            final_instance_id = matched_instance_id
        else:
            # [DB] 새 Object Instance 저장
            new_obj = VisionObjectInstance(
                feature_vector=json.dumps(current_vector.tolist()), 
                base_category=o_data['name'], 
                first_seen_image_id=new_image.id
            )
            db.add(new_obj)
            await db.flush()
            final_instance_id = new_obj.id

        # [DB] 사물 위치(Appearance) 저장
        db.add(VisionAppearance(
            image_id=new_image.id, 
            entity_type='Object', 
            entity_id=final_instance_id, 
            bounding_box=json.dumps(o_data['box'])
        ))

        # 5. 상호작용(Interaction) 검사
        for p_data in person_db_list:
            is_holding = False
            o_box = o_data['box']
            pad = 30 
            x_min, y_min = o_box[0] - pad, o_box[1] - pad
            x_max, y_max = o_box[2] + pad, o_box[3] + pad

            for wrist in ['left_wrist', 'right_wrist']:
                if p_data[wrist] and p_data[wrist][0] > 0:
                    wx, wy = p_data[wrist]
                    if x_min <= wx <= x_max and y_min <= wy <= y_max:
                        is_holding = True
            
            if is_holding: 
                # [DB] 상호작용 저장
                db.add(VisionInteraction(
                    image_id=new_image.id, 
                    person_id=p_data['db_id'], 
                    instance_id=final_instance_id, 
                    interaction_type="Hand_Holding", 
                    proximity_score=0.0
                ))

    # 에러가 나지 않았다면 모든 DB 변경사항을 확정(commit)
    await db.commit()
    
    return {
        "diary_id": diary_id,
        "image_name": os.path.basename(image_path),
        "scene": scene_result,
        "persons": len(person_db_list),
        "objects": len(objects_data)
    }