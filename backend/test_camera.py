import cv2
import sys

def test_camera(device_id=0):
    print(f"Testing camera {device_id}...")
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        print(f"Failed to open camera {device_id}")
        return False
    
    ret, frame = cap.read()
    if not ret:
        print(f"Failed to read from camera {device_id}")
        cap.release()
        return False
    
    print(f"Success! Frame shape: {frame.shape}")
    cap.release()
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_camera(int(sys.argv[1]))
    else:
        test_camera(0)
