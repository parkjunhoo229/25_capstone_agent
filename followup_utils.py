# follow-up 질문 생성, 응답 파싱, 증상 잔여 여부 판단
import re

def parse_gpt_response(text):
    result = {
        "status": None,
        "symptoms": [],
        "candidates": []
    }

    status_match = re.search(r"- 상태:\s*(.*)", text)
    if status_match:
        result["status"] = status_match.group(1).strip()

    symptom_match = re.search(r"- 누적 증상:\s*\[(.*?)\]", text)
    if symptom_match:
        symptoms_str = symptom_match.group(1).strip()
        result["symptoms"] = [s.strip() for s in symptoms_str.split(",") if s.strip()]

    candidate_match = re.search(r"- 병명 후보:\s*(.*)", text)
    if candidate_match:
        result["candidates"] = [c.strip() for c in candidate_match.group(1).split(",") if c.strip()]

    return result

def extract_question_and_symptom(gpt_response: str):
    symptom = None
    question = None

    symptom_match = re.search(r"- 다음 질문 대상 증상:\s*(.+)", gpt_response)
    question_match = re.search(r"- 추가 질문:\s*(.+)", gpt_response)

    if symptom_match:
        symptom = symptom_match.group(1).strip()
    if question_match:
        question = question_match.group(1).strip()

    return symptom, question

def build_followup_question_prompt_from_partial_info(
    confirmed_symptoms, disease_candidates, disease_data, skipped_symptoms=None
):
    if skipped_symptoms is None:
        skipped_symptoms = []

    urgency_order = {"긴급": 3, "응급": 2, "비응급": 1}
    sorted_candidates = sorted(
        disease_candidates,
        key=lambda d: urgency_order.get(disease_data.get(d, {}).get("emergency_level", ""), 0),
        reverse=True
    )

    already_asked = set(confirmed_symptoms) | set(skipped_symptoms)    
    lines = []    
    
    for disease in sorted_candidates:
        symptoms = disease_data.get(disease, {}).get("symptoms", [])
        remaining = [s for s in symptoms if s not in already_asked]
        
        if remaining:
            lines.append(f"{disease}: [{', '.join(remaining)}]")

    disease_symptom_text = "\n".join(lines)

    print("✅ 이미 물어본 증상 (confirmed + skipped):", already_asked)
    print("✅ 확인된 증상 (confirmed + skipped):", confirmed_symptoms)
    print("✅ 아니요, 모르겠음 응답 증상 (confirmed + skipped):", skipped_symptoms)

    return f"""
너는 응급환자 증상을 기반으로 질병을 감별하고자 하는 AI 응급의료 에이전트다.

[후보 병명의 남은 의심 증상 목록]
{disease_symptom_text}

[절대 물어보면 안되는 의심 증상 목록]
{already_asked}

위 정보를 참고하여, 병명 감별에 유용한 **한 가지 증상**을 골라 질문을 작성하라.

[출력 규칙 – 반드시 지킬 것]
- 아래 두 줄을 반드시 포함하라. 이 두 줄 외에 아무것도 출력하지 말 것.
- 첫 줄: 다음 질문 대상 증상 → 반드시 질병-증상 매핑에서 가져온 **정확한 증상 키워드 전체 문장**
- 두 번째 줄: 사용자에게 보여줄 질문 → 해당 증상에 대한 자연어 질문 문장 (한 문장), 반드시 아래 조건을 따를 것:

[질문 생성 조건]
- [절대 물어보면 안되는 의심 증상 목록]에 포함된 증상은 절대 질문하지 마세요. 반드시 제외하고 질문을 구성하세요.
- 반드시 **한 가지 증상만** 묻는 **짧고 명확한 문장**으로 작성할 것
- 반드시 다음 문장으로 끝낼 것: “추가적인 증상이 있다면 편하게 말씀해주세요.”
- **복합 질문은 금지** (예시: "그리고", "또는" 등으로 두 가지 이상 묻지 말 것)
- 반드시 증상이 **존재하는지 여부**를 묻는 형식으로 질문할 것! **좋은 예시: "의식을 잃었나요?", "가슴 통증이 있나요?"**,  **나쁜 예시: "의식이 있나요?", "가슴 통증이 없나요?"**
- 반드시 [후보 병명의 남은 의심 증상 목록]에 포함된 증상으로만 질문할 것!
- **가능하면 위쪽에 있는 병명(긴급한 병명)의 증상부터 질문할 것!**
- 추가 질문 포맷을 반드시 지킬 것

[출력 포멧 (반드시 이 형식을 지킬 것)]
- 다음 질문 대상 증상: 
- 추가 질문: 

[출력 예시]
- 다음 질문 대상 증상: 한쪽 얼굴이 처짐 (예: 웃으려고 할 때 비대칭)
- 추가 질문: 한쪽 얼굴이 비대칭인가요? 추가적인 증상이 있다면 편하게 말씀해주세요.
""".strip()

def has_remaining_symptoms(disease_candidates, confirmed_symptoms, disease_data, skipped_symptoms=None):
    if skipped_symptoms is None:
        skipped_symptoms = []

    already_asked = set(confirmed_symptoms) | set(skipped_symptoms)

    for disease in disease_candidates:
        if disease not in disease_data:
            continue
        symptoms = disease_data[disease].get("symptoms", [])
        remaining = [s for s in symptoms if s not in already_asked]
        if remaining:
            return True
    return False