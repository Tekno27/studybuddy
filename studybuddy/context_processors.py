def notifications_context(request):
    """
    Provides unread notification count and recent notification items
    globally across all templates for logged-in students.
    """
    if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
        profile = request.user.student_profile
        unread_count = profile.notifications.filter(is_read=False).count()
        return {
            'unread_notifications_count': unread_count,
        }
    return {
        'unread_notifications_count': 0,
    }
