#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess
import shutil


def bootstrap_environment():
    # 1. Install dependencies if anything is missing
    required_modules = [
        ('django', 'Django'),
        ('rest_framework', 'djangorestframework'),
        ('rest_framework_simplejwt', 'djangorestframework-simplejwt'),
        ('corsheaders', 'django-cors-headers'),
        ('PIL', 'Pillow'),
        ('requests', 'requests'),
        ('dotenv', 'python-dotenv'),
        ('pandas', 'pandas'),
        ('seaborn', 'seaborn'),
        ('sklearn', 'scikit-learn'),
        ('bs4', 'beautifulsoup4'),
        ('fpdf', 'fpdf2')
    ]
    
    missing = []
    for module_name, pip_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
            
    if missing:
        print("[PlantCare AI] Missing dependencies detected. Bootstrapping environment...")
        requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        if os.path.exists(requirements_path):
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
                print("[PlantCare AI] Dependencies installed successfully.")
            except Exception as e:
                print(f"[PlantCare AI] Error installing requirements.txt: {e}")
        else:
            # Install missing individually
            for pkg in missing:
                print(f"Installing {pkg}...")
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
                except Exception as e:
                    print(f"Error installing {pkg}: {e}")
                    
    # 2. Check and copy .env file if it doesn't exist
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    env_example = os.path.join(os.path.dirname(__file__), '.env.example')
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print("[PlantCare AI] Creating .env file from .env.example...")
            shutil.copyfile(env_example, env_file)
        else:
            # Create a basic default .env
            print("[PlantCare AI] Creating default .env file...")
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("DEBUG=True\nSECRET_KEY=django-insecure-default-key-for-local-dev-12345\n")


def main():
    """Run administrative tasks."""
    # Run bootstrap to ensure dependencies and settings are configured
    bootstrap_environment()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantcare.settings')

    # Normalize 'run test' or 'run_test' commands to standard 'test'
    if len(sys.argv) >= 3 and sys.argv[1] == 'run' and sys.argv[2] == 'test':
        sys.argv = [sys.argv[0], 'test'] + sys.argv[3:]
    elif len(sys.argv) >= 2 and sys.argv[1] == 'run_test':
        sys.argv = [sys.argv[0], 'test'] + sys.argv[2:]

    # Automatic database initialization & migration if database file is missing
    try:
        import django
        django.setup()
        from django.core.management import call_command
        db_file = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
        if not os.path.exists(db_file):
            print("[PlantCare AI] Database not found. Initializing database and running migrations...")
            call_command('migrate', interactive=False)
            print("[PlantCare AI] Database initialized successfully.")
            try:
                print("[PlantCare AI] Seeding default agricultural crops...")
                call_command('seed_crops', interactive=False)
            except Exception as e:
                print(f"[PlantCare AI] Failed to seed crops automatically: {e}")
    except Exception:
        pass


    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
