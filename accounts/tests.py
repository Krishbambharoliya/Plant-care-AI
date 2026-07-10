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
    # Email-change OTP flow tests (MVT views)
    # ------------------------------------------------------------------

    def test_profile_email_change_redirects_to_verify_page(self):
        """Changing email via profile update redirects to verify-email-change page."""
        from django.test import Client
        client = Client()
        client.force_login(self.test_user)
        response = client.post('/profile/', {
            'first_name': 'Existing',
            'last_name': 'User',
            'email': 'newemail@example.com',  # different from current
            'phone_number': '',
            'location_city': 'Boston',
            'farm_name': 'Old Farm',
            'farm_size_acres': 5.0,
            'latitude': 42.3601,
            'longitude': -71.0589,
        })
        self.assertRedirects(response, '/verify-email-change/')

    def test_email_change_otp_valid_updates_email(self):
        """Valid OTP on verify-email-change page commits the new email."""
        from django.test import Client
        from accounts.models import EmailOTP
        new_email = 'confirmed@example.com'
        # Pre-create OTP record as the view would
        EmailOTP.objects.create(email=new_email, otp='123456', purpose='email_change')

        client = Client()
        client.force_login(self.test_user)
        session = client.session
        session['pending_email'] = new_email
        session.save()

        response = client.post('/verify-email-change/', {'otp': '123456'})
        # Should land back on profile page with success
        self.assertEqual(response.status_code, 200)

        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.email, new_email)

    def test_email_change_otp_invalid_shows_error(self):
        """Wrong OTP on verify-email-change page shows error and does NOT update email."""
        from django.test import Client
        from accounts.models import EmailOTP
        new_email = 'shouldnotchange@example.com'
        EmailOTP.objects.create(email=new_email, otp='999999', purpose='email_change')

        client = Client()
        client.force_login(self.test_user)
        session = client.session
        session['pending_email'] = new_email
        session.save()

        response = client.post('/verify-email-change/', {'otp': '000000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid OTP')

        self.test_user.refresh_from_db()
        # Email must NOT have changed
        self.assertEqual(self.test_user.email, 'existinguser@example.com')


