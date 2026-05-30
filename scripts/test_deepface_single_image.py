from pathlib import Path


from app.db.model import Diary
from app.services.cv_runner import resolve_local_image_path
from app.services.cv_face_runner import get_user_child_refs, verify_target_child, analyze_faces



def main():
    # 여기 값은 매번 테스트할 때 바꿔서 사용
    diary = Diary(
        id=0,
        user_id=15,
        content="",
        image_url="/media/images/20260411_124739_5c7ca2ab.jpg",
    )

    image_path = resolve_local_image_path(diary.image_url)
    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일 없음: {image_path}")

    refs = get_user_child_refs(diary.user_id)
    print("REF_COUNT =", len(refs))

    target_child_found, target_child_confidence = verify_target_child(image_path, refs)
    print("TARGET_CHILD_FOUND =", target_child_found)
    print("TARGET_CHILD_CONFIDENCE =", target_child_confidence)

    persons = analyze_faces(image_path, target_child_found)
    print("PERSON_COUNT =", len(persons))
    print("PERSONS =", persons)


if __name__ == "__main__":
    main()