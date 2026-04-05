import os
import json
import sqlite3
import pandas as pd
import torch
import torch.nn.functional as F

# ----------------------------
# 경로 및 설정
# ----------------------------
BASE_DIR = "./"
# 입력 DB 경로 (AI 비전 분석 파이프라인이 저장한 DB)
DB_PATH = os.path.join(BASE_DIR, "parenting_report_final.db")

EMOTION_MAPPING = {
    'happy': '기쁨/행복',
    'surprise': '놀람/호기심',
    'neutral': '평온/집중',
    'sad': '슬픔/시무룩',
    'angry': '분노/화남',
    'fear': '두려움/공포',
    'disgust': '불쾌/찡그림'
}

# ----------------------------
# 유틸리티: 장소 클러스터링 로직
# ----------------------------
def cluster_places_strictly(df_scene, threshold=0.88):
    df_scene = df_scene.reset_index(drop=True)
    if len(df_scene) == 0: return []
    
    clusters = []
    for idx, row in df_scene.iterrows():
        try:
            vec = torch.tensor(json.loads(row['scene_vector']))
        except:
            continue
            
        matched_idx, max_sim = -1, 0.0
        for i, cluster in enumerate(clusters):
            center_vec = cluster['center_vec']
            sim = F.cosine_similarity(vec.unsqueeze(0), center_vec.unsqueeze(0)).item()
            
            # 연속 사진(인덱스 차이 3 이하)일 경우 기준치 완화
            adj_threshold = 0.85 if abs(idx - cluster['last_idx']) <= 3 else threshold
            
            if sim >= adj_threshold and sim > max_sim:
                max_sim, matched_idx = sim, i
                
        if matched_idx != -1:
            clusters[matched_idx]['photos'].append(row['file_name'])
            clusters[matched_idx]['last_idx'] = idx
        else:
            clusters.append({
                'center_vec': vec, 
                'last_idx': idx, 
                'photos': [row['file_name']]
            })
            
    for c in clusters:
        c['photo_count'] = len(c['photos'])
    return clusters

# ----------------------------
# 월간 리포트 알고리즘
# ----------------------------
def generate_monthly_report(db_path: str, target_month: str = None) -> dict:
    """
    월간 리포트 데이터를 생성하여 프론트엔드(Kotlin)에 전달할 JSON 틀을 반환합니다.
    """
    report_data = {
        "report_month": None,
        "favorite_objects": [],
        "emotions_summary": [],
        "highlight_places": []
    }

    if not os.path.exists(db_path):
        return report_data

    conn = sqlite3.connect(db_path)

    try:
        # 1. 데이터 로드
        df_obj = pd.read_sql_query("""
            SELECT i.instance_id, o.first_seen_image_id, o.base_category, img.image_id, img.file_name, img.year_month, a.bounding_box
            FROM interactions i
            JOIN persons p ON i.person_id = p.person_id
            JOIN object_instances o ON i.instance_id = o.instance_id
            JOIN images img ON i.image_id = img.image_id
            JOIN appearances a ON a.image_id = img.image_id AND a.entity_id = o.instance_id AND a.entity_type = 'Object'
            WHERE p.role IN ('Target_Child', 'Assumed_Child') AND i.interaction_type = 'Hand_Holding'
        """, conn)
        
        df_emo = pd.read_sql_query("""
            SELECT img.image_id, img.file_name, img.year_month, p.emotion, p.emotion_score, a.bounding_box
            FROM persons p
            JOIN appearances a ON p.person_id = a.entity_id AND a.entity_type = 'Person'
            JOIN images img ON a.image_id = img.image_id
            WHERE p.role = 'Target_Child' AND p.emotion != 'Unknown'
        """, conn)
        
        df_scene = pd.read_sql_query("""
            SELECT image_id, file_name, year_month, predicted_tag, scene_vector
            FROM images
            WHERE scene_vector IS NOT NULL
            ORDER BY image_id ASC
        """, conn)

        if df_scene.empty: return report_data

        # 💡 대상 월 설정 (지정되지 않으면 가장 최신 달)
        if target_month is None:
            target_month = df_scene['year_month'].max()
        report_data["report_month"] = target_month

        curr_obj = df_obj[df_obj['year_month'] == target_month]
        curr_emo = df_emo[df_emo['year_month'] == target_month]
        curr_scene = df_scene[df_scene['year_month'] == target_month]
        past_scene = df_scene[df_scene['year_month'] < target_month]

        # 2. 애착 물건 (Rank & IsNew)
        if not curr_obj.empty:
            unique_objs = curr_obj.drop_duplicates(subset=['instance_id', 'file_name'])
            top_objs = unique_objs.groupby('instance_id').size().reset_index(name='count').sort_values('count', ascending=False)
            first_seen_map = dict(zip(df_scene['image_id'], df_scene['year_month']))
            
            for rank, (idx, row) in enumerate(top_objs.head(3).iterrows(), start=1):
                inst_data = unique_objs[unique_objs['instance_id'] == row['instance_id']]
                is_new = (first_seen_map.get(inst_data.iloc[0]['first_seen_image_id']) == target_month)
                
                report_data["favorite_objects"].append({
                    "rank": rank,
                    "category": inst_data.iloc[0]['base_category'],
                    "is_new": bool(is_new),
                    "photo_count": int(row['count']),
                    "appearances": [{"file_name": r['file_name'], "bbox": json.loads(r['bounding_box'])} for _, r in inst_data.iterrows()]
                })

        # 3. 감정 분석 (전체 비율 & 신뢰도 기반 베스트 컷)
        if not curr_emo.empty:
            total_emo_cnt = len(curr_emo)
            emo_counts = curr_emo['emotion'].value_counts()
            
            for emo_en, emo_kr in EMOTION_MAPPING.items():
                if emo_en in emo_counts:
                    best_row = curr_emo[curr_emo['emotion'] == emo_en].sort_values(by='emotion_score', ascending=False).iloc[0]
                    report_data["emotions_summary"].append({
                        "emotion_en": emo_en,
                        "emotion_kr": emo_kr,
                        "ratio": round((emo_counts[emo_en] / total_emo_cnt) * 100, 1),
                        "best_cut": {
                            "file_name": best_row['file_name'],
                            "confidence": round(best_row['emotion_score'], 1),
                            "bbox": json.loads(best_row['bounding_box'])
                        }
                    })

        # 4. 나들이 하이라이트 (Clustering & IsNew)
        if not curr_scene.empty:
            curr_outing = curr_scene[~curr_scene['predicted_tag'].isin(["Routine_Indoor", "No_Scene"])]
            if not curr_outing.empty:
                clusters = cluster_places_strictly(curr_outing, threshold=0.88)
                
                # 과거 장소 벡터 텐서화
                past_vectors = [torch.tensor(json.loads(r['scene_vector'])) for _, r in past_scene.iterrows()]

                for c in clusters:
                    c['is_new'] = True
                    for pv in past_vectors:
                        if F.cosine_similarity(c['center_vec'].unsqueeze(0), pv.unsqueeze(0)).item() >= 0.88:
                            c['is_new'] = False
                            break
                
                clusters.sort(key=lambda x: x['photo_count'], reverse=True)
                for rank, c in enumerate(clusters[:3], start=1):
                    report_data["highlight_places"].append({
                        "rank": rank,
                        "is_new": bool(c['is_new']),
                        "photo_count": int(c['photo_count']),
                        "photos": c['photos']
                    })

    except Exception as e:
        pass # Git 코드 스타일 유지 (필요 시 에러 로깅)
    finally:
        conn.close()

    return report_data

# ----------------------------
# main
# ----------------------------
if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        # 최신 달 기준 리포트 생성 예시
        result = generate_monthly_report(DB_PATH)
        # JSON 결과 확인 (필요 시 주석 해제)
        # print(json.dumps(result, indent=2, ensure_ascii=False))
