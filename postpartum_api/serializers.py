from rest_framework import serializers
from .models import Patient, Observation, Questionnaire, QuestionnaireResponse, QuestionnaireResponseItem, Provenance
from django.utils import timezone

# Serializer for patients
class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'identifier', 'active', 'name_first', 'name_last',
                  'gender', 'birth_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        # follows the FHIR patient resource format
        return {
            "resourceType": "Patient",
            "id": str(instance.id),
            "identifier": [{"value": instance.identifier}],
            "active": instance.active,
            "name": [{"family": instance.name_last, "given": [instance.name_first]}],
            "gender": instance.gender,
            "birthDate": instance.birth_date.isoformat()
        }

# Convert symptoms to JSON
class ObservationSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), required=False)
    
    class Meta:
        model = Observation
        fields = ['id', 'patient', 'status', 'category', 'code', 'code_display',
                 'value_quantity', 'value_unit', 'effective_date_time',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # doesn't allow observations submitted for future 
    def validate_effective_date_time(self, value):
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise serializers.ValidationError("effective_date_time cannot be in the far future")
        return value
    
    # uses current time
    def validate(self, data):
        if 'effective_date_time' not in data:
            data['effective_date_time'] = timezone.now()
        return data
    
    # FHIR output format
    def to_representation(self, instance):
        return {
            "resourceType": "Observation",
            "id": str(instance.id),
            "status": instance.status,
            "code": {
                "coding": [{
                    "code": instance.code,
                    "display": instance.code_display
                }]
            },
            "subject": {"reference": f"Patient/{instance.patient.id}"},
            "effectiveDateTime": instance.effective_date_time.isoformat(),
            "valueQuantity": {
                "value": instance.value_quantity,
                "unit": instance.value_unit
            }
        }

class QuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questionnaire
        fields = ['id', 'identifier', 'version', 'name', 'title',
                 'status', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # FHIR format
    def to_representation(self, instance):
        return {
            "resourceType": "Questionnaire",
            "id": str(instance.id),
            "name": instance.name,
            "title": instance.title,
            "status": instance.status,
            "description": instance.description}

class QuestionnaireResponseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireResponseItem
        fields = ['id', 'link_id', 'text', 'answer_boolean', 'answer_decimal',
                 'answer_integer', 'answer_string', 'answer_date',
                 'answer_datetime', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class QuestionnaireResponseSerializer(serializers.ModelSerializer):
    items = QuestionnaireResponseItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuestionnaireResponse
        fields = ['id', 'questionnaire', 'patient', 'status',
                 'authored', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'authored', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        # gets all items for this respone
        items = []
        for item in instance.items.all():
            answer = {}
            if item.answer_boolean is not None:
                answer = {"valueBoolean": item.answer_boolean}
            elif item.answer_decimal is not None:
                answer = {"valueDecimal": float(item.answer_decimal)}
            elif item.answer_integer is not None:
                answer = {"valueInteger": item.answer_integer}
            elif item.answer_string is not None:
                answer = {"valueString": item.answer_string}
            elif item.answer_date is not None:
                answer = {"valueDate": item.answer_date.isoformat()}
            elif item.answer_datetime is not None:
                answer = {"valueDateTime": item.answer_datetime.isoformat()}
            
            items.append({
                "linkId": item.link_id,
                "text": item.text,
                "answer": [answer] if answer else []
            })
        
        return {
            "resourceType": "QuestionnaireResponse",
            "id": str(instance.id),
            "questionnaire": {"reference": f"Questionnaire/{instance.questionnaire.id}"},
            "subject": {"reference": f"Patient/{instance.patient.id}"},
            "authored": instance.authored.isoformat(),
            "item": items
        }
    
    
    def create(self, validated_data):

        items_data = self.context.get('request').data.get('items', []) # gets the data items 
        response = QuestionnaireResponse.objects.create(**validated_data) 
        for item_data in items_data:
            QuestionnaireResponseItem.objects.create(
                questionnaire_response=response,
                **item_data
            )
        
        return response

# Keeps track of what changed and who did it
class ProvenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provenance
        fields = ['id', 'observation', 'questionnaire_response',
                'recorded_at', 'user', 'action', 'reason']
        read_only_fields = ['id', 'recorded_at']
    
    def to_representation(self, instance):
        target_reference = None
        if instance.observation:
            target_reference = f"Observation/{instance.observation.id}"
        elif instance.questionnaire_response:
            target_reference = f"QuestionnaireResponse/{instance.questionnaire_response.id}"
        
        return {
            "resourceType": "Provenance",
            "id": str(instance.id),
            "recorded": instance.recorded_at.isoformat(),
            "agent": [{"who": {"reference": f"Patient/{instance.user.id}"}}],
            "activity": {
                "code": instance.action,
                "display": dict(
                    create="Create",
                    update="Update",
                    delete="Delete"
                ).get(instance.action, instance.action)
            },
            "target": [{"reference": target_reference}] if target_reference else []
        }