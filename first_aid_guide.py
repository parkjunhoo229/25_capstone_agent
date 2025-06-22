import os
import json

# 병명별 개별 JSON 로딩 함수
def load_disease_data(disease_name: str) -> dict | None:
    try:
        with open(f"first_aid_data/{disease_name}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def emergency_instruction(disease_name: str):
    data = load_disease_data(disease_name)
    if not data:
        print(f"에이전트: '{disease_name}'에 대한 응급처치 정보가 존재하지 않습니다.")
        return

    checklist = data.get("checklist", [])
    yes_instructions = []

    # 질문-응답 단계가 있는 경우
    if checklist:
        print("에이전트: 질문에 '예' 또는 '아니요'로 대답해주세요. 모르겠다면 '모르겠어요'라고 말씀해주세요.")
        for step in checklist:
            print(f"에이전트: {step['question']}")
            while True:
                user_input = input("사용자: ").strip()
                if user_input in ["예", "아니요", "모르겠어요"]:
                    break
                print("에이전트: '예', '아니요', 또는 '모르겠어요'로 대답해주세요.")
                
                if user_input in ["끝", "종료", "그만"]:
                    print("대화를 종료합니다.")
                    return

            if user_input == "예":
                yes_instructions.append(step["instruction"])

    print(f"에이전트: {data.get('intro', '')}")
    while input("다음 단계로 진행하려면 '다음'을 입력하세요: ").strip() != "다음":
        pass

    print(f"에이전트: {data.get('precaution', '')}")
    while input("사용자: ").strip() != "다음":
        pass

    # instruction 단계
    if checklist:
        for instruction in yes_instructions:
            print(f"에이전트: {instruction}")
            while input("사용자: ").strip() != "다음":
                pass
    else:
        print(f"에이전트: {data.get('instruction', '')}")
        while input("사용자: ").strip() != "다음":
            pass

    print(f"에이전트: {data.get('closing', '이상으로 응급처치 안내를 마치겠습니다. 빠른 회복을 바랍니다.')}")
