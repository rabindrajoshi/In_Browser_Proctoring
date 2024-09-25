from django.db import models
from django.utils import timezone


class FormResponse(models.Model):
    timestamp = models.DateTimeField(
        default=timezone.now
    )  # To store the timestamp from Google Form
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    photo = models.ImageField(
        upload_to="photos/"
    )  # Ensure you have media setup for file upload
    cv = models.FileField(upload_to="cvs/", null=True, blank=True)  # Optional field
    feedback = models.TextField(null=True, blank=True)  # Optional field

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Question(models.Model):
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()

    # Four options for each question
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    # Correct answer field
    correct_answer = models.CharField(
        max_length=1,
        choices=[
            ("A", "Option A"),
            ("B", "Option B"),
            ("C", "Option C"),
            ("D", "Option D"),
        ],
    )

    def __str__(self):
        return self.text


class Exam(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="exams")
    questions = models.ManyToManyField(Question, related_name="exams")
    duration_minutes = models.PositiveIntegerField()
    date = models.DateTimeField()

    def __str__(self):
        return f"Exam for {self.subject.name} on {self.date.strftime('%Y-%m-%d')}"
