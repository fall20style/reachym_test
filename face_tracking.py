# face_tracking.py

import cv2
import numpy as np
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

# OpenCV 기본 얼굴 감지기(Haar Cascade) 로드
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# PC 기본 웹캠(0번) 열기
cap = cv2.VideoCapture(0)

# 부드러운 움직임을 위한 이전 목표 각도 저장 변수
smooth_yaw = 0.0
smooth_pitch = 0.0
ALPHA = 0.25  # 반응 속도 계수 (0.1: 매우 부드러움 ~ 0.5: 빠름)

print("얼굴 추적을 시작합니다. 종료하려면 웹캠 창을 선택하고 'q'를 누르세요.")

with ReachyMini() as mini:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 거울 모드(좌우 반전) 적용 및 흑백 변환
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 얼굴 검출
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        if len(faces) > 0:
            # 가장 크게 인식된 얼굴 1개 선택
            x, y, fw, fh = max(faces, key=lambda rect: rect[2] * rect[3])
            
            # 화면에 얼굴 박스 및 중심점 표시
            cx, cy = x + fw // 2, y + fh // 2
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # 화면 중심(0, 0) 기준으로 얼굴 위치를 -1.0 ~ +1.0 범위로 정규화
            norm_x = (cx - w / 2) / (w / 2)
            norm_y = (cy - h / 2) / (h / 2)

            # 목표 회전 각도 계산 (좌우 최대 ±35도, 상하 최대 ±25도)
            target_yaw = -norm_x * 35.0
            target_pitch = norm_y * 25.0

            # 지수 이동 평균(EMA) 필터로 떨림 방지
            smooth_yaw += ALPHA * (target_yaw - smooth_yaw)
            smooth_pitch += ALPHA * (target_pitch - smooth_pitch)

            # 실시간 제어에는 goto_target 대신 set_target 사용 (블로킹 없이 즉시 갱신)
            mini.set_target(
                head=create_head_pose(
                    yaw=smooth_yaw,
                    pitch=smooth_pitch,
                    degrees=True
                ),
                # 얼굴을 발견하면 안테나를 반갑게 살짝 벌림
                antennas=[0.35, -0.35]
            )
        else:
            # 얼굴이 안 보이면 안테나를 원래 위치로 내림
            mini.set_target(antennas=[0.0, 0.0])

        cv2.imshow("PC Webcam - Reachy Mini Face Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # 종료 시 기본 자세로 복귀
    mini.goto_target(head=create_head_pose(), antennas=[0.0, 0.0], duration=0.8)

cap.release()
cv2.destroyAllWindows()
