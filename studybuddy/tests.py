from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import ProfileForm
from .models import Course, Notification, Programme, StudentProfile, StudyRequest, University
from .services import calculate_match_score


class AccountFlowTests(TestCase):
	def setUp(self):
		self.university = University.objects.create(name='University of Cape Coast', location='Cape Coast')
		self.programme = Programme.objects.create(university=self.university, name='BSc Computer Science')
		self.course = Course.objects.create(programme=self.programme, code='CSC301', name='Database Systems')

	def registration_data(self):
		return {
			'first_name': 'Ama',
			'last_name': 'Mensah',
			'email': 'ama@example.com',
			'password1': 'A secure password 123!',
			'password2': 'A secure password 123!',
			'university': self.university.pk,
			'programme': self.programme.pk,
			'level': 300,
		}

	def test_registration_creates_user_and_profile(self):
		response = self.client.post('/register/', self.registration_data())

		self.assertRedirects(response, '/profile/')
		user = get_user_model().objects.get(email='ama@example.com')
		self.assertEqual(user.get_full_name(), 'Ama Mensah')
		self.assertEqual(user.student_profile.university, self.university)
		self.assertTrue(self.client.session.get('_auth_user_id'))

	def test_profile_requires_login(self):
		response = self.client.get('/profile/')

		self.assertRedirects(response, '/login/?next=/profile/')

	def test_profile_edit_updates_courses_and_preferences(self):
		user = get_user_model().objects.create_user(username='ama@example.com', email='ama@example.com')
		profile = StudentProfile.objects.create(
			user=user,
			university=self.university,
			programme=self.programme,
			level=300,
			study_preference=StudentProfile.StudyPreference.BOTH,
		)
		self.client.force_login(user)

		response = self.client.post('/profile/edit/', {
			'university': self.university.pk,
			'programme': self.programme.pk,
			'level': 300,
			'courses': [self.course.pk],
			'study_preference': StudentProfile.StudyPreference.IN_PERSON,
			'availability': 'Weekday evenings',
			'bio': 'Looking for a study group.',
		})

		self.assertRedirects(response, '/profile/')
		profile.refresh_from_db()
		self.assertEqual(profile.study_preference, StudentProfile.StudyPreference.IN_PERSON)
		self.assertEqual(list(profile.courses.all()), [self.course])

	def test_profile_form_rejects_course_from_another_programme(self):
		other_programme = Programme.objects.create(university=self.university, name='BSc Information Technology')
		other_course = Course.objects.create(programme=other_programme, code='IFT301', name='Web Systems')

		form = ProfileForm(data={
			'university': self.university.pk,
			'programme': self.programme.pk,
			'level': 300,
			'courses': [other_course.pk],
			'study_preference': StudentProfile.StudyPreference.BOTH,
			'availability': '',
			'bio': '',
		})

		self.assertFalse(form.is_valid())
		self.assertIn('courses', form.errors)


class PartnerDiscoveryTests(TestCase):
	def setUp(self):
		self.university = University.objects.create(name='University of Cape Coast')
		self.programme = Programme.objects.create(university=self.university, name='BSc Computer Science')
		self.course = Course.objects.create(programme=self.programme, code='CSC301', name='Database Systems')
		self.user = get_user_model().objects.create_user(username='ama@example.com', email='ama@example.com')
		self.profile = StudentProfile.objects.create(
			user=self.user,
			university=self.university,
			programme=self.programme,
			level=300,
			study_preference=StudentProfile.StudyPreference.IN_PERSON,
			availability='Weekday evenings',
		)
		self.profile.courses.add(self.course)

	def create_partner(self, email, first_name, course=None):
		user = get_user_model().objects.create_user(username=email, email=email, first_name=first_name)
		partner = StudentProfile.objects.create(
			user=user,
			university=self.university,
			programme=self.programme,
			level=300,
			study_preference=StudentProfile.StudyPreference.IN_PERSON,
			availability='Weekday evenings',
		)
		if course:
			partner.courses.add(course)
		return partner

	def test_match_score_rewards_shared_course_and_profile_preferences(self):
		partner = self.create_partner('kofi@example.com', 'Kofi', self.course)

		self.assertEqual(calculate_match_score(self.profile, partner), 100)

	def test_find_partners_excludes_current_student_and_filters_courses(self):
		matching_partner = self.create_partner('kofi@example.com', 'Kofi', self.course)
		self.create_partner('kojo@example.com', 'Kojo')
		self.client.force_login(self.user)

		response = self.client.get('/partners/', {'course': self.course.pk})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Kofi')
		self.assertNotContains(response, 'Kojo')
		self.assertNotContains(response, 'Ama')
		self.assertEqual(response.context['partners'][0][0], matching_partner)

	def test_dashboard_loads_with_real_profile_counts(self):
		self.client.force_login(self.user)

		response = self.client.get('/dashboard/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Welcome back')
		self.assertEqual(response.context['profile'], self.profile)

	def test_student_can_send_request_and_duplicate_is_blocked(self):
		partner = self.create_partner('kofi@example.com', 'Kofi', self.course)
		self.client.force_login(self.user)

		response = self.client.post(f'/partners/{partner.pk}/request/', {'message': 'Study Database Systems together?'})

		self.assertRedirects(response, '/partners/')
		study_request = StudyRequest.objects.get(sender=self.profile, receiver=partner)
		self.assertEqual(study_request.status, StudyRequest.Status.PENDING)
		self.assertEqual(study_request.message, 'Study Database Systems together?')
		self.assertEqual(Notification.objects.filter(recipient=partner).count(), 1)

		self.client.post(f'/partners/{partner.pk}/request/', {'message': 'Another request'})
		self.assertEqual(StudyRequest.objects.filter(sender=self.profile, receiver=partner).count(), 1)

	def test_receiver_can_accept_request_and_connection_is_visible(self):
		partner = self.create_partner('kofi@example.com', 'Kofi', self.course)
		study_request = StudyRequest.objects.create(sender=partner, receiver=self.profile, message='Want to study together?')
		self.client.force_login(self.user)

		response = self.client.post(f'/requests/{study_request.pk}/accept/')

		self.assertRedirects(response, '/requests/')
		study_request.refresh_from_db()
		self.assertEqual(study_request.status, StudyRequest.Status.ACCEPTED)
		self.assertTrue(Notification.objects.filter(recipient=partner, message__contains='accepted').exists())
		connections_response = self.client.get('/connections/')
		self.assertContains(connections_response, 'Kofi')

	def test_only_receiver_can_update_request(self):
		partner = self.create_partner('kofi@example.com', 'Kofi', self.course)
		study_request = StudyRequest.objects.create(sender=self.profile, receiver=partner)
		self.client.force_login(self.user)

		response = self.client.post(f'/requests/{study_request.pk}/accept/')

		self.assertEqual(response.status_code, 404)
