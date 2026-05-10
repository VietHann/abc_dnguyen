"""
GUARDIAN - Violence Detection System Backend
Flask server that wraps YOLOv8 violence detection model.
"""

import os
import base64
import uuid
import time
import json
import numpy as np
import cv2
import requests
from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Blockchain service URL
BLOCKCHAIN_SERVICE_URL = os.environ.get('BLOCKCHAIN_SERVICE_URL', 'http://localhost:5001')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
ALLOWED_VIDEO = {'mp4', 'avi', 'mov', 'mkv'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# YOLO Model (lazy loaded)
_model = None
_model_loaded = False


def get_model():
    """Lazy load the YOLO model, matching detect.py behavior."""
    global _model, _model_loaded
    if _model is not None:
        return _model

    try:
        from ultralytics import YOLO
        # Match detect.py: default="best.pt" at project root
        model_paths = [
            os.path.join(PROJECT_ROOT, 'best.pt'),
            os.path.join(PROJECT_ROOT, 'runs', 'detect', 'train', 'weights', 'best.pt'),
        ]
        for path in model_paths:
            if os.path.exists(path):
                _model = YOLO(path)
                _model_loaded = True
                print(f"[MODEL] Loaded from: {path}")
                return _model

        print("[MODEL] No trained model found. Using yolov8n.pt for demo.")
        _model = YOLO('yolov8n.pt')
        _model_loaded = True
        return _model
    except ImportError:
        print("[MODEL] ultralytics not installed.")
        _model_loaded = False
        return None


def run_detection(model, frame, conf=0.5, imgsz=640):
    """
    Run YOLO detection on a frame, matching detect.py logic:
    - class 0 = person
    - class 1 = violence
    - Filter tiny boxes (area < 0.5% of frame)
    - Return detections with bbox, confidence, class
    """
    results = model.predict(
        source=frame,
        classes=[0, 1],
        conf=conf,
        imgsz=imgsz,
        verbose=False,
    )

    detections = []
    result = results[0]
    boxes = result.boxes

    if boxes is None:
        return detections

    frame_h, frame_w = frame.shape[:2]
    frame_area = frame_h * frame_w

    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf_val = float(box.conf[0])
        cls_id = int(box.cls[0])

        box_w = x2 - x1
        box_h = y2 - y1
        area = box_w * box_h

        # Filter tiny boxes (same as detect.py: area < frame_area * 0.005)
        if area < frame_area * 0.005:
            continue

        class_name = 'person' if cls_id == 0 else 'violence'

        detections.append({
            'class': class_name,
            'class_id': cls_id,
            'confidence': round(conf_val, 4),
            'bbox': [int(x1), int(y1), int(x2), int(y2)],
        })

    return detections


def draw_boxes(frame, detections):
    """Draw bounding boxes on frame, matching detect.py styling."""
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        conf = det['confidence']
        cls_name = det['class']

        if cls_name == 'violence':
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
            frame, (x1, y1 - label_h - 8), (x1 + label_w, y1), color, -1
        )
        cv2.putText(
            frame, label, (x1, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
        )

    return frame


# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'index.html'))


@app.route('/api/status', methods=['GET'])
def get_status():
    model = get_model()
    uptime = time.time() - system_state['start_time']
    uptime_str = f"{int(uptime // 3600):02d}:{int((uptime % 3600) // 60):02d}:{int(uptime % 60):02d}"

    return jsonify({
        'status': 'online',
        'model': 'YOLOv8 Violence Detection' if _model_loaded else 'Not Loaded',
        'model_loaded': _model_loaded,
        'model_path': str(getattr(_model, 'model_path', 'N/A')) if _model else 'N/A',
        'uptime': uptime_str,
        'uptime_seconds': uptime,
        'total_detections': system_state['total_detections'],
        'violence_detections': system_state['violence_detections'],
        'timestamp': datetime.now().isoformat(),
        'version': '2.5.0',
        'classes': {0: 'person', 1: 'violence'}
    })


@app.route('/api/detect', methods=['POST'])
def detect():
    """
    Detect violence in uploaded image or video file.
    Returns JSON with detection results including bounding boxes.

    Accepts: multipart/form-data with a 'file' field
    Optional: 'conf' parameter for confidence threshold (default 0.5)
    """
    start_time = time.time()

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided. Use multipart/form-data with a "file" field.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    conf = float(request.form.get('conf', 0.5))

    filename = file.filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    is_image = ext in ALLOWED_IMAGE
    is_video = ext in ALLOWED_VIDEO

    if not (is_image or is_video):
        return jsonify({
            'success': False,
            'error': f'Unsupported file type. Allowed: {", ".join(ALLOWED_IMAGE | ALLOWED_VIDEO)}'
        }), 400

    # Save uploaded file
    safe_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
    file.save(filepath)

    model = get_model()

    try:
        if is_image:
            frame = cv2.imread(filepath)
            if frame is None:
                return jsonify({'success': False, 'error': 'Could not read image file'}), 400

            detections = run_detection(model, frame, conf=conf) if model else []
            violence_count = sum(1 for d in detections if d['class'] == 'violence')
            person_count = sum(1 for d in detections if d['class'] == 'person')

            # Draw boxes and encode result image
            result_frame = draw_boxes(frame.copy(), detections)
            _, img_encoded = cv2.imencode('.jpg', result_frame)
            result_img_base64 = base64.b64encode(img_encoded).decode('utf-8')

            system_state['total_detections'] += len(detections)
            system_state['violence_detections'] += violence_count

            return jsonify({
                'success': True,
                'filename': filename,
                'file_type': 'image',
                'detections': detections,
                'total_objects': len(detections),
                'violence_count': violence_count,
                'person_count': person_count,
                'result_image': result_img_base64,
                'processing_time': round(time.time() - start_time, 3),
                'timestamp': datetime.now().isoformat()
            })

        else:  # video
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return jsonify({'success': False, 'error': 'Could not open video file'}), 400

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            all_detections = []
            frame_idx = 0
            violence_events = 0

            # Process every N frames to keep it fast
            step = max(1, int(fps / 2))  # ~2 frames per second of video

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % step == 0:
                    detections = run_detection(model, frame, conf=conf) if model else []
                    violence_count = sum(1 for d in detections if d['class'] == 'violence')

                    if detections:
                        all_detections.append({
                            'frame': frame_idx,
                            'timestamp': round(frame_idx / fps, 2),
                            'detections': detections,
                            'violence_count': violence_count
                        })
                    violence_events += violence_count
                    system_state['total_detections'] += len(detections)
                    system_state['violence_detections'] += violence_count

                frame_idx += 1

            cap.release()

            return jsonify({
                'success': True,
                'filename': filename,
                'file_type': 'video',
                'total_frames': total_frames,
                'processed_frames': frame_idx,
                'fps': round(fps, 1),
                'resolution': f'{width}x{height}',
                'all_detections': all_detections,
                'total_violence_events': violence_events,
                'processing_time': round(time.time() - start_time, 3),
                'timestamp': datetime.now().isoformat()
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        try:
            os.remove(filepath)
        except:
            pass


@app.route('/api/webcam/detect', methods=['POST'])
def webcam_detect():
    """
    Process a single webcam frame through YOLO.
    Accepts: base64 encoded image frame + conf parameter
    Returns: base64 image with drawn boxes + detection results
    """
    start_time = time.time()
    data = request.get_json()

    if not data or 'frame' not in data:
        return jsonify({'success': False, 'error': 'No frame data provided'}), 400

    try:
        conf = float(data.get('conf', 0.5))

        # Decode base64 frame
        img_bytes = base64.b64decode(data['frame'])
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'success': False, 'error': 'Could not decode frame'}), 400

        model = get_model()
        detections = run_detection(model, frame, conf=conf) if model else []

        # Draw boxes
        result_frame = draw_boxes(frame.copy(), detections)

        # Encode result
        _, img_encoded = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        result_img = base64.b64encode(img_encoded).decode('utf-8')

        violence_count = sum(1 for d in detections if d['class'] == 'violence')
        system_state['total_detections'] += len(detections)
        system_state['violence_detections'] += violence_count

        return jsonify({
            'success': True,
            'detections': detections,
            'total_objects': len(detections),
            'violence_count': violence_count,
            'person_count': sum(1 for d in detections if d['class'] == 'person'),
            'result_image': result_img,
            'processing_time': round(time.time() - start_time, 3),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'total_detections': system_state['total_detections'],
        'violence_detections': system_state['violence_detections'],
        'person_detections': system_state['total_detections'] - system_state['violence_detections'],
        'uptime': time.time() - system_state['start_time']
    })


@app.route('/api/reset-stats', methods=['POST'])
def reset_stats():
    system_state['total_detections'] = 0
    system_state['violence_detections'] = 0
    system_state['start_time'] = time.time()
    return jsonify({'success': True, 'message': 'Statistics reset successfully'})


@app.route('/api/evidence/save', methods=['POST'])
def save_evidence():
    """
    Bridge endpoint: nhận base64 file + metadata từ frontend,
    chuyển tiếp sang Node.js blockchain service để upload IPFS + mint chain.
    Kết quả được lưu cục bộ và trả về cho frontend.
    """
    start_time = time.time()
    data = request.get_json()

    if not data or 'frame' not in data:
        return jsonify({'success': False, 'error': 'No frame data provided'}), 400

    try:
        frame_b64 = data['frame']
        filename = data.get('filename', f'incident_{uuid.uuid4().hex[:8]}.jpg')
        event_timestamp = data.get('eventTimestamp', int(time.time()))
        metadata = data.get('metadata', {})

        img_bytes = base64.b64decode(frame_b64)
        mime_type = data.get('mimeType', 'image/jpeg')

        # Lưu file cục bộ trước (backup)
        safe_name = f"evidence_{uuid.uuid4().hex}_{filename}"
        evidence_path = os.path.join(BASE_DIR, 'evidences')
        os.makedirs(evidence_path, exist_ok=True)
        local_path = os.path.join(evidence_path, safe_name)
        with open(local_path, 'wb') as f:
            f.write(img_bytes)

            # Chuyển sang blockchain service
            try:
                resp = requests.post(
                    f'{BLOCKCHAIN_SERVICE_URL}/api/evidence/save',
                    json={
                        'file': frame_b64,
                        'filename': filename,
                        'mimeType': mime_type,
                        'eventTimestamp': event_timestamp,
                        'metadata': metadata,
                    },
                    timeout=60,
                )
                bc_data = resp.json()
                # Blockchain service trả flat: { success, ipfs, blockchain, fileHash, ... }
                ipfs_result = bc_data.get('ipfs', {})
                chain_result = bc_data.get('blockchain', {})
                file_hash = bc_data.get('fileHash', '')
            except requests.exceptions.ConnectionError:
                ipfs_result = {'skipped': True, 'reason': 'Blockchain service unavailable'}
                chain_result = {'skipped': True, 'reason': 'Blockchain service unavailable'}
                file_hash = ''
            except requests.exceptions.Timeout:
                ipfs_result = {'skipped': True, 'reason': 'Blockchain service timeout'}
                chain_result = {'skipped': True, 'reason': 'Blockchain service timeout'}
                file_hash = ''

        return jsonify({
            'success': True,
            'local_path': local_path,
            'file_size': len(img_bytes),
            'file_hash': file_hash,
            'ipfs': ipfs_result,
            'blockchain': chain_result,
            'processing_time': round(time.time() - start_time, 3),
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/evidence/list', methods=['GET'])
def list_evidence():
    """Liệt kê các file bằng chứng đã lưu cục bộ."""
    evidence_path = os.path.join(BASE_DIR, 'evidences')
    os.makedirs(evidence_path, exist_ok=True)
    files = []
    for fname in sorted(os.listdir(evidence_path), reverse=True):
        fpath = os.path.join(evidence_path, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            files.append({
                'filename': fname,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            })
    return jsonify({'success': True, 'total': len(files), 'files': files})


@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 500MB.'}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


# System state
system_state = {
    'start_time': time.time(),
    'total_detections': 0,
    'violence_detections': 0,
}

if __name__ == '__main__':
    print("=" * 50)
    print("GUARDIAN Violence Detection System")
    print("=" * 50)
    print("Starting server...")
    print("Dashboard: http://localhost:5000")
    print("API Status: http://localhost:5000/api/status")
    print("API Detect: POST http://localhost:5000/api/detect")
    print("API Webcam: POST http://localhost:5000/api/webcam/detect")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
