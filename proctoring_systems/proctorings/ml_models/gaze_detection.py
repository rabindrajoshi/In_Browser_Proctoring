import cv2
import numpy as np
import dlib


# Load the pre-trained face detector and shape predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(
    "shape_predictor_model/shape_predictor_68_face_landmarks.dat"
)


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open video device")
else:
    print("Webcam initialized")


# Font I'll use to display the gaze direction
font = cv2.FONT_HERSHEY_PLAIN

# Define the points for the left and right eyes
left_eye_points = [36, 37, 38, 39, 40, 41]
right_eye_points = [42, 43, 44, 45, 46, 47]


# Get gaze ratio and eye mask
def get_gaze_ratio(eye_points, facial_landmarks, gray, frame):
    eye_region = np.array(
        [
            (
                facial_landmarks.part(eye_points[0]).x,
                facial_landmarks.part(eye_points[0]).y,
            ),
            (
                facial_landmarks.part(eye_points[1]).x,
                facial_landmarks.part(eye_points[1]).y,
            ),
            (
                facial_landmarks.part(eye_points[2]).x,
                facial_landmarks.part(eye_points[2]).y,
            ),
            (
                facial_landmarks.part(eye_points[3]).x,
                facial_landmarks.part(eye_points[3]).y,
            ),
            (
                facial_landmarks.part(eye_points[4]).x,
                facial_landmarks.part(eye_points[4]).y,
            ),
            (
                facial_landmarks.part(eye_points[5]).x,
                facial_landmarks.part(eye_points[5]).y,
            ),
        ],
        np.int32,
    )

    height, width, _ = frame.shape
    mask = np.zeros((height, width), np.uint8)
    cv2.polylines(mask, [eye_region], True, 255, 2)
    cv2.fillPoly(mask, [eye_region], 255)
    eye = cv2.bitwise_and(gray, gray, mask=mask)

    min_x = np.min(eye_region[:, 0])
    max_x = np.max(eye_region[:, 0])
    min_y = np.min(eye_region[:, 1])
    max_y = np.max(eye_region[:, 1])

    gray_eye = eye[min_y:max_y, min_x:max_x]
    _, threshold_eye = cv2.threshold(gray_eye, 70, 255, cv2.THRESH_BINARY)
    height, width = threshold_eye.shape

    left_side_threshold = threshold_eye[0:height, 0 : int(width / 2)]
    left_side_white = cv2.countNonZero(left_side_threshold)

    right_side_threshold = threshold_eye[0:height, int(width / 2) : width]
    right_side_white = cv2.countNonZero(right_side_threshold)

    if left_side_white == 0:
        gaze_ratio = 1
    elif right_side_white == 0:
        gaze_ratio = 5
    else:
        gaze_ratio = left_side_white / right_side_white

    # Find the pupil (centroid of the white region in thresholded eye)
    moments = cv2.moments(threshold_eye)
    if moments["m00"] != 0:
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
    else:
        cx, cy = width // 2, height // 2

    pupil_pos = (min_x + cx, min_y + cy)

    # Draw the red dot on the pupil position
    cv2.circle(frame, pupil_pos, 3, (0, 0, 255), 2)

    return gaze_ratio, gray_eye


def gaze_detection(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    for face in faces:
        # Extract the bounding box coordinates for each face
        x, y, w, h = face.left(), face.top(), face.width(), face.height()
        # Draw bounding box around the face
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        landmarks = predictor(gray, face)

        left_gaze_ratio, left_eye_mask = get_gaze_ratio(
            left_eye_points, landmarks, gray, frame
        )
        right_gaze_ratio, right_eye_mask = get_gaze_ratio(
            right_eye_points, landmarks, gray, frame
        )
        gaze_ratio = (left_gaze_ratio + right_gaze_ratio) / 2

        if gaze_ratio <= 1:
            cv2.putText(frame, "Eye Gaze: RIGHT", (50, 100), font, 2, (0, 0, 255), 3)
        elif 1 < gaze_ratio < 1.3:
            cv2.putText(frame, "Eye Gaze: CENTER", (50, 100), font, 2, (0, 0, 255), 3)
        else:
            cv2.putText(frame, "Eye Gaze: LEFT", (50, 100), font, 2, (0, 0, 255), 3)

        # Resize eye masks to the same size
        left_eye_mask_resized = cv2.resize(left_eye_mask, (100, 50))
        right_eye_mask_resized = cv2.resize(right_eye_mask, (100, 50))

        # Concatenate both eye masks horizontally
        combined_eye_mask = np.hstack((left_eye_mask_resized, right_eye_mask_resized))

        # Display the combined eye mask
        # cv2.imshow("Eye Masks", combined_eye_mask)

    cv2.imshow("Frame", frame)
