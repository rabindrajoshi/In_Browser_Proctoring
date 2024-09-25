from django.core.management.base import BaseCommand
from models import Subject, Question


class Command(BaseCommand):
    help = "Populates the database with dummy questions"

    def handle(self, *args, **kwargs):
        questions = [
            {
                "subject": "Mathematics",
                "text": "What is the value of π (Pi) approximately?",
                "option_a": "3.14",  # Correct Answer
                "option_b": "2.71",  # Wrong Answer
                "option_c": "1.41",  # Wrong Answer
                "option_d": "0.57",  # Wrong Answer
                "correct_answer": "A",
            },
            {
                "subject": "Science",
                "text": "What is the chemical symbol for water?",
                "option_a": "O2",  # Wrong Answer
                "option_b": "H2O",  # Correct Answer
                "option_c": "CO2",  # Wrong Answer
                "option_d": "NaCl",  # Wrong Answer
                "correct_answer": "B",
            },
            {
                "subject": "History",
                "text": "Who was the first president of the United States?",
                "option_a": "Abraham Lincoln",  # Wrong Answer
                "option_b": "George Washington",  # Correct Answer
                "option_c": "Thomas Jefferson",  # Wrong Answer
                "option_d": "John Adams",  # Wrong Answer
                "correct_answer": "B",
            },
            # Add other questions similarly
        ]

        for question_data in questions:
            subject, _ = Subject.objects.get_or_create(name=question_data["subject"])
            Question.objects.create(
                subject=subject,
                text=question_data["text"],
                option_a=question_data["option_a"],
                option_b=question_data["option_b"],
                option_c=question_data["option_c"],
                option_d=question_data["option_d"],
                correct_answer=question_data["correct_answer"],
            )

        self.stdout.write(self.style.SUCCESS("Successfully populated dummy questions"))
