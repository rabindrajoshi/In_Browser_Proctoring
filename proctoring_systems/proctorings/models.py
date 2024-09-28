from django.db import models
from django.utils import timezone

class FormResponse(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)  # To store the timestamp from Google Form
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='photos/')  # Ensure you have media setup for file upload
    cv = models.FileField(upload_to='cvs/', null=True, blank=True)  # Optional field
    feedback = models.TextField(null=True, blank=True)  # Optional field

    def __str__(self):
        return self.name
    

class CheatingLog(models.Model):
    username = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    face_count = models.IntegerField()
    detected_objects = models.TextField()
    head_pose = models.CharField(max_length=100)
    gaze_direction = models.CharField(max_length=100)
    cheating_count = models.IntegerField()

    def __str__(self):
        return f"{self.username} - {self.timestamp}"
    


    

