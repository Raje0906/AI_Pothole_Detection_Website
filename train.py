import os
from ultralytics import YOLO

# Define the path to the dataset YAML file
dataset_path = os.path.abspath("dataset/pothole.yaml")  # data parameter

# Load YOLO model
model = YOLO("yolov8n.pt")  # Specify the YOLO model you are using, e.g., yolov8n.pt

# Train model
model.train(
    data=dataset_path,  # Path to the dataset YAML file
    epochs=10,  # Number of training epochs
    batch=16,  # Batch size
    imgsz=640  # Image size
)
