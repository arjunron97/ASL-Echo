import cv2
import mediapipe as mp
import pandas as pd

# Initialize MediaPipe models
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands


def extract_selected_landmarks(video_path, video_id, class_label, output_csv):
    cap = cv2.VideoCapture(video_path)

    # Initialize models with configurations
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=2)
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2)

    data = []
    frame_num = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to RGB for processing
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame with both models
        pose_results = pose.process(frame_rgb)
        hands_results = hands.process(frame_rgb)

        # Initialize landmarks array
        landmarks = [video_id, class_label, frame_num]

        # Extract face landmarks (indices 0-10)
        face_landmark_indices = list(range(11))
        if pose_results.pose_landmarks:
            for i in face_landmark_indices:
                lm = pose_results.pose_landmarks.landmark[i]
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * (len(face_landmark_indices) * 3))

        # Extract shoulder landmarks (indices 11-12)
        shoulder_indices = [11, 12]
        if pose_results.pose_landmarks:
            for i in shoulder_indices:
                lm = pose_results.pose_landmarks.landmark[i]
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * (len(shoulder_indices) * 3))

        # Process hands
        left_hand = None
        right_hand = None

        if hands_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(hands_results.multi_hand_landmarks,
                                                  hands_results.multi_handedness):
                label = handedness.classification[0].label
                if label == "Left" and left_hand is None:
                    left_hand = hand_landmarks
                elif label == "Right" and right_hand is None:
                    right_hand = hand_landmarks

        # Add left hand landmarks
        if left_hand:
            for lm in left_hand.landmark:
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * 63)  # 21 points × 3 coordinates

        # Add right hand landmarks
        if right_hand:
            for lm in right_hand.landmark:
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * 63)

        data.append(landmarks)
        frame_num += 1

    cap.release()

    # Create DataFrame with headers
    face_headers = [f"Face_LM_{i}_{axis}" for i in range(11) for axis in ['x', 'y', 'z']]
    shoulder_headers = [f"Shoulder_LM_{i}_{axis}" for i in range(11, 13) for axis in ['x', 'y', 'z']]
    left_hand_headers = [f"LH_LM_{i}_{axis}" for i in range(21) for axis in ['x', 'y', 'z']]
    right_hand_headers = [f"RH_LM_{i}_{axis}" for i in range(21) for axis in ['x', 'y', 'z']]

    columns = ["video_id", "class", "frame"] + face_headers + shoulder_headers + left_hand_headers + right_hand_headers

    # Save to CSV
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(output_csv, index=False)
    print(f"Successfully saved landmarks to {output_csv}")


# Example usage
extract_selected_landmarks("6Mmgrtw_Zro.f136.mp4", "video1", "hello", "output_landmarks.csv")