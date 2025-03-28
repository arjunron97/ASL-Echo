"""
this function getteg head , sholgers and hand sign for barch processing
"""


def process_single_video(video_path, video_id, class_label):
    cap = cv2.VideoCapture(video_path)
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=2)
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2)

    data = []
    frame_num = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = pose.process(frame_rgb)
        hands_results = hands.process(frame_rgb)

        landmarks = [video_id, class_label, frame_num]

        # Process face/head landmarks (indices 0-10)
        face_landmark_indices = list(range(11))
        if pose_results.pose_landmarks:
            for i in face_landmark_indices:
                lm = pose_results.pose_landmarks.landmark[i]
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * (len(face_landmark_indices) * 3))

        # Process shoulders (indices 11-12)
        shoulder_indices = [11, 12]
        if pose_results.pose_landmarks:
            for i in shoulder_indices:
                lm = pose_results.pose_landmarks.landmark[i]
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * (len(shoulder_indices) * 3))

        # Process hands
        left_hand = right_hand = None

        if hands_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(hands_results.multi_hand_landmarks,
                                                  hands_results.multi_handedness):
                label = handedness.classification[0].label

                if label == "Left" and left_hand is None:
                    left_hand = hand_landmarks
                elif label == "Right" and right_hand is None:
                    right_hand = hand_landmarks

        # Left hand
        if left_hand:
            for lm in left_hand.landmark:
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * 63)

        # Right hand
        if right_hand:
            for lm in right_hand.landmark:
                landmarks.extend([lm.x, lm.y, lm.z])
        else:
            landmarks.extend([0] * 63)

        data.append(landmarks)
        frame_num += 1

    cap.release()
    return data


def process_video_batch(video_info_list, output_dir="output_landmarks"):
    import os

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define headers (same for all files)
    face_headers = [f"Face_LM_{i}_{axis}" for i in range(11) for axis in ['x', 'y', 'z']]
    shoulder_headers = [f"Shoulder_LM_{i}_{axis}" for i in range(2) for axis in ['x', 'y', 'z']]
    left_hand_headers = [f"LH_LM_{i}_{axis}" for i in range(21) for axis in ['x', 'y', 'z']]
    right_hand_headers = [f"RH_LM_{i}_{axis}" for i in range(21) for axis in ['x', 'y', 'z']]
    columns = ["video_id", "class", "frame"] + face_headers + shoulder_headers + left_hand_headers + right_hand_headers

    for video_info in video_info_list:
        video_path = video_info['path']
        video_id = video_info['id']
        class_label = video_info['class']

        print(f"Processing {video_id}...")

        try:
            data = process_single_video(video_path, video_id, class_label)

            # Create DataFrame and save
            df = pd.DataFrame(data, columns=columns)
            output_filename = f"{video_id}_landmarks.csv"
            output_path = os.path.join(output_dir, output_filename)
            df.to_csv(output_path, index=False)

            print(f"Saved {output_path}")

        except Exception as e:
            print(f"Error processing {video_id}: {str(e)}")
            continue