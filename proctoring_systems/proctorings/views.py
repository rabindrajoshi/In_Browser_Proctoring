from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.utils import timezone
from django.http import HttpResponse
import requests
import threading
import cv2
import os
import time
import numpy as np
from datetime import datetime

from .models import CheatingLog, FormResponse  # Assuming you have these models
from proctorings.ml_models.audio_detection import audio_detection
from proctorings.ml_models.facial_detections import detectFace
from proctorings.ml_models.object_detections import detectObject
from proctorings.ml_models.head_pose_estimation import head_pose_detection
from proctorings.ml_models.gaze_detection import gaze_detection
from .google_sheets import get_sheet_data  # Assuming this is for retrieving data


# Log file path
log_file_path = os.path.join('logs', 'activity_log.txt')
if not os.path.exists('logs'):
    os.makedirs('logs')

def log_activity(activity):
    """Log activities to a specified log file."""
    with open(log_file_path, 'a') as file:
        file.write(str(activity) + '\n')

def convert_drive_link_to_direct_download(drive_url):
    """Convert a Google Drive share link to a direct download link."""
    if 'drive.google.com' in drive_url:
        if 'id=' in drive_url:
            file_id = drive_url.split('id=')[1]
        elif '/d/' in drive_url:
            file_id = drive_url.split('/d/')[1].split('/')[0]
        else:
            print("Invalid Google Drive link format.")
            return None
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    return None

def save_sheet_data_to_model(data):
    """Save data from Google Sheets to the FormResponse model."""
    FormResponse.objects.all().delete()  # Clear existing records
    for index, row in enumerate(data):
        if index == 0 or len(row) < 6:
            continue  # Skip header and invalid rows

        try:
            timestamp = timezone.make_aware(datetime.strptime(row[0], '%m/%d/%Y %H:%M:%S'))

            if not FormResponse.objects.filter(email=row[3]).exists():
                # Handle photo upload
                photo_url = row[4]
                photo_path = handle_file_upload(photo_url, row[1], 'photos', 'jpg')

                # Handle CV upload
                cv_url = row[5]
                cv_path = handle_file_upload(cv_url, row[1], 'cvs', 'pdf')

                # Create FormResponse instance
                form_response = FormResponse(
                    timestamp=timestamp,
                    name=row[1],
                    address=row[2],
                    email=row[3],
                    photo=photo_path,
                    cv=cv_path,
                    feedback=row[6] if len(row) > 6 else None,
                )
                form_response.save()
                create_user_from_form_response(row)
            else:
                print(f"Entry for {row[3]} already exists, skipping.")

        except ValueError as e:
            print(f"Error parsing row {row}: {e}")
        except IntegrityError as e:
            print(f"Error saving row {row}: {e}")

def handle_file_upload(url, name, folder, extension):
    """Download and save a file from a given URL."""
    if url:
        direct_url = convert_drive_link_to_direct_download(url)
        if direct_url:
            file_name = f"{name.replace(' ', '_')}.{extension}"
            file_path = os.path.join(folder, file_name)

            if not default_storage.exists(file_path):
                response = requests.get(direct_url)
                default_storage.save(file_path, ContentFile(response.content))
            return file_path
    return None

def create_user_from_form_response(row):
    """Create a user from form response data."""
    email = row[3]
    if not User.objects.filter(username=email).exists():
        password = email  # Set password to the same as the email
        name = row[1]
        first_name, last_name = (name.split() + [''])[:2]  # Split name into first and last
        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        print(f"User {email} created successfully.")
    else:
        print(f"User with email {email} already exists.")

def index(request):
    """Render the login page and authenticate users."""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'index.html')


def home(request):
    return render(request, 'home.html') 

@login_required(login_url='/')
def exam_page(request):
    """Render the exam page and start the proctoring system."""
    if request.method == 'POST':
        username = request.POST.get('username')  # Assuming username is sent in POST request
        log_file = f"{username}.log"
        report_file = "report.html"

        # Initialize variables
        cap = cv2.VideoCapture(0)  # Open webcam
        cheat_count = 0  # Total cheat count
        consecutive_cheat_events = 0
        alert_threshold = 3
        report_interval = 300  # 5 minutes
        next_report_time = time.time() + report_interval
        real_time_alert = False
        interval_logs = []  # Activity logs within each 5-minute interval

        # Function to log activity
        def log_activity(log_file, activity):
            with open(log_file, 'a') as file:
                file.write(str(activity) + '\n')

        # Function to determine cheating
        def detect_cheating(detected_objects, head_pose, face_count, audio_detected):
            nonlocal cheat_count, consecutive_cheat_events, real_time_alert
            cheated = False
            
            if any(obj in ['cell phone', 'phone', 'book'] for obj, _ in detected_objects):
                cheat_count += 1
                consecutive_cheat_events += 1
                cheated = True
            
            if head_pose in ['left', 'right', 'down']:
                cheat_count += 1
                consecutive_cheat_events += 1
                cheated = True
            
            if face_count > 1:
                cheat_count += 1
                consecutive_cheat_events += 1
                cheated = True
            
            if audio_detected == 'talking':
                cheat_count += 1
                consecutive_cheat_events += 1
                cheated = True
            
            if not cheated:
                consecutive_cheat_events = 0
            
            if consecutive_cheat_events >= alert_threshold:
                real_time_alert = True
            
            return cheated

        # Threaded function for audio detection
        def audio_thread_function():
            while True:
                audio_status = audio_detection()
                print(f"Audio detection status: {audio_status}")
                time.sleep(5)  # Run every 5 seconds

        # Start the audio detection thread
        audio_thread = threading.Thread(target=audio_thread_function)
        audio_thread.daemon = True
        audio_thread.start()

        # Initialize the report structure
        with open(report_file, 'w') as report:
            report.write("<html><head><title>Proctoring Report</title></head><body>")
            report.write(f"<h1>Proctoring Report for {username}</h1>")

        # Function to append logs to the report
        def append_to_report(username, start_time, end_time, interval_logs, cheat_count, report_filename):
            with open(report_filename, 'a') as report:
                report.write(f"<h2>Activity Report for {username} from {start_time} to {end_time}</h2>")
                report.write("<table border='1'><tr><th>Time</th><th>Status</th><th>Details</th></tr>")
                for log in interval_logs:
                    report.write(f"<tr><td>{log['time']}</td><td>{log['status']}</td><td>{log['details']}</td></tr>")
                report.write("</table>")
                report.write(f"<h3>Total Cheat Count in this Interval: {cheat_count}</h3>")
                if real_time_alert:
                    report.write("<h3 style='color:red;'>ALERT: Multiple Consecutive Suspicious Activities Detected</h3>")
                report.write("<hr>")
            interval_logs.clear()  # Clear logs after appending

        # Main detection loop
        start_time = time.time()
        model_interval = 10  # 10 seconds for each model to run
        next_model_time = time.time() + model_interval

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame from camera.")
                break

            current_time_str = datetime.now().strftime("%H:%M:%S")

            # Run models sequentially
            if time.time() >= next_model_time:
                face_count, faces = detectFace(frame)
                head_pose = head_pose_detection(faces, frame) if face_count > 0 else "No head detected."
                detected_objects = detectObject(frame)
                audio_status = 'talking' if 'talking' in detected_objects else 'No suspicious audio detected'
                
                cheating = detect_cheating(detected_objects, head_pose, face_count, audio_status)

                # Log activity
                status = "Cheating Detected" if cheating else "No Cheating Detected"
                activity = {
                    'time': current_time_str,
                    'status': status,
                    'details': f"Face Count: {face_count}, Detected Objects: {detected_objects}, Head Pose: {head_pose}, Audio: {audio_status}"
                }
                interval_logs.append(activity)
                log_activity(log_file, activity)

                # Update next model time
                next_model_time += model_interval

            # Generate report every 5 minutes
            if time.time() >= next_report_time:
                report_end_time = datetime.now().strftime("%H:%M:%S")
                append_to_report(username, start_time, report_end_time, interval_logs, cheat_count, report_file)
                start_time = time.time()  # Reset start time for the next interval
                next_report_time += report_interval

            # Display the frame with annotations
            cv2.imshow('Proctoring System', frame)

            key = cv2.waitKey(1)
            if key == 27:  # Press 'Esc' to exit
                break

        cap.release()
        cv2.destroyAllWindows()

        # Finalize report with closing tags
        with open(report_file, 'a') as report:
            report.write("</body></html>")

        return render(request, 'exam_page.html')

    return render(request, 'exam_page.html')
