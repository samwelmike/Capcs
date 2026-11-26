import logging
import sqlite3
from datetime import datetime

import cv2
from ultralytics import YOLO
from ultralytics.utils import LOGGER

LOGGER.setLevel(logging.ERROR)

# Configuration: use a video filename, 0 for webcam, or an RTSP stream URL
VIDEO_SOURCE = "people-detection.mp4"
COUNT_LINE_Y = 240
DEAD_ZONE = 15
INVERT_DIRECTION = False  # Set to True if moving upward counts as entering

db = sqlite3.connect("church_attendance.db")
db.execute(
    """
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        in_count INTEGER,
        out_count INTEGER,
        current_inside INTEGER
    )
    """
)

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    print(f"Could not open video or camera source: '{VIDEO_SOURCE}'. Check the path or device.")
    raise SystemExit

entered_count = 0
exited_count = 0
last_position = {}

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.resize(frame, (640, 480))
    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.4,
        tracker="bytetrack.yaml",
        verbose=False,
    )[0]

    cv2.line(frame, (0, COUNT_LINE_Y), (640, COUNT_LINE_Y), (0, 255, 0), 2)

    if results.boxes.id is not None:
        boxes = results.boxes.xyxy.cpu().numpy()
        track_ids = results.boxes.id.int().cpu().numpy()

        for (x1, y1, x2, y2), track_id in zip(boxes, track_ids):
            center_y = int((y1 + y2) / 2)

            if center_y < COUNT_LINE_Y - DEAD_ZONE:
                side = -1
            elif center_y > COUNT_LINE_Y + DEAD_ZONE:
                side = 1
            else:
                side = 0

            if side != 0:
                previous_side = last_position.get(track_id)
                if previous_side is not None and previous_side != side:
                    moving_down = side == 1
                    if moving_down != INVERT_DIRECTION:
                        entered_count += 1
                    else:
                        exited_count += 1

                    current_inside = max(0, entered_count - exited_count)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    db.execute(
                        """
                        INSERT INTO attendance_logs (timestamp, in_count, out_count, current_inside)
                        VALUES (?, ?, ?, ?)
                        """,
                        (timestamp, entered_count, exited_count, current_inside),
                    )
                    db.commit()

                last_position[track_id] = side

            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)

    inside_now = max(0, entered_count - exited_count)
    status_text = f"Inside: {inside_now}  IN: {entered_count}  OUT: {exited_count}"
    cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("AIC Chang'ombe Door Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

print(f"Total entered: {entered_count}, Total exited: {exited_count}")
cap.release()
cv2.destroyAllWindows()
db.close()