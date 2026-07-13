from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class AccountsTests(APITestCase):
    databases = '__all__'
    
    def setUp(self):
        self.register_url = reverse('api-register')
        self.login_url = reverse('api-login')
        self.refresh_url = reverse('api-token_refresh')
        self.profile_url = reverse('api-profile')
        self.preferences_url = reverse('api-preferences')
        
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
            'phone_number': '1234567890',
            'farm_name': 'Green Fields',
            'farm_size_acres': 10.5,
            'location_city': 'New York',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'preferred_language': 'en',
            'theme_preference': 'light'
        }
        
        # Create a default user for login and auth tests
        self.test_user = User.objects.create_user(
            username='existinguser',
            email='existinguser@example.com',
            password='ExistingPassword123!',
            phone_number='0987654321',
            farm_name='Old Farm',
            farm_size_acres=5.0,
            location_city='Boston',
            latitude=42.3601,
            longitude=-71.0589,
            preferred_language='hi',
            theme_preference='dark'
        )

    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['user']['email'], 'testuser@example.com')
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_fails_when_passwords_dont_match(self):
        data = self.user_data.copy()
        data['password2'] = 'DifferentPassword123!'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)

    def test_register_fails_with_duplicate_username(self):
        data = self.user_data.copy()
        data['username'] = 'existinguser'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_fails_with_weak_password(self):
        data = self.user_data.copy()
        data['password'] = 'short'
        data['password2'] = 'short'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_defaults_language_and_theme_when_omitted(self):
        data = self.user_data.copy()
        data.pop('preferred_language')
        data.pop('theme_preference')
        data['username'] = 'defaultuser'
        data['email'] = 'default@example.com'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['preferred_language'], 'en')
        self.assertEqual(response.data['user']['theme_preference'], 'light')

    def test_login_with_correct_credentials(self):
        login_data = {
            'username': 'existinguser',
            'password': 'ExistingPassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'existinguser')

    def test_login_with_email_works(self):
        login_data = {
            'username': 'existinguser@example.com',
            'password': 'ExistingPassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_with_wrong_password_fails(self):
        login_data = {
            'username': 'existinguser',
            'password': 'WrongPassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_wrong_email_fails(self):
        login_data = {
            'username': 'wrong@example.com',
            'password': 'ExistingPassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        login_data = {
            'username': 'existinguser',
            'password': 'ExistingPassword123!'
        }
        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.data['refresh']
        
        response = self.client.post(self.refresh_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_refresh_fails_with_invalid_token(self):
        response = self.client.post(self.refresh_url, {'refresh': 'garbage_token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_requires_auth(self):
        response = self.client.post(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_profile(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.post(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'existinguser')
        self.assertEqual(response.data['location_city'], 'Boston')

    def test_partial_profile_update_only_changes_given_fields(self):
        self.client.force_authenticate(user=self.test_user)
        update_data = {'farm_name': 'Super Farm'}
        response = self.client.patch(self.profile_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['farm_name'], 'Super Farm')
        # Check other fields remained same
        self.assertEqual(response.data['location_city'], 'Boston')

    def test_update_theme_and_language(self):
        self.client.force_authenticate(user=self.test_user)
        pref_data = {'preferred_language': 'gu', 'theme_preference': 'light'}
        response = self.client.patch(self.preferences_url, pref_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preferred_language'], 'gu')
        self.assertEqual(response.data['theme_preference'], 'light')

    def test_invalid_language_rejected(self):
        self.client.force_authenticate(user=self.test_user)
        pref_data = {'preferred_language': 'fr'}
        response = self.client.patch(self.preferences_url, pref_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preferred_language', response.data)

    def test_invalid_theme_rejected(self):
        self.client.force_authenticate(user=self.test_user)
        pref_data = {'theme_preference': 'blue'}
        response = self.client.patch(self.preferences_url, pref_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('theme_preference', response.data)

    def test_preferences_endpoint_ignores_unrelated_fields(self):
        self.client.force_authenticate(user=self.test_user)
        pref_data = {'username': 'newusername', 'preferred_language': 'en'}
        response = self.client.patch(self.preferences_url, pref_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check username did not change
        self.assertEqual(response.data['username'], 'existinguser')
        self.assertEqual(response.data['preferred_language'], 'en')

    # ------------------------------------------------------------------
    # Email uniqueness tests (API)
    # ------------------------------------------------------------------

    def test_register_fails_with_duplicate_email_api(self):
        """Cannot register a new account using an email already taken."""
        data = self.user_data.copy()
        data['username'] = 'brandnewuser'
        data['email'] = 'existinguser@example.com'  # already used by self.test_user
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_fails_with_duplicate_email_case_insensitive_api(self):
        """Email uniqueness check is case-insensitive (EXISTINGUSER@EXAMPLE.COM == existinguser@example.com)."""
        data = self.user_data.copy()
        data['username'] = 'anotheruser'
        data['email'] = 'EXISTINGUSER@EXAMPLE.COM'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_profile_update_rejects_email_already_used_by_another_account_api(self):
        """A user cannot change their email to one that belongs to a different account."""
        # Create a second user
        other = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        self.client.force_authenticate(user=self.test_user)
        response = self.client.patch(self.profile_url, {'email': 'other@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_profile_update_allows_keeping_own_email_api(self):
        """A user can submit their own email unchanged during a profile update."""
        self.client.force_authenticate(user=self.test_user)
        response = self.client.patch(self.profile_url, {'email': 'existinguser@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'existinguser@example.com')

    # ------------------------------------------------------------------
    # Email uniqueness tests (MVT forms)
    # ------------------------------------------------------------------

    def test_registration_form_rejects_duplicate_email(self):
        """FarmerRegistrationForm.clean_email raises ValidationError for a taken email."""
        from accounts.forms import FarmerRegistrationForm
        form_data = {
            'username': 'formuser',
            'email': 'existinguser@example.com',  # already taken
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'preferred_language': 'en',
        }
        form = FarmerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_profile_form_rejects_email_taken_by_another_user(self):
        """FarmerProfileForm.clean_email raises ValidationError when another user owns the email."""
        from accounts.forms import FarmerProfileForm
        User.objects.create_user(
            username='seconduser', email='second@example.com', password='Pass123!'
        )
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'second@example.com',  # belongs to seconduser
            'phone_number': '',
            'location_city': '',
            'farm_name': '',
            'farm_size_acres': '',
            'latitude': '',
            'longitude': '',
        }
        # Bind form to self.test_user instance so it excludes their own pk
        form = FarmerProfileForm(data=form_data, instance=self.test_user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_profile_form_allows_user_to_keep_own_email(self):
        """FarmerProfileForm does NOT reject a user updating profile with their own email."""
        from accounts.forms import FarmerProfileForm
        form_data = {
            'first_name': 'Existing',
            'last_name': 'User',
            'email': 'existinguser@example.com',  # same as self.test_user
            'phone_number': '',
            'location_city': 'Boston',
            'farm_name': 'Old Farm',
            'farm_size_acres': 5.0,
            'latitude': 42.3601,
            'longitude': -71.0589,
        }
        form = FarmerProfileForm(data=form_data, instance=self.test_user)
        self.assertTrue(form.is_valid(), msg=form.errors)

    # ------------------------------------------------------------------
    # Profile update OTP flow tests (unified verify_profile_update_view)
    # ------------------------------------------------------------------

    def test_profile_any_change_redirects_to_verify_page(self):
        """Any profile update redirects to /verify-profile-update/ for OTP confirmation."""
        from django.test import Client
        client = Client()
        client.force_login(self.test_user)
        response = client.post('/profile/', {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'existinguser@example.com',  # same email, just other field changes
            'phone_number': '9999999999',
            'location_city': 'Mumbai',
            'farm_name': 'New Farm',
            'farm_size_acres': 8.0,
            'latitude': 19.0760,
            'longitude': 72.8777,
        })
        self.assertRedirects(response, '/verify-profile-update/')

    def test_profile_update_otp_valid_applies_changes(self):
        """Valid OTP on verify-profile-update applies all pending profile changes."""
        from django.test import Client
        from accounts.models import EmailOTP
        # Pre-create the OTP record as the view would
        EmailOTP.objects.create(
            email=self.test_user.email, otp='112233', purpose='profile_update'
        )
        pending = {
            'first_name': 'Krish', 'last_name': 'B',
            'email': 'existinguser@example.com',
            'phone_number': '8888888888', 'location_city': 'Surat',
            'farm_name': 'Krish Farm', 'farm_size_acres': 12.0,
            'latitude': 21.1702, 'longitude': 72.8311,
        }
        client = Client()
        client.force_login(self.test_user)
        session = client.session
        session['pending_profile'] = pending
        session.save()

        response = client.post('/verify-profile-update/', {'otp': '112233'})
        self.assertEqual(response.status_code, 200)

        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.first_name, 'Krish')
        self.assertEqual(self.test_user.location_city, 'Surat')

    def test_profile_update_otp_with_email_change(self):
        """Valid OTP also commits email change if new email is unique."""
        from django.test import Client
        from accounts.models import EmailOTP
        new_email = 'krishnew@example.com'
        EmailOTP.objects.create(
            email=self.test_user.email, otp='445566', purpose='profile_update'
        )
        pending = {
            'first_name': 'Krish', 'last_name': 'B',
            'email': new_email,   # <-- email is changing
            'phone_number': '', 'location_city': 'Ahmedabad',
            'farm_name': 'Test', 'farm_size_acres': None,
            'latitude': None, 'longitude': None,
        }
        client = Client()
        client.force_login(self.test_user)
        session = client.session
        session['pending_profile'] = pending
        session.save()

        response = client.post('/verify-profile-update/', {'otp': '445566'})
        self.assertEqual(response.status_code, 200)

        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.email, new_email)

    def test_profile_update_otp_invalid_shows_error(self):
        """Wrong OTP shows error and does NOT apply any changes."""
        from django.test import Client
        from accounts.models import EmailOTP
        EmailOTP.objects.create(
            email=self.test_user.email, otp='777777', purpose='profile_update'
        )
        pending = {
            'first_name': 'ShouldNotChange', 'last_name': '',
            'email': 'existinguser@example.com',
            'phone_number': '', 'location_city': '',
            'farm_name': '', 'farm_size_acres': None,
            'latitude': None, 'longitude': None,
        }
        client = Client()
        client.force_login(self.test_user)
        session = client.session
        session['pending_profile'] = pending
        session.save()

        response = client.post('/verify-profile-update/', {'otp': '000000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid OTP')

        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.first_name, 'ShouldNotChange')

    # ------------------------------------------------------------------
    # Password reset redirect fix tests
    # ------------------------------------------------------------------

    def test_password_reset_success_redirects_to_login(self):
        """After successful password reset, user is redirected to /login/ (not a broken render)."""
        from django.test import Client
        from accounts.models import EmailOTP
        EmailOTP.objects.create(
            email=self.test_user.email, otp='654321', purpose='password_reset'
        )
        client = Client()
        response = client.post('/password-reset/verify/', {
            'email': self.test_user.email,
            'otp': '654321',
            'new_password': 'NewStrongPass123!',
        })
        self.assertRedirects(response, '/login/')

    def test_new_password_works_after_reset(self):
        """After password reset, logging in with the NEW password succeeds."""
        from django.test import Client
        from accounts.models import EmailOTP
        new_pw = 'BrandNewPass456!'
        EmailOTP.objects.create(
            email=self.test_user.email, otp='321321', purpose='password_reset'
        )
        client = Client()
        client.post('/password-reset/verify/', {
            'email': self.test_user.email,
            'otp': '321321',
            'new_password': new_pw,
        })
        # Now log in with new password
        login_ok = client.login(username=self.test_user.username, password=new_pw)
        self.assertTrue(login_ok, "Login with new password should succeed after reset")

    def test_old_password_fails_after_reset(self):
        """After password reset, logging in with the OLD password fails."""
        from django.test import Client
        from accounts.models import EmailOTP
        old_pw = 'ExistingPassword123!'
        new_pw = 'TotallyDifferent789!'
        EmailOTP.objects.create(
            email=self.test_user.email, otp='159753', purpose='password_reset'
        )
        client = Client()
        client.post('/password-reset/verify/', {
            'email': self.test_user.email,
            'otp': '159753',
            'new_password': new_pw,
        })
        login_ok = client.login(username=self.test_user.username, password=old_pw)
        self.assertFalse(login_ok, "Old password should NOT work after reset")

    # ------------------------------------------------------------------
    # Find Username tests
    # ------------------------------------------------------------------

    def test_find_username_with_valid_email_returns_success(self):
        """GET+POST to /find-username/ with existing email shows success page."""
        from django.test import Client
        client = Client()
        response = client.post('/find-username/', {'email': self.test_user.email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username has been sent')

    def test_find_username_with_unknown_email_shows_error(self):
        """POST to /find-username/ with unknown email shows error message."""
        from django.test import Client
        client = Client()
        response = client.post('/find-username/', {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account found')

    # ------------------------------------------------------------------
    # Support page tests
    # ------------------------------------------------------------------

    def test_support_page_loads_anonymous(self):
        """Support page loads successfully for unauthenticated users."""
        from django.test import Client
        client = Client()
        response = client.get('/support/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contact Support')

    def test_support_page_loads_authenticated(self):
        """Support page loads successfully for authenticated users with prefilled values."""
        from django.test import Client
        client = Client()
        client.force_login(self.test_user)
        response = client.get('/support/')
        self.assertEqual(response.status_code, 200)
        # Prefilled user email should be visible in template response
        self.assertContains(response, self.test_user.email)

    def test_support_submission_sends_email(self):
        """Submitting support form sends email and shows success message."""
        from django.test import Client
        from django.core import mail
        client = Client()
        response = client.post('/support/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '9999999999',
            'details': 'Need help identifying tomato early blight.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Message Sent!')
        # Check that email was successfully sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Support Request from Test User', mail.outbox[0].subject)

    def test_support_submission_invalid_data(self):
        """Submitting incomplete support form shows error."""
        from django.test import Client
        client = Client()
        response = client.post('/support/', {
            'name': '',
            'email': 'test@example.com',
            'phone': '',
            'details': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'fill in all required fields')
