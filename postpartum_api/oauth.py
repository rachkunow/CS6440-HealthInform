from oauth2_provider.models import get_application_model
from django.contrib.auth.models import User

Application = get_application_model()

def create_oauth_application(name, client_id, client_secret, user):
    """
    Create an OAuth application
    """
    return Application.objects.create(
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_PASSWORD,
        user=user
    )

def get_or_create_oauth_application():
    """
    Get or create the default OAuth application
    """
    try:
        return Application.objects.get(name='Postpartum Health App')
    except Application.DoesNotExist:
        # Create a superuser if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_superuser': True, 'is_staff': True}
        )
        if created:
            admin_user.set_password('admin')  # Change this in production!
            admin_user.save()
        
        return create_oauth_application(
            name='Postpartum Health App',
            client_id='your_client_id',  # Change this in production!
            client_secret='your_client_secret',  # Change this in production!
            user=admin_user
        ) 