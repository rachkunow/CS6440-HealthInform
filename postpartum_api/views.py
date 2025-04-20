from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.conf import settings
from .models import Patient, Observation, Questionnaire, QuestionnaireResponse, QuestionnaireResponseItem, Provenance
from .serializers import PatientSerializer, ObservationSerializer, QuestionnaireSerializer, QuestionnaireResponseSerializer
import json
import base64
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate
import requests
from datetime import date, datetime
from django.utils import timezone
from rest_framework.authtoken.models import Token
import os

# Create your views here.

# view functions to handle requests

def generate_nonce():
    return secrets.token_urlsafe(32)

# login page
def login_view(request):
    return render(request, 'login.html')

# google login
def google_login(request):
    # random string for security reasons
    nonce = secrets.token_urlsafe(16)
    request.session['oauth_nonce'] = nonce
    
    # from settings or from env variables
    client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', ''))
    redirect_uri = getattr(settings, 'GOOGLE_OAUTH2_REDIRECT_URI', os.environ.get('GOOGLE_OAUTH2_REDIRECT_URI', 'https://cs6440-healthinform.onrender.com/api/accounts/google/login/callback/'))
    
    # builds google url with app
    google_auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth' +
        '?client_id=' + client_id +
        '&response_type=code' +
        '&redirect_uri=' + redirect_uri +
        '&scope=email profile openid' +
        '&nonce=' + nonce
    )
    return redirect(google_auth_url)

def google_callback_view(request):
    code = request.GET.get('code')
    if not code:
        return redirect('/api/login/')
    
    try:
        client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', ''))
        client_secret = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_SECRET', os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET', ''))
        redirect_uri = getattr(settings, 'GOOGLE_OAUTH2_REDIRECT_URI', os.environ.get('GOOGLE_OAUTH2_REDIRECT_URI', 'https://cs6440-healthinform.onrender.com/api/accounts/google/login/callback/'))

        # get token  
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        # call google API
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            return redirect('/api/login/')
        
        token_info = token_response.json()
        id_token = token_info.get('id_token')
        
        # decode token 
        token_parts = id_token.split('.')
        user_data_part = token_parts[1]
        
        # padding for base64 decoding
        padding_needed = len(user_data_part) % 4
        if padding_needed:
            user_data_part += '=' * (4 - padding_needed)
            
        # decode  token for user info
        user_data = json.loads(base64.b64decode(user_data_part).decode('utf-8'))
        
        # user account get/create
        user, created = User.objects.get_or_create(
            username=user_data['email'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', '')}
        )
        
        # patient record get for this user
        patient, created = Patient.objects.get_or_create(
            user=user,
            defaults={
                'identifier': f"PAT-{user.id}",
                'name_first': user_data.get('given_name', ''),
                'name_last': user_data.get('family_name', ''),
                'gender': 'unknown',
                'birth_date': datetime.now().date(),
                'active': True
            }   
        )
        
        # create auth token
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        
        return redirect(f'/api/test/?token={token.key}')
    except Exception as e:
        print(f"Error in google_callback_view: {str(e)}")
        return redirect('/api/login/')

# API for patient data
class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Patient.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def observations(self, request, pk=None):
        patient = self.get_object()
        observations = Observation.objects.filter(patient=patient)
        serializer = ObservationSerializer(observations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def questionnaire_responses(self, request, pk=None):
        patient = self.get_object()
        responses = QuestionnaireResponse.objects.filter(patient=patient)
        serializer = QuestionnaireResponseSerializer(responses, many=True)
        return Response(serializer.data)

# track symptoms
class ObservationViewSet(viewsets.ModelViewSet):
    serializer_class = ObservationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Observation.objects.filter(patient__user=self.request.user)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(effective_date_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(effective_date_time__lte=end_date)
            
        return queryset
    
    def perform_create(self, serializer):
        # save who symptom for
        try:
            patient = Patient.objects.get(user=self.request.user)
            observation = serializer.save(patient=patient)
            
            Provenance.objects.create(  #this tracks changes
                observation=observation,
                user=patient,
                action='create',
                reason='Created via API'
            )
        except Exception as e:
            print(f"Error in perform_create: {e}")
            raise
    
    def perform_update(self, serializer):
        patient = Patient.objects.get(user=self.request.user)
        observation = serializer.save()
        
        Provenance.objects.create(
            observation=observation,
            user=patient,
            action='update',
            reason='Updated via API'
        )

    def create(self, request, *args, **kwargs):
        if request.data.get('resourceType') == 'Observation':
            data = {}
            
            data['status'] = request.data.get('status', 'final')
            
            # get just first category 
            if request.data.get('category'):
                categories = request.data.get('category', [{}])
                if len(categories) > 0:
                    codings = categories[0].get('coding', [{}])
                    if len(codings) > 0:
                        data['category'] = codings[0].get('code', '')
            else:
                data['category'] = ''
            
            # get code and display name
            if request.data.get('code'):
                code_info = request.data.get('code', {})
                codings = code_info.get('coding', [])
                if len(codings) > 0:
                    data['code'] = codings[0].get('code', '')
                    data['code_display'] = codings[0].get('display', '')
            else:
                data['code'] = ''
                data['code_display'] = ''
            
            # get severthy number
            if request.data.get('valueQuantity'):
                value_info = request.data.get('valueQuantity', {})
                data['value_quantity'] = value_info.get('value')
                data['value_unit'] = value_info.get('unit')
            
            data['effective_date_time'] = request.data.get('effectiveDateTime', timezone.now())
            
            # notes as part of observation model, currentlh not implemented in user interface tho, perhaps for next development?
            if request.data.get('note'):
                notes = request.data.get('note', [])
                if len(notes) > 0:
                    data['notes'] = notes[0].get('text', '')
            else:
                data['notes'] = ''
            
            request.data.clear()
            request.data.update(data)

        return super().create(request, *args, **kwargs)

# questionnaire api
class QuestionnaireViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionnaireSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Questionnaire.objects.all()

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        # returns all responses for a questionnaire
        questionnaire = self.get_object()
        responses = QuestionnaireResponse.objects.filter(questionnaire=questionnaire)
        serializer = QuestionnaireResponseSerializer(responses, many=True)
        return Response(serializer.data)

# questionnaire response api
class QuestionnaireResponseViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionnaireResponseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return QuestionnaireResponse.objects.filter(patient__user=self.request.user)
    
    def perform_create(self, serializer):
        patient = Patient.objects.get(user=self.request.user)
        response = serializer.save(patient=patient)
        
        # keep track of changes
        Provenance.objects.create(
            questionnaire_response=response,
            user=patient,
            action='create',
            reason='Created via API'
        )

#  main app page
def test_page(request):
    return render(request, 'test_api.html')

# saves symptoms
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_symptoms(request):
    patient = Patient.objects.get(user=request.user)
    symptoms = request.data.get('symptoms', [])
    
    # save each symptom
    for symptom in symptoms:
        if symptom in Observation.SYMPTOM_CODES:
            code, display = Observation.SYMPTOM_CODES[symptom]
            severity = request.data.get('severity', 5)
            
            # create new symptom
            observation = Observation.objects.create(
                patient=patient,
                status='final',
                category='vital-signs',
                code=code,
                code_display=display,
                value_quantity=severity,
                value_unit='1-10',
                effective_date_time=datetime.now()
            )
            
            # keep track of changes
            Provenance.objects.create(
                observation=observation,
                user=patient,
                action='create',
                reason='Created via symptom tracker'
            )
    
    return Response({'status': 'success'})

def api_interface(request):
    return render(request, 'api_interface.html')

@api_view(['POST'])
@permission_classes([AllowAny])
def token_login(request):
    # Token-based login endpoint

    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'error': 'Please provide both username and password'
        }, status=400)

    user = authenticate(username=username, password=password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        
        # create patient profile
        patient_profile, created = Patient.objects.get_or_create(
            user=user,
            defaults={
                'identifier': f"PAT-{user.id}",
                'name_first': user.first_name or 'Unknown',
                'name_last': user.last_name or 'Unknown',
                'gender': 'unknown',
                'birth_date': date(2000, 1, 1),  # a default birth date
                'active': True
            }
        )

        # Create default questionnaire if none
        Questionnaire.objects.get_or_create(
            identifier='postpartum-wellness-v1',
            version='1.0',
            name='Postpartum Wellness Assessment',
            title='Postpartum Wellness Questionnaire',
            status='active',
            description='A comprehensive assessment of postpartum health and well-being'
        )

        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'patient_id': patient_profile.id
        })
    else:
        return Response({
            'error': 'Invalid credentials'
        }, status=401)
