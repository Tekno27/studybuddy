from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    PartnerFilterForm,
    ProfileForm,
    RegistrationForm,
    ReportForm,
    StudyGroupForm,
    StudyRequestForm,
    StudySessionForm,
)
from .models import (
    Course,
    Notification,
    Report,
    StudentProfile,
    StudyGroup,
    StudyGroupMember,
    StudyRequest,
    StudySession,
)
from .services import calculate_match_score


def home(request):
	return render(request, 'studybuddy/home.html')


def register(request):
	if request.user.is_authenticated:
		return redirect('studybuddy:profile')
	form = RegistrationForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		with transaction.atomic():
			user = form.save()
		login(request, user)
		messages.success(request, 'Welcome to StudyBuddy. Complete your profile to find study partners.')
		return redirect('studybuddy:profile')
	return render(request, 'studybuddy/register.html', {'form': form})


@login_required
def profile(request):
	student_profile = get_object_or_404(
		StudentProfile.objects.select_related('user', 'university', 'programme').prefetch_related('courses'),
		user=request.user,
	)
	return render(request, 'studybuddy/profile.html', {'profile': student_profile})


@login_required
def edit_profile(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	form = ProfileForm(request.POST or None, instance=student_profile)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Your study profile has been updated.')
		return redirect('studybuddy:profile')
	return render(request, 'studybuddy/edit_profile.html', {'form': form})


@login_required
def find_partners(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	form = PartnerFilterForm(request.GET or None)
	partners = StudentProfile.objects.exclude(pk=student_profile.pk).select_related('user', 'university', 'programme').prefetch_related('courses')
	if form.is_valid():
		query = form.cleaned_data.get('query')
		if query:
			partners = partners.filter(models.Q(user__first_name__icontains=query) | models.Q(user__last_name__icontains=query) | models.Q(courses__name__icontains=query) | models.Q(courses__code__icontains=query))
		if form.cleaned_data.get('university'):
			partners = partners.filter(university=form.cleaned_data['university'])
		if form.cleaned_data.get('programme'):
			partners = partners.filter(programme=form.cleaned_data['programme'])
		if form.cleaned_data.get('level'):
			partners = partners.filter(level=form.cleaned_data['level'])
		if form.cleaned_data.get('course'):
			partners = partners.filter(courses=form.cleaned_data['course'])
		if form.cleaned_data.get('study_preference'):
			partners = partners.filter(study_preference=form.cleaned_data['study_preference'])
	ranked_partners = sorted(((partner, calculate_match_score(student_profile, partner)) for partner in partners.distinct()), key=lambda item: item[1], reverse=True)
	return render(request, 'studybuddy/find_partners.html', {'form': form, 'partners': ranked_partners, 'request_form': StudyRequestForm()})


@login_required
@transaction.atomic
def send_study_request(request, profile_id):
	if request.method != 'POST':
		return redirect('studybuddy:find_partners')
	sender = get_object_or_404(StudentProfile, user=request.user)
	receiver = get_object_or_404(StudentProfile, pk=profile_id)
	if sender.pk == receiver.pk:
		messages.error(request, 'You cannot send a study request to yourself.')
		return redirect('studybuddy:find_partners')
	form = StudyRequestForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Please check your request message and try again.')
		return redirect('studybuddy:find_partners')
	reverse_request = StudyRequest.objects.filter(sender=receiver, receiver=sender).first()
	if reverse_request and reverse_request.status in [StudyRequest.Status.PENDING, StudyRequest.Status.ACCEPTED]:
		messages.info(request, 'You already have an active connection or request with this student.')
		return redirect('studybuddy:find_partners')
	study_request, created = StudyRequest.objects.get_or_create(
		sender=sender,
		receiver=receiver,
		defaults={'message': form.cleaned_data['message']},
	)
	if not created and study_request.status != StudyRequest.Status.REJECTED:
		messages.info(request, 'You already sent a request to this student.')
		return redirect('studybuddy:find_partners')
	if not created:
		study_request.message = form.cleaned_data['message']
		study_request.status = StudyRequest.Status.PENDING
		study_request.save(update_fields=['message', 'status'])
	Notification.objects.create(recipient=receiver, message=f'{sender} sent you a study request.')
	messages.success(request, f'Study request sent to {receiver}.')
	return redirect('studybuddy:find_partners')


@login_required
def requests_view(request):
	profile = get_object_or_404(StudentProfile, user=request.user)
	received = profile.received_requests.select_related('sender__user', 'sender__programme')
	sent = profile.sent_requests.select_related('receiver__user', 'receiver__programme')
	return render(request, 'studybuddy/requests.html', {'profile': profile, 'received_requests': received, 'sent_requests': sent})


@login_required
@transaction.atomic
def update_study_request(request, request_id, action):
	profile = get_object_or_404(StudentProfile, user=request.user)
	study_request = get_object_or_404(StudyRequest, pk=request_id, receiver=profile)
	if request.method != 'POST' or action not in {'accept', 'reject'}:
		return redirect('studybuddy:requests')
	if study_request.status != StudyRequest.Status.PENDING:
		messages.info(request, 'That study request has already been handled.')
		return redirect('studybuddy:requests')
	study_request.status = StudyRequest.Status.ACCEPTED if action == 'accept' else StudyRequest.Status.REJECTED
	study_request.save(update_fields=['status'])
	if action == 'accept':
		Notification.objects.create(recipient=study_request.sender, message=f'{profile} accepted your study request.')
		messages.success(request, f'You are now connected with {study_request.sender}.')
	else:
		messages.success(request, 'Study request rejected.')
	return redirect('studybuddy:requests')


@login_required
def connections(request):
	profile = get_object_or_404(StudentProfile, user=request.user)
	accepted_sent = StudyRequest.objects.filter(sender=profile, status=StudyRequest.Status.ACCEPTED).values_list('receiver_id', flat=True)
	accepted_received = StudyRequest.objects.filter(receiver=profile, status=StudyRequest.Status.ACCEPTED).values_list('sender_id', flat=True)
	connected_profiles = StudentProfile.objects.filter(pk__in=list(accepted_sent) + list(accepted_received)).select_related('user', 'programme', 'university').prefetch_related('courses')
	return render(request, 'studybuddy/connections.html', {'profile': profile, 'connections': connected_profiles})


@login_required
def dashboard(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	partners = StudentProfile.objects.exclude(pk=student_profile.pk).select_related('user', 'programme').prefetch_related('courses')
	top_matches = sorted(
		((partner, calculate_match_score(student_profile, partner)) for partner in partners),
		key=lambda item: item[1],
		reverse=True,
	)[:3]
	return render(request, 'studybuddy/dashboard.html', {
		'profile': student_profile,
		'top_matches': top_matches,
		'group_count': student_profile.study_groups.count(),
		'session_count': student_profile.created_sessions.count(),
		'pending_request_count': student_profile.received_requests.filter(status='pending').count(),
		'accepted_request_count': student_profile.sent_requests.filter(status='accepted').count(),
	})


@login_required
def partner_profile(request, profile_id):
	current_student = get_object_or_404(StudentProfile, user=request.user)
	target_student = get_object_or_404(
		StudentProfile.objects.select_related('user', 'university', 'programme').prefetch_related('courses'),
		pk=profile_id,
	)
	if current_student.pk == target_student.pk:
		return redirect('studybuddy:profile')

	score = calculate_match_score(current_student, target_student)

	sent_request = StudyRequest.objects.filter(sender=current_student, receiver=target_student).first()
	received_request = StudyRequest.objects.filter(sender=target_student, receiver=current_student).first()

	status = 'none'
	if sent_request:
		status = f'sent_{sent_request.status}'
	elif received_request:
		status = f'received_{received_request.status}'

	target_course_ids = set(target_student.courses.values_list('pk', flat=True))
	shared_courses = current_student.courses.filter(pk__in=target_course_ids)

	return render(request, 'studybuddy/partner_profile.html', {
		'target_student': target_student,
		'score': score,
		'status': status,
		'shared_courses': shared_courses,
		'request_form': StudyRequestForm(),
	})


@login_required
def notifications_view(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	notifications = student_profile.notifications.all()
	return render(request, 'studybuddy/notifications.html', {
		'notifications': notifications,
	})


@login_required
def mark_notification_read(request, notification_id):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	notification = get_object_or_404(Notification, pk=notification_id, recipient=student_profile)
	notification.is_read = True
	notification.save(update_fields=['is_read'])
	messages.success(request, 'Notification marked as read.')
	return redirect('studybuddy:notifications')


@login_required
def mark_all_notifications_read(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	student_profile.notifications.filter(is_read=False).update(is_read=True)
	messages.success(request, 'All notifications marked as read.')
	return redirect('studybuddy:notifications')


@login_required
def groups_list(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	my_groups = student_profile.study_groups.select_related('course', 'creator__user').prefetch_related('members')

	query = request.GET.get('query', '').strip()
	course_id = request.GET.get('course')

	all_groups = StudyGroup.objects.select_related('course', 'creator__user').prefetch_related('members')
	if query:
		all_groups = all_groups.filter(
			models.Q(name__icontains=query) |
			models.Q(course__name__icontains=query) |
			models.Q(course__code__icontains=query)
		)
	if course_id:
		all_groups = all_groups.filter(course_id=course_id)

	my_group_ids = set(my_groups.values_list('pk', flat=True))

	return render(request, 'studybuddy/groups_list.html', {
		'my_groups': my_groups,
		'all_groups': all_groups,
		'my_group_ids': my_group_ids,
		'student_courses': student_profile.courses.all(),
		'query': query,
	})


@login_required
def create_group(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	form = StudyGroupForm(request.POST or None, programme=student_profile.programme)
	if request.method == 'POST' and form.is_valid():
		group = form.save(commit=False)
		group.creator = student_profile
		group.save()
		StudyGroupMember.objects.create(group=group, student=student_profile)
		messages.success(request, f'Study group "{group.name}" created successfully!')
		return redirect('studybuddy:group_detail', group_id=group.pk)
	return render(request, 'studybuddy/create_group.html', {'form': form})


@login_required
def group_detail(request, group_id):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	group = get_object_or_404(
		StudyGroup.objects.select_related('course', 'creator__user').prefetch_related('members__user', 'sessions__created_by__user'),
		pk=group_id,
	)
	is_member = group.members.filter(pk=student_profile.pk).exists()
	upcoming_sessions = group.sessions.all()
	return render(request, 'studybuddy/group_detail.html', {
		'group': group,
		'is_member': is_member,
		'is_creator': group.creator_id == student_profile.pk,
		'upcoming_sessions': upcoming_sessions,
	})


@login_required
def join_group(request, group_id):
	if request.method != 'POST':
		return redirect('studybuddy:group_detail', group_id=group_id)
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	group = get_object_or_404(StudyGroup, pk=group_id)
	member, created = StudyGroupMember.objects.get_or_create(group=group, student=student_profile)
	if created:
		if group.creator_id != student_profile.pk:
			Notification.objects.create(recipient=group.creator, message=f'{student_profile} joined your study group "{group.name}".')
		messages.success(request, f'You joined "{group.name}"!')
	else:
		messages.info(request, f'You are already a member of "{group.name}".')
	return redirect('studybuddy:group_detail', group_id=group.pk)


@login_required
def leave_group(request, group_id):
	if request.method != 'POST':
		return redirect('studybuddy:group_detail', group_id=group_id)
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	group = get_object_or_404(StudyGroup, pk=group_id)
	if group.creator_id == student_profile.pk:
		messages.error(request, 'As the group creator, you cannot leave the group. You can manage or delete it in Admin.')
		return redirect('studybuddy:group_detail', group_id=group.pk)
	StudyGroupMember.objects.filter(group=group, student=student_profile).delete()
	messages.success(request, f'You left "{group.name}".')
	return redirect('studybuddy:groups_list')


@login_required
def create_session(request, group_id):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	group = get_object_or_404(StudyGroup, pk=group_id)
	if not group.members.filter(pk=student_profile.pk).exists():
		messages.error(request, 'You must be a member of the study group to schedule a session.')
		return redirect('studybuddy:group_detail', group_id=group.pk)

	form = StudySessionForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		session = form.save(commit=False)
		session.group = group
		session.created_by = student_profile
		session.save()
		for member in group.members.exclude(pk=student_profile.pk):
			Notification.objects.create(
				recipient=member,
				message=f'New study session in "{group.name}": {session.title} on {session.date}.',
			)
		messages.success(request, f'Study session "{session.title}" scheduled successfully!')
		return redirect('studybuddy:group_detail', group_id=group.pk)
	return render(request, 'studybuddy/create_session.html', {'form': form, 'group': group})


@login_required
def sessions_list(request):
	student_profile = get_object_or_404(StudentProfile, user=request.user)
	my_groups = student_profile.study_groups.all()
	sessions = StudySession.objects.filter(group__in=my_groups).select_related('group__course', 'created_by__user').order_by('date', 'time')
	return render(request, 'studybuddy/sessions_list.html', {
		'sessions': sessions,
		'has_groups': my_groups.exists(),
	})


@login_required
def report_student(request, profile_id):
	reporter = get_object_or_404(StudentProfile, user=request.user)
	reported_student = get_object_or_404(StudentProfile, pk=profile_id)
	if reporter.pk == reported_student.pk:
		messages.error(request, 'You cannot report yourself.')
		return redirect('studybuddy:profile')

	form = ReportForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		report = form.save(commit=False)
		report.reporter = reporter
		report.reported_student = reported_student
		report.save()
		messages.success(request, f'Your report regarding {reported_student} has been submitted for administrative review.')
		return redirect('studybuddy:find_partners')
	return render(request, 'studybuddy/report_student.html', {
		'form': form,
		'reported_student': reported_student,
	})

