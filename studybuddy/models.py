from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class University(models.Model):
	name = models.CharField(max_length=150, unique=True)
	location = models.CharField(max_length=150, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Programme(models.Model):
	university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='programmes')
	name = models.CharField(max_length=150)

	class Meta:
		ordering = ['university__name', 'name']
		constraints = [
			models.UniqueConstraint(fields=['university', 'name'], name='unique_programme_per_university'),
		]

	def __str__(self):
		return f'{self.name} ({self.university.name})'


class Course(models.Model):
	programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='courses')
	code = models.CharField(max_length=20)
	name = models.CharField(max_length=150)

	class Meta:
		ordering = ['code']
		constraints = [
			models.UniqueConstraint(fields=['programme', 'code'], name='unique_course_code_per_programme'),
		]

	def __str__(self):
		return f'{self.code} - {self.name}'


class StudentProfile(models.Model):
	class StudyPreference(models.TextChoices):
		IN_PERSON = 'in_person', 'In-person'
		ONLINE = 'online', 'Online'
		BOTH = 'both', 'In-person or online'

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
	university = models.ForeignKey(University, on_delete=models.PROTECT, related_name='students')
	programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name='students')
	level = models.PositiveSmallIntegerField()
	bio = models.TextField(max_length=500, blank=True)
	study_preference = models.CharField(max_length=20, choices=StudyPreference.choices)
	availability = models.CharField(max_length=200, blank=True)
	courses = models.ManyToManyField(Course, through='StudentCourse', related_name='students')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['user__first_name', 'user__last_name']

	def clean(self):
		if self.programme_id and self.university_id and self.programme.university_id != self.university_id:
			raise ValidationError('The programme must belong to the selected university.')
		if self.level < 1:
			raise ValidationError({'level': 'Level must be at least 1.'})

	def __str__(self):
		return self.user.get_full_name() or self.user.username


class StudentCourse(models.Model):
	student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='student_courses')
	course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_courses')

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['student', 'course'], name='unique_student_course'),
		]

	def __str__(self):
		return f'{self.student} - {self.course.code}'


class StudyRequest(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		ACCEPTED = 'accepted', 'Accepted'
		REJECTED = 'rejected', 'Rejected'

	sender = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='sent_requests')
	receiver = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='received_requests')
	message = models.TextField(max_length=500, blank=True)
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_study_request'),
			models.CheckConstraint(condition=~models.Q(sender=models.F('receiver')), name='request_sender_not_receiver'),
		]

	def clean(self):
		if self.sender_id == self.receiver_id:
			raise ValidationError('You cannot send a study request to yourself.')

	def __str__(self):
		return f'{self.sender} -> {self.receiver} ({self.get_status_display()})'


class StudyGroup(models.Model):
	name = models.CharField(max_length=150)
	course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='study_groups')
	description = models.TextField(max_length=1000, blank=True)
	creator = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='created_groups')
	members = models.ManyToManyField(StudentProfile, through='StudyGroupMember', related_name='study_groups')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.name


class StudyGroupMember(models.Model):
	group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='group_memberships')
	student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='group_memberships')
	joined_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['group', 'student'], name='unique_group_member'),
		]


class StudySession(models.Model):
	group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='sessions')
	title = models.CharField(max_length=150)
	date = models.DateField()
	time = models.TimeField()
	location = models.CharField(max_length=200, blank=True)
	description = models.TextField(max_length=1000, blank=True)
	created_by = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name='created_sessions')

	class Meta:
		ordering = ['date', 'time']

	def __str__(self):
		return self.title


class Notification(models.Model):
	recipient = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='notifications')
	message = models.CharField(max_length=255)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.recipient}: {self.message[:40]}'


class Report(models.Model):
	reporter = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reports_made')
	reported_student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reports_received')
	reason = models.CharField(max_length=255)
	details = models.TextField(max_length=1000, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	resolved = models.BooleanField(default=False)

	class Meta:
		ordering = ['resolved', '-created_at']

	def clean(self):
		if self.reporter_id == self.reported_student_id:
			raise ValidationError('You cannot report yourself.')

	def __str__(self):
		return f'Report from {self.reporter} about {self.reported_student}'
