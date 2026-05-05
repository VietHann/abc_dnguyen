# Phat Hien Dan Chien

Du an phat hien dan chien / bat chuong su dung YOLOv8 (nano va small) nhan dien hanh dong bao luc trong video va anh.

## Model

- `best.pt` - Model YOLOv8 duoc train san
- `Yolo_nano_weights.pt` - YOLOv8-nano
- `yolo_small_weights.pt` - YOLOv8-small

## Cai Dat

Tao moi truong ao:
```bash
python -m venv venv
```

Kich hoat moi truong:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

Cai dat thu vien:
```bash
pip install -r requirements.txt
```

## Su Dung

### webcam (phan tich thoi gian thuc)
```bash
python detect.py --source 0 --weights best.pt
```

### Video
```bash
python detect.py --source video.mp4 --weights best.pt --save
```

### Anh
```bash
python detect.py --source image.jpg --weights best.pt --save
```

## Tham So

| Tham so | Mac dinh | Mo ta |
|---------|----------|-------|
| `--weights` | `best.pt` | Duong dan file model |
| `--source` | `0` | Camera / video / anh |
| `--class` | `1` | Lop can nhan dien (1 = Violence) |
| `--conf` | `0.5` | Nguong chung min |
| `--save` | - | Luu anh/video da ghi nhan |
| `--save-txt` | - | Luu ket qua ra file .txt |
| `--realtime` | - | Hien thi khung hinh webcam |
| `--view-fps` | - | Hien thi FPS tren man hinh |
