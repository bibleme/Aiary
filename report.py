import os
import json
import sqlite3
import pandas as pd

# ----------------------------
# 경로 및 설정
# ----------------------------
BASE_DIR = "./"

# 입력 DB 경로 (AI 비전 분석 파이프라인이 저장한 DB)
DB_PATH = os.path.join(BASE_DIR, "outputs/parenting_report_final.db")

# ----------------------------
# 월간 리포트 알고리즘
# ----------------------------
def generate_monthly_report(db_path: str) -> dict:
    """
    월간 리포트 데이터를 생성하여 프론트엔드(Kotlin)에 전달할 JSON(Dict) 틀을 반환합니다.
    AI 모델의 불확실성을 고려하여 정확한 '횟수'는 제외하고 랭킹과 주요 경향성만 도출합니다.
    """
    # 최종 프론트엔드로 내려갈 JSON 구조
    report_data = {
        "favorite_objects": [],
        "top_emotion": None,
        "primary_scene": None,
        "social_status": None
    }

    if not os.path.exists(db_path):
        print(f"[경고] DB 파일을 찾을 수 없습니다: {db_path}")
        return report_data

    conn = sqlite3.connect(db_path)

    try:
        # 1. 애착 물건: 횟수 없이 순위와 크롭용 팝업 사진 정보만 제공
        query_obj = """
            SELECT i.instance_id, o.base_category, img.file_name, a.bounding_box
            FROM interactions i
            JOIN persons p ON i.person_id = p.person_id
            JOIN object_instances o ON i.instance_id = o.instance_id
            JOIN images img ON i.image_id = img.image_id
            JOIN appearances a ON a.image_id = img.image_id AND a.entity_id = o.instance_id AND a.entity_type = 'Object'
            WHERE p.role IN ('Target_Child', 'Assumed_Child') AND i.interaction_type = 'Hand_Holding'
        """
        df_obj = pd.read_sql_query(query_obj, conn)
        
        if not df_obj.empty:
            df_obj_unique = df_obj.drop_duplicates(subset=['instance_id', 'file_name'])
            top_instances = df_obj_unique['instance_id'].value_counts().head(3).index.tolist()
            
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

        # 2. 감정 스펙트럼: 가장 많이 포착된 표정 1개만 추출
        query_emo = "SELECT emotion FROM persons WHERE role = 'Target_Child' AND emotion != 'Unknown'"
        df_emo = pd.read_sql_query(query_emo, conn)
        
        if not df_emo.empty:
            top_emo = df_emo['emotion'].mode()[0] 
            report_data["top_emotion"] = top_emo

        # 3. 활동 환경: 실내 vs 실외 비중 비교
        query_scene = """
            SELECT DISTINCT img.image_id, img.predicted_scene
            FROM images img
            JOIN appearances a ON img.image_id = a.image_id
            JOIN persons p ON a.entity_id = p.person_id AND a.entity_type = 'Person'
            WHERE p.role = 'Target_Child'
        """
        df_scene = pd.read_sql_query(query_scene, conn)
        
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

        # 4. 사회성 분석: 혼자 vs 보호자와 함께
        query_social = """
            SELECT img.image_id, p.role
            FROM images img
            JOIN appearances a ON img.image_id = a.image_id
            JOIN persons p ON a.entity_id = p.person_id AND a.entity_type = 'Person'
        """
        df_social = pd.read_sql_query(query_social, conn)
        
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
    finally:
        conn.close()

    return report_data

# ----------------------------
# main
# ----------------------------
if __name__ == "__main__":
    print("월간 리포트 데이터 생성을 시작합니다...")
    
    try:
        if os.path.exists(DB_PATH):
            result_json = generate_monthly_report(DB_PATH)
            print("\n[REPORT RESULT]")
            print(json.dumps(result_json, indent=2, ensure_ascii=False))
            print("\n✅ 프론트엔드 전달용 리포트 JSON 생성이 완료되었습니다.")
        else:
            print(f"DB 파일을 찾을 수 없습니다: {DB_PATH}")
    except Exception as e:
        print(f"오류 발생: {e}")
