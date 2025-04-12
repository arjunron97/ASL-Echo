import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Initialize models with full-frame processing
pose = mp_pose.Pose(
    static_image_mode=True,  # Disables ROI (region of interest) tracking
    min_detection_confidence=0.5
)

hands = mp_hands.Hands(
    static_image_mode=True,  # Disables automatic zoom/ROI
    max_num_hands=2,
    min_detection_confidence=0.5
)


def detect_landmarks(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process detection on full frame
    pose_results = pose.process(frame_rgb)
    hand_results = hands.process(frame_rgb)

    # Draw results
    if hand_results.multi_hand_landmarks:
        for landmarks in hand_results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame, landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2))

            if pose_results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2))

    return frame


# Webcam setup
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = detect_landmarks(frame)
    cv2.imshow('Detection - Zoom Disabled', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
pose.close()
hands.close()
