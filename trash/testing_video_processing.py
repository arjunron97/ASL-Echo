import cv2
import os
import time


def preview_clip(entry, video_folder, class_num=1):
    """
    Preview a video clip from a JSON entry using OpenCV.

    Args:
        entry (dict): JSON entry containing video and class info
        video_folder (str): Path to folder containing downloaded videos
        class_num (int): Which class to preview (e.g., 1 for class1)
    """
    # Get video path
    video_path = os.path.join(video_folder, f"{entry['link_id']}.mp4")
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return

    # Get class data
    class_key = f"class{class_num}"
    if class_key not in entry:
        print(f"{class_key} not found in entry")
        return

    class_data = entry[class_key]
    start_time = class_data['start_time']
    end_time = class_data['end_time']

    # Open video file
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Calculate frame numbers
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)

    # Set starting position
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # Create window
    window_name = f"{entry['link_id']} - {class_data['name']}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Play the clip
    while cap.isOpened() and cap.get(cv2.CAP_PROP_POS_FRAMES) <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for display if needed
        display_frame = cv2.resize(frame, (640, 360))

        # Show frame
        cv2.imshow(window_name, display_frame)

        # Exit on 'q' press
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()


# Example usage
test_entry = {
    "link": "https://www.youtube.com/watch?v=hCxSiN-vZS8",
    "link_id":  "hCxSiN-vZS8",
    "class1": {
        "name": "happy",
        "start_time": 31.767,
        "end_time": 34.033,
        # ... other fields ...
    }
}

# Assuming videos are in a 'videos' folder
preview_clip(test_entry, video_folder="videos", class_num=1)