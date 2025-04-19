from django.db import models
from django.db import models
from django.contrib.auth.models import User
import uuid

class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    identifier = models.CharField(max_length=30, unique=True)
    active = models.BooleanField(default=True)
    name_last = models.CharField(max_length=30, default='Unknown')
    name_first = models.CharField(max_length=30, default='Unknown')
    gender = models.CharField(max_length=30, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown')
    ])
    birth_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name_first} {self.name_last}"

class Observation(models.Model):
    # list of symptom codes 
    SYMPTOM_CODES = {
        'abdominal-pain': ('21522001', 'Abdominal Pain'),
        'bleeding': ('386661006', 'Bleeding'),
        'headache': ('25064002', 'Headache'),
        'body-ache': ('10601006', 'Body Ache'),
        'leg-pain': ('229373006', 'Leg Pain'),
        'chest-pain': ('29857009', 'Chest Pain'),
        'breast-pain': ('75879001', 'Breast Pain'),
        'urination-discomfort': ('49650001', 'Discomfort Urinating'),
        'sadness': ('35489007', 'Sadness'),
        'anxiety': ('48694002', 'Anxiety')
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='observations')

    # observ status
    status = models.CharField(max_length=30, choices=[
        ('final', 'Final'),
        ('update', 'Update'),
        ('unknown', 'Unknown')
    ], default='update')

    category = models.CharField(max_length=50, choices=[
        ('vital-signs', 'Vital Signs'),
    ], default='vital-signs')

    # symptom types and SNOMED CT codes
    code = models.CharField(max_length=50, choices=[
        ('21522001', 'Abdominal Pain'),    # stomach pain
        ('386661006', 'Bleeding'),         # bleeding
        ('25064002', 'Headache'),          # head hurts
        ('10601006', 'Body Ache'),         # overall body pain
        ('229373006', 'Leg Pain'),         # leg hurts
        ('29857009', 'Chest Pain'),        # chest hurts
        ('75879001', 'Breast Pain'),       # breast discomfort
        ('49650001', 'Discomfort Urinating'), # pain when peeing
        ('35489007', 'Sadness'),           # feeling down
        ('48694002', 'Anxiety')            # feeling worried
    ])

    code_display = models.CharField(max_length=100)
    # severity scale 0-10
    value_quantity = models.FloatField(default='0.0')
    value_unit = models.CharField(max_length=30, default='0-10')
    effective_date_time = models.DateTimeField()
    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True) # to implement custom notes for next development?

    def __str__(self):
        return f"{self.patient} - {self.code_display}: {self.value_quantity} {self.value_unit}"

class Questionnaire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.CharField(max_length=30, unique=True)
    version = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[ #default fhir statuses
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('retired', 'Retired'),
        ('unknown', 'Unknown')
    ])

    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# Questionnaire response status
class QuestionnaireResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name='responses')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='questionnaire_responses')
    status = models.CharField(max_length=20, choices=[
        ('in-progress', 'In Progress'),
        ('completed', 'Completed'),
        ('amended', 'Amended'),
        ('entered-in-error', 'Entered in error'),
        ('stopped', 'Stopped')
    ])
    authored = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.identifier} - {self.questionnaire.title}"

# Stores responses to questionnaire
class QuestionnaireResponseItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_response = models.ForeignKey(QuestionnaireResponse, on_delete=models.CASCADE, related_name='items')
    link_id = models.CharField(max_length=100) # links to parent response
    text = models.CharField(max_length=255)  # links to questionnaire question text
    answer_boolean = models.BooleanField(null=True, blank=True)
    answer_decimal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    answer_integer = models.IntegerField(null=True, blank=True)
    answer_string = models.TextField(null=True, blank=True)
    answer_date = models.DateField(null=True, blank=True)
    answer_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text

# this tracks changes
class Provenance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, null=True, blank=True)
    questionnaire_response = models.ForeignKey(QuestionnaireResponse, on_delete=models.CASCADE, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True)
    action = models.CharField(max_length=20, choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')], null=True)
    reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} by {self.user}"