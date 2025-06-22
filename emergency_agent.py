# 전체 진단 로직을 총괄
from dotenv import load_dotenv
import os
import openai
from persona import SYSTEM_MESSAGE
from analyze_prompt import build_gpt_prompt_from_chat_history, build_final_diagnosis_prompt
from gpt_prompt_utils import load_disease_json, get_disease_prompt_string
from followup_utils import (
    parse_gpt_response,
    build_followup_question_prompt_from_partial_info,
    has_remaining_symptoms,
    extract_question_and_symptom
)
from classify_response import classify_user_response
from first_aid_guide import emergency_instruction

def run_diagnosis_session():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)

    disease_data = load_disease_json()
    disease_text = get_disease_prompt_string(disease_data)

    chat_history = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "assistant", "content": "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"}
    ]
    print("에이전트:", chat_history[1]["content"])

    confirmed_symptoms = []
    skipped_symptoms = []
    question_count = 0

    first_input = input("사용자: ").strip()
    if first_input in ["끝", "종료", "그만"]:
        print("대화를 종료합니다.")
        return
    chat_history.append({"role": "user", "content": first_input})

    full_prompt = build_gpt_prompt_from_chat_history(chat_history[1:], disease_text)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.2,
            timeout=15
        )
        reply = response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        print("에이전트: 병명 추론 중 GPT 호출에 실패했습니다. 네트워크 상태를 확인해주세요.")
        retry = input("계속 시도할까요? (예: 이어서 진행 / 아니오: 진단 종료): ").strip()
        if retry in ["예", "그래", "어"]:
            return run_diagnosis_session()  # 1 루프 다시 시작
        else:
            print("에이전트: 진단을 종료합니다.")
            return
    
    print("에이전트:", reply)
#   ==> 분석 결과 출력 포맷:
#   - 상태: 확정 or 진행중
#   - 누적 증상: [증상1, 증상2, ...]
#   - 병명 후보: ...
#   - 응급도: **병명이 확정된 경우에만 출력할 것!**
    chat_history.append({"role": "assistant", "content": reply})

    parsed = parse_gpt_response(reply)
    

    # 1. 전체 진단 흐름 루프
    while True:
        if parsed["status"] == "진행중":
            for s in parsed["symptoms"]:
                if s not in confirmed_symptoms:
                    confirmed_symptoms.append(s)

            disease_candidates = parsed["candidates"]

            if question_count == 15:
                urgency_order = {"긴급": 3, "응급": 2, "비응급": 1}
                max_level = "비응급"
                for d in disease_candidates:
                    if d in disease_data:
                        level = disease_data[d]["emergency_level"]
                        if urgency_order[level] > urgency_order[max_level]:
                            max_level = level

                print("에이전트: 병명을 확정하는 데 실패했습니다.")
                
                if max_level == "긴급":
                    print(f"현재 병명 후보 중 {', '.join(disease_candidates)} 등이 있어 긴급 상황일 수 있습니다.")
                elif max_level == "응급":
                    print(f"현재 병명 후보 중 {', '.join(disease_candidates)} 등이 있어 응급 상황일 수 있습니다.")

                print("119에 연결해 드릴까요?")
                final_input = input("사용자 (예: 119 연결 요청 / 아니요: 처음부터 다시 시작): ").strip()
                
                if final_input in ["예", "그래", "어"]:
                    print("에이전트: 119 통화 연결을 시작하겠습니다...")
                    return
                else:
                    print("에이전트: 처음부터 다시 시작하겠습니다.")
                    return

            if question_count == 10:
                print("에이전트: 질문 횟수가 많아지고 있습니다. 119에 연결해 드릴까요?")
                
                final_input = input("사용자 (예: 119 연결 요청 / 아니요: 질문 계속): ").strip()
                                
                if final_input in ["예", "그래", "어"]:
                    print("에이전트: 119 통화 연결을 시작하겠습니다...")
                    return
                else:
                    print("에이전트: 질문을 이어가겠습니다.")
                    continue    # 현재 while 루프의 다음 턴으로 이동
           
            if not has_remaining_symptoms(disease_candidates, confirmed_symptoms, disease_data):
                urgency_order = {"긴급": 3, "응급": 2, "비응급": 1}
                max_level = "비응급"
                for d in disease_candidates:
                    if d in disease_data:
                        level = disease_data[d]["emergency_level"]
                        if urgency_order[level] > urgency_order[max_level]:
                            max_level = level

                print("에이전트: 병명을 확정하는 데 실패했습니다.")
                if max_level == "긴급":
                    print(f"현재 병명 후보 중 {', '.join(disease_candidates)} 등이 있어 긴급 상황일 수 있습니다.")
                elif max_level == "응급":
                    print(f"현재 병명 후보 중 {', '.join(disease_candidates)} 등이 있어 응급 상황일 수 있습니다.")
                else:
                    print(f"현재 병명 후보 중 {', '.join(disease_candidates)} 등이 있으며, 비응급 상황일 수 있습니다.")

                print("119에 연결해 드릴까요?")
                final_input = input("사용자 (예: 119 연결 요청 / 아니요: 처음부터 다시 시작): ").strip()
                
                if final_input in ["예", "그래", "어"]:
                    print("에이전트: 119 통화 연결을 시작하겠습니다...")
                    return
                else:
                    print("에이전트: 처음부터 다시 시작하겠습니다.")
                    return


            question_count += 1
            
            # 2. follow-up 질문 생성 루프
            retry_count = 0
            MAX_RETRY = 3

            while True:
                followup_prompt = build_followup_question_prompt_from_partial_info(
                    confirmed_symptoms,
                    disease_candidates,
                    disease_data,
                    skipped_symptoms
                )
                
                try:
                    followup_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": SYSTEM_MESSAGE},
                            {"role": "user", "content": followup_prompt}
                        ],
                        temperature=0.2,
                        timeout=15
                    )
                    next_question_full = followup_response.choices[0].message.content.strip()
                    symptom_keyword, next_question = extract_question_and_symptom(next_question_full) 
                                       
                except openai.OpenAIError as e:
                    print("에이전트: 추가 질문 생성 중 GPT 호출에 실패했습니다. 네트워크 상태를 확인해주세요.")
                    retry = input("이어서 진행할까요? (예: 이어서 진행 / 아니오: 진단 종료): ").strip()
                    if retry in ["예", "그래", "어"]:
                        continue  # 2 루프 처음부터 다시
                    else:
                        print("에이전트: 진단을 종료합니다.")
                        return
                
                previous_questions = [
                    entry["content"] for entry in chat_history
                    if entry["role"] == "assistant" and entry["content"].startswith("에이전트(추가 질문):") is False
                    ]
                
                if next_question in previous_questions:
                    retry_count += 1
                    print("에이전트: 동일한 질문이 반복되었습니다. 새로운 질문을 생성합니다...")
                    if retry_count >= MAX_RETRY:
                        failure_message = "에이전트: 새로운 질문 생성에 실패했습니다."
                        print(failure_message)
                                                
                        final_input = input("사용자 (예: 119 연결 요청 / 아니요: 처음부터 다시 시작): ").strip()
                                                
                        if final_input in ["예", "그래", "어"]:
                            print("에이전트: 119 통화 연결을 시작하겠습니다...")
                            return
                        else:
                            print("에이전트: 처음부터 다시 시작하겠습니다.")
                            return 
                    else:
                        continue    # follow-up 루프 처음부터 반복
                break   # 중복 질문이 아니면 -> follow-up 루프 종료 → 다음 질문 출력

            print("에이전트(추가 질문):", next_question)
            chat_history.append({"role": "assistant", "content": next_question})
            
            followup_input = input("사용자: ").strip()
            if followup_input in ["끝", "종료", "그만"]:
                print("대화를 종료합니다.")
                return  # 전체 루프 종료
            
            chat_history.append({"role": "user", "content": followup_input})

            answer_type = classify_user_response(next_question, followup_input)
            if answer_type == "INVALID":
                followup_input = input("에이전트: 죄송합니다. 조금 더 명확하게 말씀해주실 수 있나요?\n사용자: ").strip()
                chat_history.append({"role": "assistant", "content": "죄송합니다. 조금 더 명확하게 말씀해주실 수 있나요?"})
                chat_history.append({"role": "user", "content": followup_input})
                answer_type = classify_user_response(next_question, followup_input)
            elif answer_type == "예":
                if symptom_keyword not in confirmed_symptoms:
                    confirmed_symptoms.append(symptom_keyword)
            elif answer_type in ["아니오", "모르겠음"]:
                if symptom_keyword not in skipped_symptoms:
                    skipped_symptoms.append(symptom_keyword)
            
            
            full_prompt = build_final_diagnosis_prompt(confirmed_symptoms, disease_text)
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.2,
                    timeout=15
                )
                reply = response.choices[0].message.content.strip()
            except openai.OpenAIError as e:
                print("에이전트: 병명 추론 중 GPT 호출에 실패했습니다. 네트워크 상태를 확인해주세요.")
                retry = input("계속 시도할까요? (예: 이어서 진행 / 아니오: 진단 종료): ").strip()
                if retry in ["예", "그래", "어"]:
                    return run_diagnosis_session()  # 1 루프 다시 시작
                else:
                    print("에이전트: 진단을 종료합니다.")
                    return
    
            print("에이전트:", reply)
            chat_history.append({"role": "assistant", "content": reply})

            parsed = parse_gpt_response(reply)
            
            continue    # GPT 판단 및 질문 생성 (다음 턴으로 이동)

        # 응급 메세지는 예시를 보여준 것, 실제로 에이전트는 데이터만 전달하고 메세지는 백엔드에서 처리
        elif parsed["status"] == "확정":
            confirmed_disease = parsed["candidates"][0]
            emergency_level = disease_data[confirmed_disease]["emergency_level"]
            print(f"확정된 병명: {confirmed_disease} (응급도: {emergency_level})")

            if emergency_level == "긴급":
                print("에이전트: 긴급한 상태입니다. 119가 출동 예정입니다.")
                alert_id = "test-alert-id-001"
                phone = "010-1234-5678"
                gps = "서울특별시 종로구 세종대로 110"
                alert_message = {
                    "ID": alert_id,
                    "신고자 전화번호": phone,
                    "병명": confirmed_disease,
                    "증상": confirmed_symptoms,
                    "GPS위치": gps
                }
                print("1차 긴급 메시지:")
                print(alert_message)
                location = input("에이전트: 정확한 위치를 입력해주세요 (건물명, 층수 등): ").strip()
                update_message = {                    
                    "상세위치": location
                }
                print("상세 위치 메시지:")
                print(update_message)
                emergency_instruction(confirmed_disease)
                return

            elif emergency_level == "응급":
                print(f"에이전트: 현재 환자가 {confirmed_disease}로 응급 상태입니다. 119에 도움을 요청하시겠습니까?")
                agree = input("사용자 (예: 119 신고 / 아니요: 응급처치 안내): ").strip()
                if agree in ["예", "그래", "어"]:
                    alert_id = "test-alert-id-002"
                    phone = "010-1234-5678"
                    gps = "서울특별시 종로구 세종대로 110"
                    location = input("에이전트: 정확한 위치를 입력해주세요 (건물명, 층수 등): ").strip()
                    alert_message = {
                        "ID": alert_id,
                        "신고자 전화번호": phone,
                        "병명": confirmed_disease,
                        "증상": confirmed_symptoms,
                        "GPS위치": gps,
                        "상세위치": location
                    }
                    print("응급 메시지:")
                    print(alert_message)
                    
                emergency_instruction(confirmed_disease)
                return

            elif emergency_level == "비응급":
                print(f"에이전트: 현재 환자가 {confirmed_disease}로 비응급 상태입니다. 응급 처치를 안내하겠습니다.")
                emergency_instruction(confirmed_disease)
                return