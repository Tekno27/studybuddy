def calculate_match_score(student_a, student_b):
	courses_a = set(student_a.courses.values_list('pk', flat=True))
	courses_b = set(student_b.courses.values_list('pk', flat=True))
	course_score = len(courses_a & courses_b) / max(len(courses_a | courses_b), 1)
	programme_score = int(student_a.programme_id == student_b.programme_id)
	level_score = int(student_a.level == student_b.level)
	preference_score = int(student_a.study_preference == student_b.study_preference)
	availability_score = int(bool(student_a.availability) and bool(student_b.availability) and student_a.availability.casefold() == student_b.availability.casefold())
	return round((course_score * 40) + (programme_score * 20) + (level_score * 15) + (preference_score * 15) + (availability_score * 10))