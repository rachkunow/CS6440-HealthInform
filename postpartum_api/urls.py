from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# sets up API routes
router = DefaultRouter()
router.register(r'patients', views.PatientViewSet, basename='patient')
router.register(r'observations', views.ObservationViewSet, basename='observation')
router.register(r'questionnaires', views.QuestionnaireViewSet, basename='questionnaire')
router.register(r'questionnaire-responses', views.QuestionnaireResponseViewSet, basename='questionnaire-response')

# url patterns list
urlpatterns = [
    path('', include(router.urls)),
    # auth routes
    path('auth/google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('auth/login/', views.token_login, name='token_login'),
    path('login/', views.login_view, name='login'),
    path('google/login/', views.google_login, name='google_login'),
    path('accounts/google/login/callback/', views.google_callback_view, name='google_callback'),
    # app pages
    path('test/', views.test_page, name='test_page'),
    path('symptoms/', views.log_symptoms, name='log_symptoms'),
] 