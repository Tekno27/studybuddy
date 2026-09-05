from django.contrib import admin
from .models import (
	Course,
	Notification,
	Programme,
	Report,
	StudentCourse,
	StudentProfile,
	StudyGroup,
	StudyGroupMember,
	StudyRequest,
	StudySession,
	University,
)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
	search_fields = ['name', 'location']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
	list_display = ['name', 'university']
	list_filter = ['university']
	search_fields = ['name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
	list_display = ['code', 'name', 'programme']
	list_filter = ['programme__university', 'programme']
	search_fields = ['code', 'name']


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
	list_display = ['user', 'university', 'programme', 'level', 'study_preference']
	list_filter = ['university', 'programme', 'level', 'study_preference']
	search_fields = ['user__first_name', 'user__last_name', 'user__email']


admin.site.register(StudentCourse)


@admin.register(StudyRequest)
class StudyRequestAdmin(admin.ModelAdmin):
	list_display = ['sender', 'receiver', 'status', 'created_at']
	list_filter = ['status', 'created_at']
	search_fields = ['sender__user__username', 'receiver__user__username']


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
	list_display = ['name', 'course', 'creator', 'created_at']
	search_fields = ['name', 'course__name']


admin.site.register(StudyGroupMember)
admin.site.register(StudySession)
admin.site.register(Notification)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
	list_display = ['reporter', 'reported_student', 'resolved', 'created_at']
	list_filter = ['resolved', 'created_at']
	search_fields = ['reporter__user__username', 'reported_student__user__username', 'reason']
