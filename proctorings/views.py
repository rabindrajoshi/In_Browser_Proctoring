from django.shortcuts import render, redirect
from .google_sheets import get_sheet_data
from django.contrib.auth import authenticate, login
from .models import FormResponse
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError
import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

def index(request):
    if request.method == 'POST':
        # Get login credentials from the form in index.html
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Log the user in
            login(request, user)
            # Redirect to the home page after successful login
            return redirect('home')
        else:
            # If login fails, display an error message
            messages.error(request, 'Invalid email or password.')

    return render(request, 'index.html')

@login_required(login_url='/')
def home(request):
    return render(request, 'home.html')

def convert_drive_link_to_direct_download(drive_url):
    """
    Convert a Google Drive share link to a direct download link.
    """
    if 'drive.google.com' in drive_url:
        if 'id=' in drive_url:
            # Handle URL format: https://drive.google.com/open?id=FILE_ID
            file_id = drive_url.split('id=')[1]
        elif '/d/' in drive_url:
            # Handle URL format: https://drive.google.com/file/d/FILE_ID/view
            file_id = drive_url.split('/d/')[1].split('/')[0]
        else:
            print("Invalid Google Drive link format.")
            return None
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    return None


def save_sheet_data_to_model(data):
    FormResponse.objects.all().delete()  # Clear all existing FormResponse records

    # Skip the header row
    for index, row in enumerate(data):
        if index == 0:  # This is the header row
            continue
        print(f"length: {len(row)}, data: {row}")
        if len(row) < 6:
            continue  # Skip rows that don't have enough data

        try:
            timestamp = datetime.strptime(row[0], '%m/%d/%Y %H:%M:%S')
            timestamp = timezone.make_aware(timestamp)

            # Check if the entry already exists based on email (assuming email is unique)
            if not FormResponse.objects.filter(email=row[3]).exists():
                
                # Handle photo upload
                photo_url = row[4]
                photo_path = None
                if photo_url:
                    direct_photo_url = convert_drive_link_to_direct_download(photo_url)
                    if direct_photo_url:
                        photo_name = f"{row[1].replace(' ', '_')}.jpg"
                        photo_file_path = f'photos/{photo_name}'

                        # Check if the photo already exists before downloading
                        if not default_storage.exists(photo_file_path):
                            photo_response = requests.get(direct_photo_url)
                            photo_path = default_storage.save(photo_file_path, ContentFile(photo_response.content))
                        else:
                            photo_path = photo_file_path  # Use existing file

                # Handle CV upload
                cv_url = row[5]
                cv_path = None
                if cv_url:
                    direct_cv_url = convert_drive_link_to_direct_download(cv_url)
                    if direct_cv_url:
                        cv_name = f"{row[1].replace(' ', '_')}_cv.pdf"
                        cv_file_path = f'cvs/{cv_name}'

                        # Check if the CV already exists before downloading
                        if not default_storage.exists(cv_file_path):
                            cv_response = requests.get(direct_cv_url)
                            cv_path = default_storage.save(cv_file_path, ContentFile(cv_response.content))
                        else:
                            cv_path = cv_file_path  # Use existing file

                # Create the FormResponse instance
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

                # Create a user from form response after saving
                create_user_from_form_response(row)
            else:
                print(f"Entry for {row[3]} already exists, skipping.")

        except ValueError as e:
            print(f"Error parsing row {row}: {e}")
        except IntegrityError as e:
            print(f"Error saving row {row}: {e}")

def create_user_from_form_response(row):
    print("Creating user from form response")
    email = row[3]  # Gmail as username and password
    password = email  # Set password to the same as the email
    name = row[1]
    # Split the name into first and last names
    full_name = name.split()
    first_name = full_name[0]
    last_name = full_name[-1] if len(full_name) > 1 else ''  # Handles cases where there may not be a last name
    print(full_name)
    # Check if user already exists
    if not User.objects.filter(username=email).exists():
        print(f"Creating user with email: {email}")
        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = first_name
        user.last_name=last_name
        user.save()
        print(f"User {email} created successfully.")
    else:
        print(f"User with email {email} already exists.")

        