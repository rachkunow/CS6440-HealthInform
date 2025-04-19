# CS6440-
# Postpartum Health Tracking App

A web application for mothers in postpartum to track their physical and mental health by inputting health symptoms. The application provides analytics and visualizations of symptoms to help users identify when they need to seek treatment.

## Setup Instructions

### 1. Install Required Software

Install Python, PostgreSQL, and Git:
```bash
# On Mac with Homebrew
brew install python postgresql git

# Start PostgreSQL
brew services start postgresql

### 2. Clone: git clone https://github.gatech.edu/tphong3/CS6440-.git
cd CS6440-

###3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

###4. Install dependencies
pip install -r requirements.txt

###5. Create PostgreSQLDatabase
createdb postpartum_health

###6. Create your Local Settings 
cp postpartum_project/local_settings.example.py postpartum_project/local_settings.py

Edit 'USER' and 'PASSWORD' to be your PostgreSQL username and password

###7. Apply Db Migration
python manage.py makemigrations
python manage.py migrate

###8. Run the Dev Server
python manage.py runserver
App available at: http://127.0.0.1:8000/

###Project Structure:
- postpartum_project/: Django project settings
- postpartum_api/: Main app
- models.py: FHIR compliant data models
- views.py: API endpoints
- serializers.py: API data serializers

