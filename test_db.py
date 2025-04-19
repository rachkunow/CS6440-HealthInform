import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postpartum_project.settings")
django.setup()

from postpartum_api.models import Patient
try:
    patients = Patient.objects.all()
    print(f"Successfully connected to database. Found {len(patients)} patients.")
    print("Database connection test successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
