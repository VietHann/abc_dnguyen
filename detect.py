import argparse
import os
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8 Violence/Fight Detection")
    parser.add_argument(
        "--weights",
        type=str,
        default="best.pt",
        help="Path to model weights file (default: best.pt)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Camera index (int), video path, image path, or dir of images (default: 0 for webcam)",
    )
    parser.add_argument(
        "--class",
        dest="class_id",
        type=int,
        default=1,
        help="Class ID to detect (default: 1 for Violence/Fight)",
    )
    parser.add_argument(
        "--save-txt",
        action="store_true",
        help="Save results to *.txt labels file",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save annotated images/videos with bounding boxes",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="Confidence threshold (default: 0.25)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Inference image size (default: 640)",
    )
    parser.add_argument(
        "--view-fps",
        action="store_true",
        help="Show FPS on frame",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Run real-time webcam detection with visual output window",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.weights):
        print(f"Error: Weights file not found: {args.weights}")
        return

    model = YOLO(args.weights)
    print(f"Model loaded from: {args.weights}")

    source_input = args.source

    if source_input.isdigit():
        camera_index = int(source_input)
        run_realtime(model, args, camera_index)
        return

    if not os.path.exists(source_input):
        print(f"Error: Source not found: {source_input}")
        return

    source_path = Path(source_input)
    if source_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        run_image(model, args, source_input)
    else:
        run_video(model, args, source_input)


def run_realtime(model, args, camera_index=0):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_index}")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cv2.namedWindow("Violence Detection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Violence Detection", w, h)

    print(f"Camera {camera_index} opened. Press 'q' to quit.")

    frame_count = 0
    fps = 0.0
    fps_update_time = time.time()
    fps_frame_count = 0
    violence_class = args.class_id
    violence_frames = 0
    CONFIRM_THRESHOLD = 5

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame from camera.")
            break

        frame_count += 1
        fps_frame_count += 1
        elapsed = time.time() - fps_update_time
        if elapsed >= 1.0:
            fps = fps_frame_count / elapsed
            fps_frame_count = 0
            fps_update_time = time.time()

        results = model.predict(
            source=frame,
            classes=[violence_class, 0],
            conf=args.conf,
            imgsz=args.imgsz,
            verbose=False,
        )

        boxes = results[0].boxes
        has_violence = False

        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])

            area = (x2 - x1) * (y2 - y1)
            frame_area = frame.shape[0] * frame.shape[1]
            if area < frame_area * 0.005:
                continue

            if cls_id == violence_class:
                has_violence = True
                color = (0, 0, 255)
                label = f"VIOLENCE {conf:.2f}"
                thickness = 3
            else:
                color = (0, 255, 0)
                label = f"Person {conf:.2f}"
                thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            (label_w, label_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                frame,
                (x1, y1 - label_h - 8),
                (x1 + label_w, y1),
                color,
                -1,
            )
            cv2.putText(
                frame,
                label,
                (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

        if has_violence:
            violence_frames += 1
        else:
            violence_frames = 0

        if violence_frames >= CONFIRM_THRESHOLD:
            cv2.putText(
                frame,
                "VIOLENCE DETECTED!",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )
            print(f"[!] Violence detected | FPS: {fps:.1f}")

        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
        )

        cv2.imshow("Violence Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Exiting...")
            break

    cap.release()
    cv2.destroyAllWindows()


def run_image(model, args, source):
    results = model.predict(
        source=source,
        classes=[args.class_id],
        conf=args.conf,
        imgsz=args.imgsz,
        save=args.save,
        save_txt=args.save_txt,
        project="runs/detect",
        name="exp",
        exist_ok=True,
    )
    print_results(results, source, args.class_id)


def run_video(model, args, source):
    results = model.predict(
        source=source,
        classes=[args.class_id],
        conf=args.conf,
        imgsz=args.imgsz,
        save=args.save,
        save_txt=args.save_txt,
        project="runs/detect",
        name="exp",
        exist_ok=True,
    )
    print_results(results, source, args.class_id)


def print_results(results, source, class_id):
    for result in results:
        boxes = result.boxes
        violence_count = len(boxes)
        print(f"\nDetection complete for: {source}")
        print(f"Violence/Fight detections (class {class_id}): {violence_count}")
        if violence_count > 0:
            for i, box in enumerate(boxes):
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                print(f"  Detection {i+1}: conf={conf:.4f}, bbox={[round(x) for x in xyxy]}")


if __name__ == "__main__":
    main()
