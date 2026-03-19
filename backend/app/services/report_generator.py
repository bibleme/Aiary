# app/services/report_generator.py
import json
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_monthly_report(db: AsyncSession, user_id: int, target_month: str) -> dict:
    """
    월간 리포트 데이터를 생성하여 프론트엔드에 전달할 JSON 틀을 반환합니다.
    :param db: 비동기 DB 세션
    :param user_id: 조회할 유저의 ID
    :param target_month: 조회할 연월 (예: "2026-03")
    """
    report_data = {
        "favorite_objects": [],
        "top_emotion": None,
        "primary_scene": None,
        "social_status": None
    }

    try:
        # 1. 애착 물건 (Diary 테이블과 조인하여 유저/날짜 필터링)
        query_obj = text("""
            SELECT o.id as instance_id, o.base_category, img.file_name, a.bounding_box
            FROM vision_interactions i
            JOIN vision_persons p ON i.person_id = p.id
            JOIN vision_object_instances o ON i.instance_id = o.id
            JOIN vision_images img ON i.image_id = img.id
            JOIN vision_appearances a ON a.image_id = img.id AND a.entity_id = o.id AND a.entity_type = 'Object'
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE p.role IN ('Target_Child', 'Assumed_Child') 
              AND i.interaction_type = 'Hand_Holding'
              AND d.user_id = :user_id 
              AND TO_CHAR(d.diary_date, 'YYYY-MM') = :target_month
        """)
        result_obj = await db.execute(query_obj, {"user_id": user_id, "target_month": target_month})
        df_obj = pd.DataFrame(result_obj.mappings().all())
        
        if not df_obj.empty:
            df_obj_unique = df_obj.drop_duplicates(subset=['instance_id', 'file_name'])
            top_instances = df_obj_unique['instance_id'].value_counts().head(1).index.tolist()
            
            for rank, inst_id in enumerate(top_instances, start=1):
                inst_data = df_obj_unique[df_obj_unique['instance_id'] == inst_id]
                category = inst_data.iloc[0]['base_category']
                
                appearances = []
                for _, row in inst_data.iterrows():
                    appearances.append({
                        "file_name": row['file_name'],
                        "bbox": json.loads(row['bounding_box'])
                    })
                
                report_data["favorite_objects"].append({
                    "rank": rank,
                    "category": category,
                    "appearances": appearances
                })

        # 2. 감정 스펙트럼
        query_emo = text("""
            SELECT p.emotion 
            FROM vision_persons p
            JOIN vision_appearances a ON p.id = a.entity_id AND a.entity_type = 'Person'
            JOIN vision_images img ON a.image_id = img.id
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE p.role = 'Target_Child' AND p.emotion != 'Unknown'
              AND d.user_id = :user_id AND TO_CHAR(d.diary_date, 'YYYY-MM') = :target_month
        """)
        result_emo = await db.execute(query_emo, {"user_id": user_id, "target_month": target_month})
        df_emo = pd.DataFrame(result_emo.mappings().all())
        
        if not df_emo.empty:
            top_emo = df_emo['emotion'].mode()[0] 
            report_data["top_emotion"] = top_emo

        # 3. 활동 환경 (실내 vs 실외)
        query_scene = text("""
            SELECT DISTINCT img.id as image_id, img.predicted_scene
            FROM vision_images img
            JOIN vision_appearances a ON img.id = a.image_id
            JOIN vision_persons p ON a.entity_id = p.id AND a.entity_type = 'Person'
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE p.role = 'Target_Child'
              AND d.user_id = :user_id AND TO_CHAR(d.diary_date, 'YYYY-MM') = :target_month
        """)
        result_scene = await db.execute(query_scene, {"user_id": user_id, "target_month": target_month})
        df_scene = pd.DataFrame(result_scene.mappings().all())
        
        if not df_scene.empty:
            scene_counts = df_scene['predicted_scene'].value_counts()
            indoor_cnt = scene_counts.get('Indoor', 0)
            outdoor_cnt = scene_counts.get('Outdoor', 0)
            
            if indoor_cnt > outdoor_cnt:
                report_data["primary_scene"] = "Indoor"
            elif outdoor_cnt > indoor_cnt:
                report_data["primary_scene"] = "Outdoor"
            else:
                report_data["primary_scene"] = "Balanced"

        # 4. 사회성 분석 (혼자 vs 함께)
        query_social = text("""
            SELECT img.id as image_id, p.role
            FROM vision_images img
            JOIN vision_appearances a ON img.id = a.image_id
            JOIN vision_persons p ON a.entity_id = p.id AND a.entity_type = 'Person'
            JOIN one_line_diaries d ON img.diary_id = d.id
            WHERE d.user_id = :user_id AND TO_CHAR(d.diary_date, 'YYYY-MM') = :target_month
        """)
        result_social = await db.execute(query_social, {"user_id": user_id, "target_month": target_month})
        df_social = pd.DataFrame(result_social.mappings().all())
        
        if not df_social.empty:
            child_images = df_social[df_social['role'] == 'Target_Child']['image_id'].unique()
            adult_images = df_social[df_social['role'] == 'Adult_Helper']['image_id'].unique()
            
            together_count = sum(1 for img in child_images if img in adult_images)
            alone_count = len(child_images) - together_count
            
            if together_count > alone_count:
                report_data["social_status"] = "Together"
            elif alone_count > together_count:
                report_data["social_status"] = "Alone"
            else:
                report_data["social_status"] = "Balanced"

    except Exception as e:
        print(f"Error generating report: {e}")
        # 실제 서비스에서는 로거(logger)를 사용하거나 HTTPException을 발생시키는 것이 좋습니다.

    return report_data