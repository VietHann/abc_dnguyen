# GUARDIAN - Violence Detection Web Interface

Cyberpunk-styled surveillance dashboard for the YOLOv8 Violence Detection System.

## Quick Start

### Option 1: Standalone Demo (No Backend)
Simply open `index.html` in your browser. The dashboard runs in demo mode with simulated detections.

### Option 2: Full Backend (Recommended)
```bash
cd web
pip install -r requirements.txt
python app.py
```
Then open http://localhost:5000

## Features

### Dashboard
- **Live Stats**: Real-time counters for frames, violence events, detection rate, and uptime
- **Camera Feed**: Webcam integration with detection overlay
- **Detection Log**: Scrolling list of detection events with timestamps and confidence scores
- **Control Panel**: Confidence threshold, class toggles, and simulation controls

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve dashboard |
| `/api/status` | GET | System status and health |
| `/api/detect` | POST | Upload image/video for detection |
| `/api/stats` | GET | Detection statistics |
| `/api/reset-stats` | POST | Reset statistics |

### POST /api/detect

Upload an image or video for violence detection.

**Request:**
```
POST /api/detect
Content-Type: multipart/form-data

file: <image or video file>
```

**Response:**
```json
{
  "success": true,
  "filename": "example.jpg",
  "file_type": "image",
  "detections": [
    {
      "class": "person",
      "confidence": 0.95,
      "bbox": [100, 50, 300, 450],
      "class_id": 0
    },
    {
      "class": "violence",
      "confidence": 0.87,
      "bbox": [400, 100, 600, 500],
      "class_id": 1
    }
  ],
  "total_objects": 2,
  "violence_count": 1,
  "person_count": 1,
  "processing_time": 0.234
}
```

### Demo Mode
When `ultralytics` is not installed or the model is unavailable, the system falls back to mock detection with realistic random results.

## Project Structure

```
web/
├── index.html      # Main dashboard (standalone HTML)
├── app.py          # Flask backend server
├── requirements.txt
└── README.md       # This file
```

## System Requirements

- Python 3.8+
- Web browser with ES6+ support (Chrome, Firefox, Edge, Safari)
- Optional: Webcam for live detection

## Configuration

### Confidence Threshold
Adjust the minimum confidence score for detections (0.1 - 0.9). Higher values = fewer but more confident detections.

### Detection Classes
Toggle detection for:
- **Person**: Standard person detection
- **Violence**: Violence/aggression detection

### Simulation
Use the simulation mode to see the dashboard in action with mock data flowing through.

## Technical Details

- **Frontend**: Vanilla HTML/CSS/JS (no build step)
- **Backend**: Flask with CORS support
- **Model**: YOLOv8 (loads from `runs/detect/train/weights/best.pt` or falls back to `yolov8n.pt`)
- **Supported Formats**: JPG, PNG (images); MP4, AVI, MOV (videos)
- **Max File Size**: 500MB

## Troubleshooting

### "Camera Unavailable"
- Grant camera permissions in browser
- Ensure no other application is using the webcam

### "Backend Offline"
- Install requirements: `pip install -r requirements.txt`
- Check if port 5000 is available
- Run `python app.py` from the `web/` directory

### Model Not Loading
- Ensure YOLOv8 is installed: `pip install ultralytics`
- Train a model following the main project instructions
- Place trained weights at `runs/detect/train/weights/best.pt`

---

**GUARDIAN v2.4.1** | YOLOv8 Violence Detection System
