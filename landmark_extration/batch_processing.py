import cv2
import mediapipe as mp
import pandas as pd
import os
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import time
import logging

# Initialize MediaPipe models
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands

# Configure logging
logging.basicConfig(
    filename='landmark_processing.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
FACE_LANDMARK_INDICES = list(range(11))  # 0-10 for face/head
SHOULDER_INDICES = [11, 12]             # Shoulder landmarks
HAND_LANDMARKS = 21                     # 21 landmarks per hand

def init_models():
    """Initialize fresh models for each parallel process"""
    return {
        'pose': mp_pose.Pose(static_image_mode=False, model_complexity=2),
        'hands': mp_hands.Hands(static_image_mode=False, max_num_hands=2)
    }

def process_video_frame(args):
    """Process a single video frame"""
    frame_rgb, models = args
    pose_results = models['pose'].process(frame_rgb)
    hands_results = models['hands'].process(frame_rgb)
    
    # Initialize empty landmarks
    frame_landmarks = []
    
    # Process pose landmarks
    for landmark_set, indices in [(pose_results.pose_landmarks, FACE_LANDMARK_INDICES + SHOULDER_INDICES)]:
        if landmark_set:
            for i in indices:
                lm = landmark_set.landmark[i]
                frame_landmarks.extend([lm.x, lm.y, lm.z])
        else:
            frame_landmarks.extend([0] * (len(indices) * 3))
    
    # Process hands
    for hand_type in ['left', 'right']:
        hand_found = False
        if hands_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(hands_results.multi_hand_landmarks, 
                                                hands_results.multi_handedness):
                if handedness.classification[0].label.lower() == hand_type:
                    for lm in hand_landmarks.landmark:
                        frame_landmarks.extend([lm.x, lm.y, lm.z])
                    hand_found = True
                    break
        if not hand_found:
            frame_landmarks.extend([0] * (HAND_LANDMARKS * 3))
    
    return frame_landmarks

def process_single_video(video_info):
    """Process one video file"""
    video_path = video_info['path']
    video_id = video_info['id']
    class_label = video_info['class']
    output_dir = video_info.get('output_dir', 'output_landmarks')
    
    try:
        # Initialize models for this process
        models = init_models()
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        data = []
        frame_num = 0
        
        with tqdm(total=frame_count, desc=f"Processing {video_id}", unit='frame') as pbar:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_landmarks = process_video_frame((frame_rgb, models))
                
                # Add metadata and store
                data.append([video_id, class_label, frame_num] + frame_landmarks)
                frame_num += 1
                pbar.update(1)
                
                # Optional: Skip frames for faster processing
                # if fps > 30:  # If high FPS, process every 2nd frame
                #     cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num + 1)
        
        cap.release()
        
        # Prepare headers
        face_headers = [f"Face_LM_{i}_{axis}" for i in range(11) for axis in ['x', 'y', 'z']]
        shoulder_headers = [f"Shoulder_LM_{i}_{axis}" for i in range(2) for axis in ['x', 'y', 'z']]
        hand_headers = [f"{hand}_LM_{i}_{axis}" 
                       for hand in ['LH', 'RH'] 
                       for i in range(21) 
                       for axis in ['x', 'y', 'z']]
        
        columns = ["video_id", "class", "frame"] + face_headers + shoulder_headers + hand_headers
        
        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{video_id}_landmarks.csv")
        pd.DataFrame(data, columns=columns).to_csv(output_path, index=False)
        
        return {
            'status': 'success',
            'video_id': video_id,
            'output_path': output_path,
            'frames_processed': frame_num
        }
        
    except Exception as e:
        logging.error(f"Error processing {video_id}: {str(e)}")
        return {
            'status': 'failed',
            'video_id': video_id,
            'error': str(e)
        }
    finally:
        # Clean up models
        if 'models' in locals():
            models['pose'].close()
            models['hands'].close()

def process_video_batch(video_info_list, parallel=True):
    """Process multiple videos with optional parallel processing"""
    start_time = time.time()
    
    if parallel:
        # Use 75% of available CPUs
        num_processes = max(1, int(cpu_count() * 0.75))
        with Pool(processes=num_processes) as pool:
            results = list(tqdm(pool.imap(process_single_video, video_info_list),
                           total=len(video_info_list),
                           desc="Overall Progress"))
    else:
        results = []
        for video_info in tqdm(video_info_list, desc="Processing Videos"):
            results.append(process_single_video(video_info))
    
    # Generate summary report
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count
    
    logging.info(f"\nProcessing Complete!\n"
                f"Total Videos: {len(results)}\n"
                f"Success: {success_count}\n"
                f"Failed: {failed_count}\n"
                f"Time Taken: {time.time() - start_time:.2f} seconds")
    
    # Save failure report if any
    if failed_count > 0:
        failure_report = os.path.join(video_info_list[0].get('output_dir', 'output_landmarks'), 
                                    "processing_errors.csv")
        pd.DataFrame([r for r in results if r['status'] == 'failed']).to_csv(failure_report)
        logging.info(f"Failure report saved to {failure_report}")
    
    return results

"""
inpur format:

video_info_list = [
    {
        'path': 'data/video1.mp4',
        'id': 'video001',
        'class': 'hello',
        'output_dir': 'output/landmarks'  # optional
    },
    {
        'path': 'data/video2.mp4',
        'id': 'video002',
        'class': 'goodbye'
    },
    # Add more videos...
]

"""
# For parallel processing (recommended for many videos)
results = process_video_batch(video_info_list, parallel=True)

# For serial processing (debugging)
# results = process_video_batch(video_info_list, parallel=False)