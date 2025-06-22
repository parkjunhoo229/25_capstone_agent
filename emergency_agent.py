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
    api_key = os.getenv("OPENAI_API_KEY")   # .env에서 불러온 OpenAI API 키 (OPENAI_API_KEY)
    client = openai.OpenAI(api_key=api_key) # GPT 호출을 위한 OpenAI API 클라이언트

    disease_data = load_disease_json()  # 전체 질병-증상 매핑 데이터 (예: "골절": { "symptoms": [...], "emergency_level": "응급" })
    disease_text = get_disease_prompt_string(disease_data) # GPT 프롬프트에 넣을 요약 텍스트 (모든 병명 + 응급도 + 증상 목록 정리 문자열)

    ### 최초 추론 시작###

    # 사용자와 에이전트 간의 대화 기록 (GPT 프롬프트 생성에 사용)
    chat_history = []
    print("에이전트: 환자의 상태를 말씀해주세요. 어떤 증상이 있나요?")
    chat_history.append({"role": "assistant", "content": "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"})

    confirmed_symptoms = [] # 확정된 증상 키워드 목록
    skipped_symptoms = []   # 사용자 응답 중 “아니오” 또는 “모르겠어요”라고 한 증상 목록
    question_count = 0  # 지금까지 생성된 follow-up 질문 수 (질문 상한 제어용)

    first_input = input("사용자: ").strip() # 사용자로부터 받은 첫 증상 입력
    if first_input in ["끝", "종료", "그만"]:
        print("대화를 종료합니다.")
        return
    chat_history.append({"role": "user", "content": first_input})

    # GPT에게 보낼 병명 추론용 프롬프트 전체 문자열
    full_prompt = build_gpt_prompt_from_chat_history(chat_history, disease_text)
    try:
        # GPT가 반환한 응답 (openai 클라이언트에서 생성됨)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.2,
            timeout=15
        )
        # GPT 응답 중 텍스트 부분 (예: "- 상태: 진행중\n- 누적 증상: [...]")
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

    # GPT 응답을 파싱한 결과 (status, symptoms, candidates 키 포함)
    parsed = parse_gpt_response(reply)
    

    # 1. 전체 진단 흐름 루프
    while True:
        if parsed["status"] == "진행중":
            for s in parsed["symptoms"]:
                if s not in confirmed_symptoms:
                    confirmed_symptoms.append(s)

            # 현재 GPT가 제시한 병명 후보 리스트
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
           
            if not has_remaining_symptoms(disease_candidates, confirmed_symptoms, disease_data, skipped_symptoms):
                # 응급도 문자열을 정수 우선순위로 바꾼 매핑 (ex: "긴급" > "응급" > "비응급")
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
                    confirmed_symptoms, # 확정된 증상 키워드 목록
                    disease_candidates, # 병명 후보
                    disease_data,       # 전체 질병-증상 매핑 데이터
                    skipped_symptoms    # "아니오" 또는 "모르겠어요"라고 대답한 증상 목록
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
                    # GPT가 생성한 전체 follow-up 질문 응답(두 줄 구성)
                    next_question_full = followup_response.choices[0].message.content.strip()
                    # GPT가 생성한 질문이 타겟하는 증상 키워드, 사용자에게 보여줄 follow-up 질문 문장
                    # print("----------------------\n" + next_question_full+"\n-----------------------")
                    symptom_keyword, next_question = extract_question_and_symptom(next_question_full) 
                                       
                except openai.OpenAIError as e:
                    print("에이전트: 추가 질문 생성 중 GPT 호출에 실패했습니다. 네트워크 상태를 확인해주세요.")
                    retry = input("이어서 진행할까요? (예: 이어서 진행 / 아니오: 진단 종료): ").strip()
                    if retry in ["예", "그래", "어"]:
                        continue  # 2 루프 처음부터 다시
                    else:
                        print("에이전트: 진단을 종료합니다.")
                        return

                if symptom_keyword in confirmed_symptoms or symptom_keyword in skipped_symptoms:
                    retry_count += 1
                    print("에이전트: 동일한 질문이 반복되었습니다. 새로운 질문을 생성합니다...")
                    if retry_count >= MAX_RETRY:
                        failure_message = "에이전트: 새로운 질문 생성에 실패했습니다."
                        print(failure_message)
                                          
                        # 사용자로부터 받은 follow-up 질문에 대한 응답      
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
            # 사용자의 응답을 분류한 결과 ("예", "아니오", "모르겠음")
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