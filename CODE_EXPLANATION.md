# Giai Thich Chi Tiet Du An Phat Hien Dan Chien

Du an su dung YOLOv8 (You Only Look Once) de nhan dien hanh dong bao luc (violence/fight) trong video va anh. Dưới đây là giải thích chi tiết từng phần.

---

## 1. Cau Truc Thu Muc

```
Fight-Violence-detection-yolov8/
├── detect.py              # File chinh - chuong trinh nhan dien
├── best.pt                # Model YOLOv8 da train san (chinh)
├── Yolo_nano_weights.pt   # Model YOLOv8-nano
├── yolo_small_weights.pt  # Model YOLOv8-small
├── requirements.txt       # Danh sach thu vien can cai dat
├── README.md              # Huong dan su dung
├── .gitignore             # Loai bo file khong can thiet khoi git
└── venv/                  # Moi truong ao Python (khong push len git)
```

---

## 2. Phan Tich detect.py

### 2.1. Cac Thu Vien Su Dung

```python
import argparse      # Xu ly tham so dong lenh
import os            # Lam viec voi he thong file
import time          # Tinh thoi gian (FPS)
from pathlib import Path
import cv2           # OpenCV - xu ly anh/video
from ultralytics import YOLO  # Thu vien YOLOv8
```

- **cv2 (OpenCV)**: Thu vien xu ly anh va video, ve bounding box, hien thi khung hinh.
- **ultralytics**: Thu vien YOLOv8, load model va chay nhan dien.

### 2.2. Ham parse_args() - Dinh Nghia Tham So

Ham nay dinh nghia cac tham so nguoi dung truyen vao khi chay script:

| Tham so | Kieu | Mac dinh | Mo ta |
|---------|------|----------|-------|
| `--weights` | str | `best.pt` | Duong dan file model |
| `--source` | str | `0` | Camera / video / anh |
| `--class` | int | `1` | Lop nhan dien (1=Violence) |
| `--save-txt` | flag | False | Luu ket qua ra file .txt |
| `--save` | flag | False | Luu anh/video da danh dau |
| `--conf` | float | `0.5` | Nguong chinh xac (confidence) |
| `--imgsz` | int | `640` | Kich thuoc anh dau vao |
| `--view-fps` | flag | False | Hien thi FPS |
| `--realtime` | flag | False | Chay webcam thoi gian thuc |

**Vi du cach su dung:**
```bash
python detect.py --source 0 --weights best.pt --conf 0.6
```
-> Chay webcam, dung model best.pt, nguong chinh xac 60%.

### 2.3. Ham main() - Diem Bat Dau

```python
def main():
    args = parse_args()

    # Buoc 1: Kiem tra file model co ton tai khong
    if not os.path.exists(args.weights):
        print(f"Error: Weights file not found: {args.weights}")
        return

    # Buoc 2: Load model YOLOv8
    model = YOLO(args.weights)

    # Buoc 3: Xac dinh nguon dau vao
    source_input = args.source

    # Neu la so -> la camera (0 = webcam mac dinh)
    if source_input.isdigit():
        camera_index = int(source_input)
        run_realtime(model, args, camera_index)
        return

    # Kiem tra file co ton tai khong
    if not os.path.exists(source_input):
        print(f"Error: Source not found: {source_input}")
        return

    # Buoc 4: Phan biet anh hay video
    source_path = Path(source_input)
    if source_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        run_image(model, args, source_input)
    else:
        run_video(model, args, source_input)
```

**Luong xu ly cua main():**

```
Nhap tham so
     │
     v
File model co ton tai?
     │
     ├── Khong -> Thoat, bao loi
     │
     v (Co)
Load model YOLOv8
     │
     v
source la gi?
     │
     ├── So (0, 1, 2...) -> Chay webcam (run_realtime)
     │
     ├── Duong dan file anh (.jpg, .png...) -> run_image()
     │
     └── Duong dan file video (.mp4...) -> run_video()
```

### 2.4. Ham run_realtime() - Phan Tich Webcam

Day la ham quan trong nhat, xu ly video tu camera theo thoi gian thuc.

```python
def run_realtime(model, args, camera_index=0):
    cap = cv2.VideoCapture(camera_index)
```

**Mo camera:**
- `cv2.VideoCapture(0)` mo camera mac dinh (webcam).
- Neu la so khac (1, 2...) thi mo camera tuong ung.

**Vong lap chinh (while True):**

```python
while True:
    ret, frame = cap.read()  # Doc frame tu camera
```

**Tinh FPS:**
```python
frame_count += 1
elapsed = time.time() - start_time
if elapsed > 0:
    fps = frame_count / elapsed  # So frame moi giay
```

**Chay model nhan dien:**
```python
results = model.predict(
    source=frame,              # Frame hien tai
    classes=[violence_class, 0], # Lop 1 (Violence) va lop 0 (Person)
    conf=args.conf,            # Nguong chinh xac
    imgsz=args.imgsz,          # Kich thuoc anh
    verbose=False,             # Tat thong bao
)
```

**Xu ly tung bounding box:**

```python
for box in boxes:
    cls_id = int(box.cls[0])       # Lay ID lop
    conf = float(box.conf[0])       # Lay diem chinh xac
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())  # Toa do bbox

    # Tinh dien tich bbox
    box_w = x2 - x1
    box_h = y2 - y1
    area = box_w * box_h
    frame_area = frame.shape[0] * frame.shape[1]

    # Loai bo bbox qua nho (nho hon 0.5% dien tich khung hinh)
    if area < frame_area * 0.005:
        continue
```

**Ve bounding box va nhan:**

```python
if cls_id == violence_class:  # Lop 1 = Violence
    color = (0, 0, 255)       # Do - bao luc
    label = f"VIOLENCE {conf:.2f}"
    thickness = 3
else:                         # Lop 0 = Person
    color = (0, 255, 0)       # Xanh la - nguoi
    label = f"Person {conf:.2f}"
    thickness = 2

# Ve hinh chu nhat
cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

# Ve nen cho nhan (mau trung voi mau box)
cv2.rectangle(frame, (x1, y1 - label_h - 8), (x1 + label_w, y1), color, -1)

# Ve chu nhan tren nen
cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
```

**Hien thi FPS tren man hinh:**
```python
cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
```

**Co che xac nhan bao luc (chong bao dong gia):**

```python
violence_frames = 0
CONFIRM_THRESHOLD = 5

# Neu phat hien bao luc -> tang bien dem
if has_violence:
    violence_frames += 1
else:
    violence_frames = 0

# Chi bao dong khi phat hien lien tuc 5 frame
if violence_frames >= CONFIRM_THRESHOLD:
    cv2.putText(frame, "VIOLENCE DETECTED!", ...)
    print(f"[!] Violence detected | FPS: {fps:.1f}")
```

**Tai sao can co che nay?**
- Tranh bao dong gia (nhieu false positive).
- Chi bao khi phat hien bao luc lien tuc trong 5 frame (~0.2 giay neu 25fps).

**Hien thi va thoat:**
```python
cv2.imshow("Violence Detection", frame)  # Hien thi khung hinh

if cv2.waitKey(1) & 0xFF == ord("q"):   # Bam 'q' de thoat
    break
```

**Giai phong tai nguyen:**
```python
cap.release()           # Dong camera
cv2.destroyAllWindows() # Dong cua so hien thi
```

### 2.5. Ham run_image() - Phan Tich Anh Don

```python
def run_image(model, args, source):
    results = model.predict(
        source=source,
        classes=[args.class_id],
        conf=args.conf,
        imgsz=args.imgsz,
        save=args.save,          # Luu anh da danh dau
        save_txt=args.save_txt,  # Luu ket qua ra .txt
        project="runs/detect",
        name="exp",
        exist_ok=True,
    )
    print_results(results, source, args.class_id)
```

- Su khac biet voi `run_realtime`: khong ve thu cong bounding box, thay vi do ultrtralytics tu dong luu anh da danh dau.
- Ket qua duoc luu vao thu muc `runs/detect/exp/`.

### 2.6. Ham run_video() - Phan Tich Video

```python
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
```

- Giong `run_image()`, khac o cho `source` la file video.
- Ultralytics tu dong doc tung frame, chay nhan dien, va ghi video da danh dau.

### 2.7. Ham print_results() - In Ket Qua

```python
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
```

In ra man hinh:
- So luong phat hien
- Diem chinh xac (confidence) cua tung phat hien
- Toa do bounding box [x1, y1, x2, y2]

---

## 3. Phan Tich Cac File Khac

### 3.1. requirements.txt

```
ultralytics>=8.0.0   # Thu vien YOLOv8
opencv-python>=4.8.0 # Xu ly anh/video
numpy>=1.24.0        # Xu ly mang (phu thuoc cua ultralytics)
```

### 3.2. .gitignore

```
venv/           # Thu muc moi truong ao
__pycache__/    # File bytecode Python
*.pyc           # File .py da bien dich
```

### 3.3. testing_code.ipynb

Day la file Jupyter Notebook su dung tren Kaggle de thu nghiem model. No chua:
- Huong dan cai dat ultralytics
- Vi du nhan dien voi YOLOv8
- Code phan tich video (giong voi `detect.py` nhung viet cho Kaggle)

---

## 4. Hai Lop Trong Model

Model YOLOv8 duoc train voi 2 lop:

| Lop ID | Ten | Mau bounding box |
|--------|-----|------------------|
| 0 | Person | Xanh la (0, 255, 0) |
| 1 | Violence | Do (0, 0, 255) |

Khi chay nhan dien:
- Lop 0 (Person): Nhan dien nguoi trong khung hinh
- Lop 1 (Violence): Nhan dien hanh dong bao luc

---

## 5. Cach Hoat Dong Chi Tiet

### 5.1. Khi Nhap Video/Anh (run_image / run_video)

```
Nguoi dung truyen video/anh
         │
         v
Kiem tra file ton tai
         │
         v
Load model YOLOv8 tu file .pt
         │
         v
Ultralytics tu dong:
  1. Doc tung frame (neu la video) hoac doc anh
  2. Resize ve kich thuoc imgsz (640x640 mac dinh)
  3. Chay model nhan dien
  4. Tra ve danh sach bounding box
         │
         v
Luu anh/video da danh dau (neu --save)
Luu file .txt chua ket qua (neu --save-txt)
         │
         v
In ket qua ra man hinh
```

### 5.2. Khi Chay Webcam (run_realtime)

```
Mo camera (cv2.VideoCapture)
         │
         v
Vong lap vo han:
  1. Doc frame tu camera
  2. Chay model nhan dien (YOLOv8)
  3. Xu ly tung bounding box:
     - Tinh dien tich
     - Loai bo bbox qua nho
     - Ve bounding box + nhan
  4. Hien thi FPS
  5. Kiem tra nguong xac nhan bao luc
  6. Hien thi "VIOLENCE DETECTED!" neu can
  7. Hien thi khung hinh
  8. Cho phim 'q' de thoat
         │
         v
Giai phong camera va dong cua so
```

---

## 6. Chu Y Quan Trong

### 6.1. Nguong Chinh Xac (Confidence Threshold)

Tham so `--conf` mac dinh la 0.5 (50%):
- Gia tri cao hon (0.7, 0.8) -> It phat hien hon nhung chinh xac hon.
- Gia tri thap hon (0.3, 0.4) -> Nhieu phat hien hon nhung co the co false positive.

### 6.2. Co Che Chong Bao Dong Gia

`CONFIRM_THRESHOLD = 5` nghia la:
- Chi bao khi phat hien bao luc lien tuc trong 5 frame.
- Tranh truong hop model nhan sai 1-2 frame nham lan.

### 6.3. Loc Bounding Box Nho

```python
if area < frame_area * 0.005:
    continue
```

Loai bo cac bbox co dien tich nho hon 0.5% khung hinh, tranh phat hien nham vao nhieu vat.

---

## 7. So Sanh 3 File Model

| File | Kich thuoc | Toc do | Do chinh xac |
|------|-----------|--------|--------------|
| `best.pt` | ~6MB | Nhanh (nano) | Cao (da train tot) |
| `Yolo_nano_weights.pt` | ~6MB | Nhanh nhat | Trung binh |
| `yolo_small_weights.pt` | ~22MB | Cham hon | Cao hon |

**KHUYEN NGHI:** Dung `best.pt` vi da duoc train tot nhat.
