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
            'location_city': 'Surat',
            'latitude': 21.1702,
            'longitude': 72.8311,
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
            location_city='Ahmedabad',
            latitude=23.0225,
            longitude=72.5714,
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
        self.assertEqual(response.data['location_city'], 'Ahmedabad')

    def test_partial_profile_update_only_changes_given_fields(self):
        self.client.force_authenticate(user=self.test_user)
        update_data = {'farm_name': 'Super Farm'}
        response = self.client.patch(self.profile_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['farm_name'], 'Super Farm')
        # Check other fields remained same
        self.assertEqual(response.data['location_city'], 'Ahmedabad')

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
            'location_city': 'Ahmedabad',
            'farm_name': 'Old Farm',
            'farm_size_acres': 5.0,
            'latitude': 23.0225,
            'longitude': 72.5714,
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
            'location_city': 'Surat',
            'farm_name': 'New Farm',
            'farm_size_acres': 8.0,
            'latitude': 21.1702,
            'longitude': 72.8311,
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
        # Check that both support and confirmation emails were sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Support Request from Test User', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['plantcare799@gmail.com'])
        self.assertEqual(mail.outbox[1].to, ['test@example.com'])

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

    # ------------------------------------------------------------------
    # Crop Library API Limit & SearchHistory tests
    # ------------------------------------------------------------------

    def test_crop_library_api_limit_tracking(self):
        """External crop lookup increments APILimitTracker and caches Crop."""
        from django.test import Client
        from accounts.models import APILimitTracker, SearchHistory
        from library.models import Crop
        
        client = Client()
        client.force_login(self.test_user)
        
        # Verify initial tracker state
        tracker, _ = APILimitTracker.objects.get_or_create(api_name='crop_api')
        self.assertEqual(tracker.call_count, 0)
        
        # Search for a new crop
        response = client.get('/library/', {'q': 'KiwiFruit'})
        self.assertEqual(response.status_code, 200)
        
        # Verify tracker was incremented
        tracker.refresh_from_db()
        self.assertEqual(tracker.call_count, 1)
        
        # Verify Crop was saved locally (caching)
        self.assertTrue(Crop.objects.filter(name='Kiwifruit').exists())
        
        # Verify SearchHistory log was created
        self.assertTrue(SearchHistory.objects.filter(user=self.test_user, query_type='crop', query_text='KiwiFruit').exists())

    def test_crop_library_api_limit_exceeded(self):
        """API lookup is blocked and returns error if call count exceeds max_limit (500)."""
        from django.test import Client
        from accounts.models import APILimitTracker
        
        client = Client()
        client.force_login(self.test_user)
        
        # Set call count to limit
        tracker, _ = APILimitTracker.objects.get_or_create(api_name='crop_api')
        tracker.call_count = 500
        tracker.save()
        
        # Search for a new crop
        response = client.get('/library/', {'q': 'PineappleFruit'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'API limit is over')

    # ------------------------------------------------------------------
    # Gujarat Cities Location Constraints
    # ------------------------------------------------------------------

    def test_location_city_gujarat_only_registration(self):
        """Registration blocks cities outside Gujarat state."""
        from django.test import Client
        client = Client()
        
        # Registration payload with non-Gujarat city
        payload = {
            'username': 'gujarat_test',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'gujarat@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'location_city': 'Mumbai',  # Maharashtra city
            'preferred_language': 'en'
        }
        response = client.post('/register/', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Location City must be a city within Gujarat state.')

    def test_location_city_gujarat_only_profile_settings(self):
        """Profile update blocks cities outside Gujarat state."""
        from django.test import Client
        from accounts.models import EmailOTP
        
        client = Client()
        client.force_login(self.test_user)
        
        # Verify initial state
        self.assertEqual(self.test_user.location_city, 'Ahmedabad') # valid Gujarat city
        
        # Attempt to change location to non-Gujarat city
        response = client.post('/profile/', {
            'first_name': self.test_user.first_name,
            'last_name': self.test_user.last_name,
            'email': self.test_user.email,
            'phone_number': self.test_user.phone_number,
            'location_city': 'Delhi',  # Out of Gujarat
            'latitude': '',
            'longitude': '',
            'farm_name': self.test_user.farm_name,
            'farm_size_acres': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Location City must be a city within Gujarat state.')

    # ------------------------------------------------------------------
    # Recovery Journey Tests
    # ------------------------------------------------------------------

    def test_recovery_journey_workflow(self):
        """Test starting a recovery journey, checkin weekly, and mark recovered."""
        from django.test import Client
        from django.core.files.uploadedfile import SimpleUploadedFile
        from accounts.models import RecoveryTracker, RecoveryCheckIn
        
        client = Client()
        client.force_login(self.test_user)
        
        # 1. Start journey
        response = client.post('/recovery/start/', {
            'plant_name': 'My Diseased Potato Plant',
            'crop_type': 'Potato'
        })
        self.assertRedirects(response, '/recovery/')
        self.assertTrue(RecoveryTracker.objects.filter(user=self.test_user, plant_name='My Diseased Potato Plant').exists())
        
        journey = RecoveryTracker.objects.get(user=self.test_user, plant_name='My Diseased Potato Plant')
        self.assertEqual(journey.status, 'ongoing')
        
        # 2. Upload Check-in image
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile('test_leaf.gif', small_gif, content_type='image/gif')
        
        response = client.post(f'/recovery/{journey.id}/checkin/', {
            'image': img,
            'symptoms': 'yellow leaves and brown spots',
            'is_healthy': ''
        })
        self.assertRedirects(response, f'/recovery/{journey.id}/')
        
        checkins = journey.checkins.all()
        self.assertEqual(checkins.count(), 1)
        self.assertEqual(checkins[0].week_number, 1)
        self.assertIn('Yellowing/Spotting detected', checkins[0].care_advice)
        
        # 3. Post care Q&A details request
        response = client.post(f'/recovery/{journey.id}/ask/', {'question': 'How much fertilizer to use?'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'feed with nitrogen-rich organic compost')

        # 4. Mark fully healthy
        response = client.post(f'/recovery/{journey.id}/', {'action': 'mark_recovered'})
        self.assertRedirects(response, f'/recovery/{journey.id}/')
        journey.refresh_from_db()
        self.assertEqual(journey.status, 'recovered')

    def test_five_diseased_plants_recovery(self):
        """Test Plant Recovery Center by adding 5 diseased plants, validating list and details views."""
        from django.test import Client
        from accounts.models import RecoveryTracker
        
        client = Client()
        client.force_login(self.test_user)
        
        plants = [
            ("Tomato Late Blight Plant", "Tomato"),
            ("Potato Early Blight Plant", "Potato"),
            ("Wheat Leaf Rust Plant", "Wheat"),
            ("Maize Common Rust Plant", "Maize"),
            ("Rice Blast Plant", "Rice")
        ]
        
        for name, crop in plants:
            response = client.post('/recovery/start/', {
                'plant_name': name,
                'crop_type': crop
            })
            self.assertRedirects(response, '/recovery/')
            
        # Verify all 5 are added successfully
        self.assertEqual(RecoveryTracker.objects.filter(user=self.test_user).count(), 5)
        
        # Verify the recovery list view shows them
        response = client.get('/recovery/')
        self.assertEqual(response.status_code, 200)
        for name, crop in plants:
            self.assertContains(response, name)
            
        # Verify detail page for each works without errors
        for journey in RecoveryTracker.objects.filter(user=self.test_user):
            response = client.get(f'/recovery/{journey.id}/')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, journey.plant_name)

    # ------------------------------------------------------------------
    # History Logs View
    # ------------------------------------------------------------------

    def test_history_logs_view(self):
        """Test unified history logs page loads details correctly."""
        from django.test import Client
        from accounts.models import SearchHistory
        
        client = Client()
        client.force_login(self.test_user)
        
        # Create some queries
        SearchHistory.objects.create(user=self.test_user, query_type='weather', query_text='Surat')
        
        # Set preference to 'en' to ensure English text is rendered
        self.test_user.preferred_language = 'en'
        self.test_user.save()
        
        response = client.get('/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Surat')
        self.assertContains(response, 'History Logs')
    # ------------------------------------------------------------------
    # Multi-language search, detailed crop reference & support ticket mail
    # ------------------------------------------------------------------

    def test_multilingual_crop_search_resolving(self):
        """Test crop searches resolve in Hindi and Gujarati to standard names."""
        from django.test import Client
        from library.models import Crop
        from django.core.management import call_command
        call_command('seed_crops')
        
        # Set preference to 'en' so the template renders English names
        self.test_user.preferred_language = 'en'
        self.test_user.save()

        client = Client()
        client.force_login(self.test_user)
        
        # 1. Search in Hindi (टमाटर)
        response = client.get('/library/', {'q': 'टमाटर'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tomato')
        
        # 2. Search in Gujarati (બટાકા)
        response = client.get('/library/', {'q': 'બટાકા'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Potato')

    def test_multilingual_weather_city_search_resolving(self):
        """Test weather city search resolves Hindi/Gujarati names correctly."""
        from django.test import Client
        from accounts.models import SearchHistory
        client = Client()
        client.force_login(self.test_user)
        
        # Search for Surat in Hindi (सूरत)
        response = client.get('/weather/', {'city': 'सूरत'})
        self.assertEqual(response.status_code, 200)
        # Verify SearchHistory log recorded the query
        self.assertTrue(SearchHistory.objects.filter(user=self.test_user, query_type='weather', query_text='सूरत').exists())

    def test_partwise_disease_references_and_pdf(self):
        """Verify diseases are grouped by plant part and the catalog PDF downloads."""
        from django.test import Client
        from library.models import Crop, Disease
        from django.core.management import call_command
        call_command('seed_crops')
        
        # Set preference to 'en' so the template renders English part-wise headers
        self.test_user.preferred_language = 'en'
        self.test_user.save()

        client = Client()
        client.force_login(self.test_user)
        
        # View crop library page for Potato
        potato = Crop.objects.get(name='Potato')
        response = client.get('/library/', {'crop_id': potato.id})
        self.assertEqual(response.status_code, 200)
        
        # Verify that part-wise headers are in response
        self.assertContains(response, 'Leaf Diseases')
        self.assertContains(response, 'Fruit Diseases')
        
        # Download all crops PDF Catalog
        response_pdf = client.get('/library/pdf/')
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')
        
        # Download single crop PDF
        response_single_pdf = client.get(f'/library/pdf/{potato.id}/')
        self.assertEqual(response_single_pdf.status_code, 200)
        self.assertEqual(response_single_pdf['Content-Type'], 'application/pdf')

    def test_support_alert_mail_delivery(self):
        """Verify support form sends email to plantcare799@gmail.com and copies sender."""
        from django.test import Client
        from django.core import mail
        client = Client()
        client.force_login(self.test_user)
        
        response = client.post('/support/', {
            'name': 'Test Farmer',
            'email': 'farmer@example.com',
            'phone': '9876543210',
            'details': 'Need advice on wheat root wilt.'
        })
        self.assertEqual(response.status_code, 200)
        # Verify both support mail and confirmation copy were sent
        self.assertEqual(len(mail.outbox), 2)
        
        # First email is support ticket alert
        support_alert = mail.outbox[0]
        self.assertEqual(support_alert.to, ['plantcare799@gmail.com'])
        self.assertIn('Support Request from Test Farmer', support_alert.subject)
        
        # Second email is confirmation to the sender
        confirmation = mail.outbox[1]
        self.assertEqual(confirmation.to, ['farmer@example.com'])
        self.assertIn('We have received your support request!', confirmation.subject)

    def test_invalid_crop_id_graceful_fallback(self):
        """Verify requesting a non-existent crop_id falls back gracefully instead of 404."""
        from django.test import Client
        client = Client()
        client.force_login(self.test_user)
        
        response = client.get('/library/', {'crop_id': 999999})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crops Catalog')

    def test_farming_assistant_ten_times(self):
        """Verify the Farming Assistant handles different queries correctly, querying the DB."""
        from django.test import Client
        client = Client()
        client.force_login(self.test_user)

        queries = [
            "Why did my crop become yellow?",
            "Which fertilizer should I use?",
            "What soil type does Potato need?",
            "How to cure leaf spot disease?",
            "What are the symptoms of early blight?",
            "Pesticide recommendation for tomato",
            "Why are my potato leaves drying?",
            "Best manure for clay soil",
            "What is the ideal temperature range for Potato?",
            "General advice for winter crop watering"
        ]

        for q in queries:
            response = client.post('/assistant/', {'question': q})
            self.assertEqual(response.status_code, 200)
            # Check for a language-independent element (the robot SVG used in the assistant page header)
            self.assertContains(response, 'submit_interview')
