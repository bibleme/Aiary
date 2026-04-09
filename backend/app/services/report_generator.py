import json
import pandas as pd
import torch
import torch.nn.functional as F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# ----------------------------
# 매핑 설정
# ----------------------------
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
# 월간 리포트 알고리즘 (비동기 처리)
# ----------------------------
async def generate_monthly_report(db: AsyncSession, user_id: int, target_month: str) -> dict:
    """
    FastAPI 비동기 세션을 받아 특정 유저(user_id)의 월간 리포트를 생성합니다.
    """
    report_data = {
        "report_month": target_month,
        "favorite_objects": [],
        "emotions_summary": [],
        "highlight_places": []
    }

    try:
        # 1. 비동기 쿼리 작성 (JOIN diaries를 통해 user_id 필터링 적용)
        # 💡 주의: 테이블 이름(vision_interactions 등)은 실제 DB 모델의 __tablename__과 일치해야 합니다.
        
        query_obj = text("""
            SELECT i.instance_id, o.first_seen_image_id, o.base_category, img.id as image_id, img.file_name, 
                   to_char(d.diary_date, 'YYYY-MM') AS year_month, a.bounding_box
            FROM vision_interactions i
            JOIN vision_persons p ON i.person_id = p.id
            JOIN vision_object_instances o ON i.instance_id = o.id
            JOIN vision_images img ON i.image_id = img.id
            JOIN one_line_diaries d ON img.diary_id = d.id
            JOIN vision_appearances a ON a.image_id = img.id AND a.entity_id = o.id AND a.entity_type = 'Object'
            WHERE p.role IN ('Target_Child', 'Assumed_Child') AND i.interaction_type = 'Hand_Holding'
              AND d.user_id = :user_id
        """)
        
        query_emo = text("""
            SELECT img.id as image_id, img.file_name, to_char(d.diary_date, 'YYYY-MM') AS year_month, 
                   p.emotion, p.emotion_score, a.bounding_box
            FROM vision_persons p
            JOIN vision_appearances a ON p.id = a.entity_id AND a.entity_type = 'Person'
            JOIN vision_images img ON a.image_id = img.id
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE p.role = 'Target_Child' AND p.emotion != 'Unknown'
              AND d.user_id = :user_id
        """)
        
        query_scene = text("""
            SELECT img.id as image_id, img.file_name, to_char(d.diary_date, 'YYYY-MM') AS year_month, 
                   img.predicted_scene AS predicted_tag, img.scene_vector
            FROM vision_images img
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE img.scene_vector IS NOT NULL
              AND d.user_id = :user_id
            ORDER BY img.id ASC
        """)

        # 2. 비동기로 쿼리 실행
        params = {"user_id": user_id}
        res_obj = await db.execute(query_obj, params)
        res_emo = await db.execute(query_emo, params)
        res_scene = await db.execute(query_scene, params)

        # 3. Pandas DataFrame으로 변환
        df_obj = pd.DataFrame(res_obj.mappings().all())
        df_emo = pd.DataFrame(res_emo.mappings().all())
        df_scene = pd.DataFrame(res_scene.mappings().all())

        if df_scene.empty: 
            return report_data

        if target_month is None:
            target_month = df_scene['year_month'].max()
        report_data["report_month"] = target_month

        # 데이터 프레임이 비어있지 않을 때만 필터링
        curr_obj = df_obj[df_obj['year_month'] == target_month] if not df_obj.empty else pd.DataFrame()
        curr_emo = df_emo[df_emo['year_month'] == target_month] if not df_emo.empty else pd.DataFrame()
        curr_scene = df_scene[df_scene['year_month'] == target_month] if not df_scene.empty else pd.DataFrame()
        past_scene = df_scene[df_scene['year_month'] < target_month] if not df_scene.empty else pd.DataFrame()

        # ----------------------------------------------------
        # 4. 아래부터는 기존에 작성하신 데이터 가공 알고리즘을 그대로 적용
        # ----------------------------------------------------
        
        # [애착 물건]
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

        # [감정 분석]
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

        # [나들이 하이라이트]
        if not curr_scene.empty:
            curr_outing = curr_scene[~curr_scene['predicted_tag'].isin(["Routine_Indoor", "No_Scene"])]
            if not curr_outing.empty:
                clusters = cluster_places_strictly(curr_outing, threshold=0.88)
                
                past_vectors = []
                if not past_scene.empty:
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

        return report_data

    except Exception as e:
        raise Exception(f"월간 리포트 생성 중 오류 발생: {str(e)}")