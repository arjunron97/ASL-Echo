"""
ASL Video Landmark Processor with JSON Configuration
"""

import os
import re
import json
import cv2
import pandas as pd
import mediapipe as mp

# MediaPipe initializations
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands


# ========================
# Core Processing Functions
# ========================

def find_video_file(base_dir, link_id):
    """Find video file using flexible naming pattern"""
    pattern = re.compile(rf".*{re.escape(link_id)}.*\.mp4$", re.IGNORECASE)
    for root, _, files in os.walk(base_dir):
        for file in files:
            if pattern.match(file):
                return os.path.join(root, file)
    return None


def parse_json_to_video_info(json_path, video_base_dir):
    """Convert JSON structure to video processing queue"""
    with open(json_path) as f:
        data = json.load(f)

    video_info_list = []

    for entry in data:
        link_id = entry["link_id"]
        video_path = find_video_file(video_base_dir, link_id)

        if not video_path:
            print(f"⚠️ Skipping {link_id} - video file not found")
            continue

        # Extract all class segments (class1, class2, etc)
        classes = [v for k, v in entry.items()
                   if k.startswith("class") and k[5:].isdigit()]

        for class_info in classes:
            video_info_list.append({
                "path": video_path,
                "id": f"{link_id}_{class_info['name']}",
                "class": class_info["name"],
                "start_sec": class_info["start_time"],
                "end_sec": class_info["end_time"]
            })

    return video_info_list


def process_single_video(video_path, video_id, class_label, pose, hands, start_sec, end_sec):
    """Process a video segment and extract landmarks"""
    cap = cv2.VideoCapture(video_path)
    data = []

    try:
        # Video metadata
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate frame range
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)
        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = max(start_frame, min(end_frame, total_frames - 1))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current_frame = start_frame

        while cap.isOpened() and current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            # Landmark extraction
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_height, image_width, _ = frame_rgb.shape
            pose_results = pose.process(frame_rgb)
            hands_results = hands.process(frame_rgb)

            # Initialize landmark record
            landmarks = [video_id, class_label, current_frame]

            # Process pose landmarks
            _process_landmarks(pose_results.pose_landmarks,
                                    face_indices=range(11),
                                    shoulder_indices=[11, 12],
                                    landmarks=landmarks)

            # Process hands
            _process_hands(hands_results, landmarks)

            data.append(landmarks)
            current_frame += 1

    finally:
        cap.release()

    return data


def _process_landmarks(pose_landmarks, face_indices, shoulder_indices, landmarks):
    """Helper: Process pose-related landmarks"""
    # Face/Head (0-10)
    if pose_landmarks:
        for i in face_indices:
            lm = pose_landmarks.landmark[i]
            landmarks.extend([lm.x, lm.y, lm.z])
    else:
        landmarks.extend([0] * (len(face_indices) * 3))

    # Shoulders (11-12)
    if pose_landmarks:
        for i in shoulder_indices:
            lm = pose_landmarks.landmark[i]
            landmarks.extend([lm.x, lm.y, lm.z])
    else:
        landmarks.extend([0] * (len(shoulder_indices) * 3))


def _process_hands(hands_results, landmarks):
    """Helper: Process hand landmarks"""
    left_hand = right_hand = None

    if hands_results.multi_hand_landmarks:
        for hand, handedness in zip(hands_results.multi_hand_landmarks,
                                    hands_results.multi_handedness):
            label = handedness.classification[0].label
            if label == "Left" and not left_hand:
                left_hand = hand
            elif label == "Right" and not right_hand:
                right_hand = hand

    # Left hand (21 landmarks x 3 coordinates)
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


def process_video_batch(json_path, video_base_dir, output_dir="output_landmarks"):
    """Main entry point for batch processing"""
    # Prepare directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize MediaPipe once
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=2)
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2)

    try:
        # Parse JSON and prepare processing queue
        video_info_list = parse_json_to_video_info(json_path, video_base_dir)
        if not video_info_list:
            print("❌ No valid video segments to process")
            return

        # CSV headers
        columns = ["video_id", "class", "frame"] + \
                  [f"Face_LM_{i}_{ax}" for i in range(11) for ax in ['x', 'y', 'z']] + \
                  [f"Shoulder_LM_{i}_{ax}" for i in [11, 12] for ax in ['x', 'y', 'z']] + \
                  [f"LH_LM_{i}_{ax}" for i in range(21) for ax in ['x', 'y', 'z']] + \
                  [f"RH_LM_{i}_{ax}" for i in range(21) for ax in ['x', 'y', 'z']]

        # Process all segments
        for vid_info in video_info_list:
            try:
                print(f"⏳ Processing {vid_info['id']}...")
                data = process_single_video(
                    video_path=vid_info['path'],
                    video_id=vid_info['id'],
                    class_label=vid_info['class'],
                    pose=pose,
                    hands=hands,
                    start_sec=vid_info['start_sec'],
                    end_sec=vid_info['end_sec']
                )

                # Save results
                df = pd.DataFrame(data, columns=columns)
                output_path = os.path.join(output_dir, f"{vid_info['id']}_landmarks.csv")
                df.to_csv(output_path, index=False)
                print(f"✅ Saved {output_path}")

            except Exception as e:
                print(f"❌ Failed {vid_info['id']}: {str(e)}")

    finally:
        # Cleanup MediaPipe resources
        pose.close()
        hands.close()


# ========================
# Execution Example
# ========================
if __name__ == "__main__":
    # Configure these paths
    JSON_PATH = "C:/Users/kaush/Music/asl/MS-ASL/MSASL_test_transformed.json"
    VIDEO_BASE_DIR = "C:/Users/kaush/Music/asl\MS-ASL/trash"
    OUTPUT_DIR = "asl_landmarks_output"

    process_video_batch(
        json_path=JSON_PATH,
        video_base_dir=VIDEO_BASE_DIR,
        output_dir=OUTPUT_DIR
    )
