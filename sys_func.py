import math
from datetime import date


def get_eng_day(rus_day):
	eng_days = {
	'понедельник': 'monday',
	'вторник': 'tuesday',
	'среда': 'wednesday',
	'четверг': 'thursday',
	'пятница': 'friday',
	'суббота': 'saturday'
	}
	return eng_days[rus_day.lower()]

def reduce_subjects_titles(subjects_titles: list):
	final_subjects = []
	subjects = {
			'Иностранный язык': 'Иностр. яз.',
			'Русская литература': 'Рус. лит.',
			'Русский язык': 'Рус. яз.',
			'Белорусская литература': 'Бел. лит.',
			'Белорусский язык': 'Бел. яз.',
			'Физическая культура и здоровье': 'Физ-ра',
			'Обществоведение': 'Общество.',
			'Всемирная история': 'Всемирная ист.',
			'История Беларуси': 'Ист. Бел.'
	}

	for subject in subjects_titles:
		try:
			final_subjects.append(subjects[subject])
		except KeyError:
			final_subjects.append(subject)
	return final_subjects

def rating_formula(impact, avg_mark):
	return math.trunc(impact * 50 + avg_mark * 100)

def get_days_before_ct():
	now = date.today()
	ct = date(2022,6,16)
	final = str(ct - now)

	return final.split(" ")[0]

	