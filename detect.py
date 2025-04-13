import cv2
import torch
from ultralytics import YOLO
import os
from datetime import datetime
import numpy as np
import os

# Define relative path to the model
model_path = os.path.join("runs", "detect", "train", "weights", "best.pt")

# For more reliability, you can base it off the current file's location
base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, "runs", "detect", "train", "weights", "best.pt")

# Global model variable
_model = None

def load_model():
    global _model
    if _model is not None:
        return _model

    print("Starting model loading process...")
    try:
        # Try loading the trained model first
        model_paths = [
            "runs/detect/train/weights/best.pt",  # Local training path
            "best.pt",                            # Root directory
            "yolov8n.pt"                         # Fallback to pretrained
        ]
        
        for model_path in model_paths:
            if os.path.exists(model_path):
                print(f"Loading model from: {model_path}")
                _model = YOLO(model_path)
                print("Model loaded successfully!")
                
                # Print model information
                if hasattr(_model, 'names'):
                    print(f"Model names: {_model.names}")
                print(f"Model task: {_model.task if hasattr(_model, 'task') else 'detect'}")
                return _model
                
        raise FileNotFoundError("No model file found in any of the expected locations")
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        raise
    
# Initialize model
try:
    model = load_model()
except Exception as e:
    print(f"Error loading model: {str(e)}")
    raise e

def ensure_rgb(image):
    """Ensure image is in RGB format."""
    if len(image.shape) == 2:  # Grayscale
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[2] == 4:  # RGBA
        return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
    return image

def detect_potholes(input_path, is_video=False):
    # Get the model instance
    model = load_model()
    """Detect potholes in images or videos."""
    print(f"Starting detection for file: {input_path}")
    
    # Configuration
    CONFIDENCE_THRESHOLD = 0.5  # Confidence threshold
    MIN_AREA_THRESHOLD = 100  # Minimum area for a detection to be considered valid
    
    # Since we're using the default YOLO model, we'll look for relevant objects
    # like potholes, holes, or damage in roads
    RELEVANT_CLASSES = ['pothole', 'hole', 'damage']  # Add any relevant class names
    
    # Ensure input file exists and is readable
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist: {input_path}")
        return None, None
    
    if not os.access(input_path, os.R_OK):
        print(f"Error: Input file is not readable: {input_path}")
        return None, None
    
    # Use the existing static/detections directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    detections_dir = os.path.join(project_root, "static", "detections")
    
    print(f"Using existing detections directory: {detections_dir}")
    
    # Check if detections directory exists
    if not os.path.exists(detections_dir):
        print(f"Error: Detections directory does not exist: {detections_dir}")
        return None, None
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"detection_{timestamp}_{base_filename}"
    output_path = os.path.join(detections_dir, filename)
    
    print(f"Output path: {output_path}")
    
    try:
        if not is_video:
            # Process Image
            print("Processing image...")
            image = cv2.imread(input_path)
            if image is None:
                print(f"Error: Could not read image file: {input_path}")
                return None, None
            
            # Get image dimensions
            img_height, img_width = image.shape[:2]
            
            # Ensure image is in RGB format
            image = ensure_rgb(image)
            
            print("Running detection...")
            try:
                results = model(image, conf=CONFIDENCE_THRESHOLD)
                print(f"Detection completed. Found {len(results[0].boxes)} potential objects")
                
                # Create a copy of the image for output
                output_image = image.copy()
                
                # Draw "No potholes detected" on image if no objects found
                if len(results[0].boxes) == 0:
                    # Add text to the image
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = "No potholes detected"
                    text_size = cv2.getTextSize(text, font, 1, 2)[0]
                    text_x = (img_width - text_size[0]) // 2
                    text_y = (img_height + text_size[1]) // 2
                    
                    # Add semi-transparent background for text
                    cv2.rectangle(output_image, 
                                (text_x - 10, text_y - text_size[1] - 10),
                                (text_x + text_size[0] + 10, text_y + 10),
                                (0, 0, 0), -1)
                    cv2.putText(output_image, text, (text_x, text_y), 
                              font, 1, (255, 255, 255), 2)
                    
                    # Save the image
                    save_path = output_path + '.jpg'
                    cv2.imwrite(save_path, output_image)
                    relative_path = '/static/detections/' + os.path.basename(save_path)
                    return relative_path, []
                
                # Process detections if found
                objects_detected = False
                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None and len(boxes) > 0:
                        for box in boxes:
                            conf = float(box.conf)
                            cls_id = int(box.cls)
                            class_name = CLASS_NAMES[cls_id]
                            
                            # Get box coordinates
                            if box.xyxy is not None and len(box.xyxy) > 0:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                detection_area = (x2 - x1) * (y2 - y1)
                                
                                if conf >= CONFIDENCE_THRESHOLD and detection_area >= MIN_AREA_THRESHOLD:
                                    objects_detected = True
                                    # Draw rectangle and label
                                    cv2.rectangle(output_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                    label = f"{class_name} {conf:.2f}"
                                    cv2.putText(output_image, label, (x1, y1-10), 
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                                    
                                    # Store detection info
                                    detections.append({
                                        'box': [x1, y1, x2, y2],
                                        'confidence': conf,
                                        'class': class_name
                                    })
                
                # Save the image with detections
                save_path = output_path + '.jpg'
                cv2.imwrite(save_path, output_image)
                relative_path = '/static/detections/' + os.path.basename(save_path)
                return relative_path, detections if objects_detected else []
                
            except Exception as e:
                print(f"Error during detection: {str(e)}")
                return None, None
            
        else:
            # Process Video (similar changes for video processing)
            print("Video processing not implemented in test mode")
            return None, None
            
    except Exception as e:
        print(f"Error in detection: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, None
