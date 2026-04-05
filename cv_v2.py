import os
import gc
import json
import math
import glob
import re
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
# 1. 경로 및 설정 (Constants)
# ----------------------------
BASE_DIR = "./"

# 모델 가중치 경로
YOLO_POSE_MODEL = os.path.join(BASE_DIR, "models/yolo26m-pose.pt")
YOLO_OBJ_MODEL  = os.path.join(BASE_DIR, "models/yolo26m.pt")

# 기준 사진 폴더 및 DB 경로
REF_DIR = os.path.join(BASE_DIR, "child_refs")
DB_PATH = os.path.join(BASE_DIR, "parenting_report_final.db")

# CLIP 프롬프트 매핑 딕셔너리
PROMPT_TO_TAG = {
    "a photo of a residential home interior or living room": "Routine_Indoor",
    "a photo of a house with play mats and toys": "Routine_Indoor",
    "a photo of a daycare center or kindergarten classroom": "Routine_Indoor",
    "a photo of a kids cafe or indoor children's playground": "Routine_Indoor",
    "a photo of an aquarium or museum interior": "Special_Outing",
    "a photo of an exhibition or art gallery": "Special_Outing",
    "a photo of an indoor amusement park or large shopping mall": "Special_Outing",
    "a photo of a fancy restaurant, cafe, or hotel interior": "Special_Outing",
    "a photo of a nature park, forest, or outdoor playground": "Outdoor_Outing",
    "a photo of the beach or sea": "Outdoor_Outing",
    "a photo of a zoo or botanical garden": "Outdoor_Outing",
    "a photo of a city street or outdoor building exterior": "Outdoor_Outing",
    "an extreme close-up photo of an object, food, or toy": "No_Scene",
    "a blurry photo or texture without a visible background": "No_Scene",
    "a photo of a plain floor, wall, or ceiling": "No_Scene"
}

# ----------------------------
# 2. Database (SQLAlchemy)
# ----------------------------
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()

class ImageDB(Base):
    __tablename__ = 'images'
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String, nullable=False)
    year_month = Column(String, nullable=False) 
    predicted_tag = Column(String)
    scene_vector = Column(String)

class Person(Base):
    __tablename__ = 'persons'
    person_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String, nullable=False)
    emotion = Column(String)
    emotion_score = Column(Float)

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
# 3. Device & Memory
# ----------------------------
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

DEVICE = get_device()

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
# 4. Utilities
# ----------------------------
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

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
        features = model.get_image_features(**inputs)
        features = F.normalize(features, dim=-1)
        
    return features.cpu().flatten()

def calculate_cosine_similarity(vec1, vec2):
    return F.cosine_similarity(vec1.unsqueeze(0), vec2.unsqueeze(0)).item()

def calculate_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

# ----------------------------
# 5. Inference & DB Storage
# ----------------------------
def process_image(models, image_path, session, best_faces_per_month):
    model_yolo_pose = models['yolo_pose']
    model_yolo_obj = models['yolo_obj']
    model_clip = models['clip']
    preprocess_clip = models['clip_preprocess']
    model_siglip = models['siglip']
    processor_siglip = models['siglip_processor']
    
    global_text_features_norm = models['global_text_features_norm']
    all_prompts = models['all_prompts']

    folder_name = os.path.dirname(image_path)
    year_month = os.path.basename(folder_name) if folder_name else "root"
    
    if year_month not in best_faces_per_month:
        best_faces_per_month[year_month] = {"min_distance": 999.0, "face_crop": None}

    # 1. CLIP
    img_pil = Image.open(image_path).convert('RGB')
    img_tensor = preprocess_clip(img_pil).unsqueeze(0).to(DEVICE)
    
    with torch.inference_mode():
        image_features = model_clip.encode_image(img_tensor)
        image_features_norm = F.normalize(image_features, dim=-1)
        
        similarities = (image_features_norm @ global_text_features_norm.T).squeeze(0)
        predicted_tag = PROMPT_TO_TAG[all_prompts[similarities.argmax().item()]]
        scene_vector = image_features_norm.cpu().flatten().tolist()

    new_image = ImageDB(file_name=image_path, year_month=year_month, predicted_tag=predicted_tag, scene_vector=json.dumps(scene_vector))
    session.add(new_image)
    session.flush()

    img_cv2 = cv2.imread(image_path)
    persons_data, objects_data = [], []

    # 2-A. YOLO Pose
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

    # 2-B. YOLO Object
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

    # 3. DeepFace
    person_db_list = []
    target_child_found = False
    temp_persons = []
    
    ref_images = glob.glob(f"{REF_DIR}/*.jpg") + glob.glob(f"{REF_DIR}/*.png")

    for p_data in persons_data:
        box = p_data['box']
        x1, y1 = max(0, int(box[0])), max(0, int(box[1]))
        x2, y2 = min(img_cv2.shape[1], int(box[2])), min(img_cv2.shape[0], int(box[3]))
        person_crop = img_cv2[y1:y2, x1:x2]
        
        is_child, emotion_str, emotion_score = False, "Unknown", 0.0
        best_dist_for_this_face = 999.0
        
        if person_crop.size > 0 and len(ref_images) > 0:
            try:
                for ref_img in ref_images:
                    res_verify = DeepFace.verify(img1_path=person_crop, img2_path=ref_img, enforce_detection=False, silent=True)
                    if res_verify['verified']:
                        is_child = True
                        
                    current_dist = res_verify['distance']
                    if current_dist < best_dist_for_this_face:
                        best_dist_for_this_face = current_dist

                if is_child:
                    res_emo = DeepFace.analyze(img_path=person_crop, actions=['emotion'], enforce_detection=False, silent=True)
                    emotion_str = res_emo[0]['dominant_emotion']
                    emotion_score = res_emo[0]['emotion'][emotion_str]
                    
                    if best_dist_for_this_face < 0.25 and best_dist_for_this_face < best_faces_per_month[year_month]["min_distance"]:
                        best_faces_per_month[year_month]["min_distance"] = best_dist_for_this_face
                        best_faces_per_month[year_month]["face_crop"] = person_crop
                        
            except Exception: 
                pass 
        
        if is_child: target_child_found = True
        temp_persons.append({"p_data": p_data, "box": box, "is_child": is_child, "emotion_str": emotion_str, "emotion_score": emotion_score})
        
    for tp in temp_persons:
        role_name = "Target_Child" if tp["is_child"] else ("Assumed_Child" if not target_child_found else "Adult_Helper")
        if role_name == "Assumed_Child": tp["emotion_str"] = "Hidden" 
                
        new_person = Person(role=role_name, emotion=tp["emotion_str"], emotion_score=tp["emotion_score"])
        session.add(new_person)
        session.flush()
        
        session.add(Appearance(image_id=new_image.image_id, entity_type='Person', entity_id=new_person.person_id, bounding_box=json.dumps(tp["box"])))
        tp["p_data"]['db_id'] = new_person.person_id 
        person_db_list.append(tp["p_data"])

    # 4. SigLIP & Interaction
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
    return True

# ----------------------------
# 6. Main
# ----------------------------
if __name__ == "__main__":
    cleanup_torch()

    if not os.path.exists(REF_DIR):
        os.makedirs(REF_DIR)

    model_yolo_pose = YOLO(YOLO_POSE_MODEL) if os.path.exists(YOLO_POSE_MODEL) else YOLO('yolov8n-pose.pt')
    model_yolo_obj = YOLO(YOLO_OBJ_MODEL) if os.path.exists(YOLO_OBJ_MODEL) else YOLO('yolov8n.pt')

    model_clip, preprocess_clip = clip.load("ViT-B/32", device=DEVICE)
    model_clip.eval()

    all_prompts = list(PROMPT_TO_TAG.keys())
    text_inputs = clip.tokenize(all_prompts).to(DEVICE)
    with torch.inference_mode():
        global_text_features = model_clip.encode_text(text_inputs)
        global_text_features_norm = F.normalize(global_text_features, dim=-1)

    processor_siglip = AutoProcessor.from_pretrained("google/siglip-base-patch16-224")
    model_siglip = AutoModel.from_pretrained("google/siglip-base-patch16-224").to(DEVICE)
    model_siglip.eval()

    models_dict = {
        'yolo_pose': model_yolo_pose,
        'yolo_obj': model_yolo_obj,
        'clip': model_clip,
        'clip_preprocess': preprocess_clip,
        'siglip': model_siglip,
        'siglip_processor': processor_siglip,
        'global_text_features_norm': global_text_features_norm,
        'all_prompts': all_prompts
    }

    all_files = []
    for ext in ['**/*.jpg', '**/*.jpeg', '**/*.png']:
        all_files.extend(glob.glob(ext, recursive=True))
        
    all_files = [f.replace('\\', '/') for f in all_files]
    image_files = sorted(all_files, key=natural_sort_key)
    image_files = [f for f in image_files if REF_DIR not in f]
    
    best_faces_per_month = {}
    session = SessionLocal()
    
    try:
        if len(image_files) > 0:
            for filepath in image_files:
                process_image(models_dict, filepath, session, best_faces_per_month)
                
            for ym, data in best_faces_per_month.items():
                if data["face_crop"] is not None:
                    save_path = os.path.join(REF_DIR, f"ref_{ym}.jpg")
                    cv2.imwrite(save_path, data["face_crop"])
                    
    except Exception as e:
        session.rollback()
        print(f"Error occurred: {e}")
    finally:
        session.close()

    del models_dict
    del model_yolo_pose, model_yolo_obj, model_clip, model_siglip
    cleanup_torch()
