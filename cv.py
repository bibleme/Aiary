import os
import gc
import json
import math
import cv2
import torch
import torch.nn.functional as F

from PIL import Image
from ultralytics import YOLO
import clip
from deepface import DeepFace
from transformers import AutoProcessor, AutoModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

# ----------------------------
# 경로 및 설정
# ----------------------------
BASE_DIR = "./"

# 모델 가중치 및 레퍼런스 이미지 경로
YOLO_POSE_MODEL = os.path.join(BASE_DIR, "models/yolo26m-pose.pt")
YOLO_OBJ_MODEL  = os.path.join(BASE_DIR, "models/yolo26m.pt")
REF_CHILD_IMG   = os.path.join(BASE_DIR, "data/my_child_ref.jpg")

# 입력/출력 경로
INPUT_IMAGE     = os.path.join(BASE_DIR, "data/input_sample.jpg")
DB_PATH         = os.path.join(BASE_DIR, "outputs/parenting_report_final.db")

# ----------------------------
# Database (SQLAlchemy)
# ----------------------------
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()

class ImageDB(Base):
    __tablename__ = 'images'
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String, nullable=False)
    predicted_scene = Column(String)

class Person(Base):
    __tablename__ = 'persons'
    person_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String, nullable=False)
    emotion = Column(String)

class ObjectInstance(Base):
    __tablename__ = 'object_instances'
    instance_id = Column(Integer, primary_key=True, autoincrement=True)
    feature_vector = Column(String)
    base_category = Column(String, nullable=False)
    parent_assigned_name = Column(String, nullable=True)
    first_seen_image_id = Column(Integer, ForeignKey('images.image_id'))

class Appearance(Base):
    __tablename__ = 'appearances'
    appearance_id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('images.image_id'))
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    bounding_box = Column(String)

class Interaction(Base):
    __tablename__ = 'interactions'
    interaction_id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('images.image_id'))
    person_id = Column(Integer, ForeignKey('persons.person_id'))
    instance_id = Column(Integer, ForeignKey('object_instances.instance_id'))
    interaction_type = Column(String)
    proximity_score = Column(Float)

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# ----------------------------
# device & Memory
# ----------------------------
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

DEVICE = get_device()
print("DEVICE:", DEVICE)

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
# util
# ----------------------------
def get_siglip_embedding(processor, model, img_pil, box):
    width, height = img_pil.size
    x_coords = [int(box[0]), int(box[2])]
    y_coords = [int(box[1]), int(box[3])]
    
    left, right = max(0, min(x_coords)), min(width, max(x_coords))
    upper, lower = max(0, min(y_coords)), min(height, max(y_coords))
    
    # 박스 최소 크기 보장 (10px)
    if right - left < 10:
        right = min(width, left + 10)
        left = max(0, right - 10)
    if lower - upper < 10:
        lower = min(height, upper + 10)
        upper = max(0, lower - 10)
        
    cropped_img = img_pil.crop((left, upper, right, lower))
    
    inputs = processor(images=cropped_img, return_tensors="pt").to(DEVICE)
    with torch.inference_mode():
        features = model.get_image_features(**inputs)
        features = F.normalize(features, dim=-1)
        
    return features.cpu().flatten()

def calculate_cosine_similarity(vec1, vec2):
    return F.cosine_similarity(vec1.unsqueeze(0), vec2.unsqueeze(0)).item()

def calculate_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

# ----------------------------
# inference & DB Storage
# ----------------------------
def process_image(models, image_path, session):
    model_yolo_pose = models['yolo_pose']
    model_yolo_obj = models['yolo_obj']
    model_clip = models['clip']
    preprocess_clip = models['clip_preprocess']
    model_siglip = models['siglip']
    processor_siglip = models['siglip_processor']

    print(f"[{os.path.basename(image_path)}] 분석 시작...")

    # 1. CLIP: 장소 분석
    img_pil = Image.open(image_path).convert('RGB')
    img_tensor = preprocess_clip(img_pil).unsqueeze(0).to(DEVICE)
    text_inputs = clip.tokenize(["a photo of an indoor room", "a photo of an outdoor nature or street"]).to(DEVICE)
    
    with torch.inference_mode():
        image_features = model_clip.encode_image(img_tensor)
        text_features = model_clip.encode_text(text_inputs)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
        scene_result = "Indoor" if similarity[0][0].item() > 0.5 else "Outdoor"

    new_image = ImageDB(file_name=os.path.basename(image_path), predicted_scene=scene_result)
    session.add(new_image)
    session.flush()

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
        if person_crop.size > 0 and os.path.exists(REF_CHILD_IMG):
            try:
                res_verify = DeepFace.verify(img1_path=person_crop, img2_path=REF_CHILD_IMG, enforce_detection=False, silent=True)
                if res_verify['verified']:
                    is_child = True
                    res_emo = DeepFace.analyze(img_path=person_crop, actions=['emotion'], enforce_detection=False, silent=True)
                    emotion_str = res_emo[0]['dominant_emotion']
            except Exception: 
                pass 
        
        if is_child: target_child_found = True
        temp_persons.append({"p_data": p_data, "box": box, "is_child": is_child, "emotion_str": emotion_str})
        
    for tp in temp_persons:
        if tp["is_child"]: 
            role_name = "Target_Child"
        elif not target_child_found: 
            role_name, tp["emotion_str"] = "Assumed_Child", "Hidden"
        else: 
            role_name = "Adult_Helper"
                
        new_person = Person(role=role_name, emotion=tp["emotion_str"])
        session.add(new_person)
        session.flush()
        
        session.add(Appearance(image_id=new_image.image_id, entity_type='Person', entity_id=new_person.person_id, bounding_box=json.dumps(tp["box"])))
        tp["p_data"]['db_id'] = new_person.person_id 
        person_db_list.append(tp["p_data"])

    # 4. SigLIP: 사물 Re-ID 및 상호작용
    for o_data in objects_data:
        current_vector = get_siglip_embedding(processor_siglip, model_siglip, img_pil, o_data['box'])
        matched_instance_id, max_sim = None, 0.0
        
        existing_objects = session.query(ObjectInstance).filter_by(base_category=o_data['name']).all()
        for ext_obj in existing_objects:
            stored_vector = torch.tensor(json.loads(ext_obj.feature_vector))
            sim = calculate_cosine_similarity(current_vector, stored_vector)
            if sim > max_sim:
                max_sim, matched_instance_id = sim, ext_obj.instance_id
        
        if max_sim > 0.75: 
            final_instance_id = matched_instance_id
        else:
            new_obj = ObjectInstance(feature_vector=json.dumps(current_vector.tolist()), base_category=o_data['name'], first_seen_image_id=new_image.image_id)
            session.add(new_obj)
            session.flush()
            final_instance_id = new_obj.instance_id

        session.add(Appearance(image_id=new_image.image_id, entity_type='Object', entity_id=final_instance_id, bounding_box=json.dumps(o_data['box'])))

        # 상호작용 검사
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
                session.add(Interaction(image_id=new_image.image_id, person_id=p_data['db_id'], instance_id=final_instance_id, interaction_type="Hand_Holding", proximity_score=0.0))

    session.commit()
    
    return {
        "image_name": os.path.basename(image_path),
        "scene": scene_result,
        "persons": len(person_db_list),
        "objects": len(objects_data)
    }

# ----------------------------
# main
# ----------------------------
if __name__ == "__main__":
    cleanup_torch()

    print("loading vision models...")
    
    # YOLO (기본적으로 내부에서 디바이스를 관리합니다)
    model_yolo_pose = YOLO(YOLO_POSE_MODEL) if os.path.exists(YOLO_POSE_MODEL) else YOLO('yolov8n-pose.pt')
    model_yolo_obj = YOLO(YOLO_OBJ_MODEL) if os.path.exists(YOLO_OBJ_MODEL) else YOLO('yolov8n.pt')

    # CLIP
    model_clip, preprocess_clip = clip.load("ViT-B/32", device=DEVICE)
    model_clip.eval()

    # SigLIP
    processor_siglip = AutoProcessor.from_pretrained("google/siglip-base-patch16-224")
    model_siglip = AutoModel.from_pretrained("google/siglip-base-patch16-224").to(DEVICE)
    model_siglip.eval()

    models_dict = {
        'yolo_pose': model_yolo_pose,
        'yolo_obj': model_yolo_obj,
        'clip': model_clip,
        'clip_preprocess': preprocess_clip,
        'siglip': model_siglip,
        'siglip_processor': processor_siglip
    }

    print("processing image...")
    session = SessionLocal()
    
    try:
        if os.path.exists(INPUT_IMAGE):
            result = process_image(models_dict, INPUT_IMAGE, session)
            print("\n[RESULT]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"\n데이터가 {DB_PATH} 에 성공적으로 저장되었습니다.")
        else:
            print(f"이미지 파일을 찾을 수 없습니다: {INPUT_IMAGE}")
    except Exception as e:
        session.rollback()
        print(f"오류 발생: {e}")
    finally:
        session.close()

    # 메모리 해제
    print("cleaning up resources...")
    del models_dict
    del model_yolo_pose, model_yolo_obj, model_clip, model_siglip
    cleanup_torch()
