import sqlite3
import random
import string
from datetime import date


class Database:
	def __init__(self,database_file):
		self.connection = sqlite3.connect(database_file, check_same_thread=False)
		self.cursor = self.connection.cursor()

	def add_user(self, name, surname, city, school_id, telegram_id, class_id, type_, moderation, patronymic):	
		with self.connection:
			self.cursor.execute("INSERT INTO `users` (`name`,`surname`,`city`,`school_id`,`telegram_id`,`class_id`,`type`,`moderation`,`patronymic`) VALUES(?,?,?,?,?,?,?,?,?)",
									(name, surname, city, school_id, telegram_id, class_id, type_, moderation, patronymic))

	def user_exists(self, telegram_id):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchall()
			return bool(len(result))

	def user_moderation_exists(self, telegram_id):
		with self.connection:
			result = self.cursor.execute('SELECT `moderation`,`type` FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchall()
			return result[0]

	def get_all_schools(self, city):
		with self.connection:
			result = self.cursor.execute('SELECT `school_id`,`school_name` FROM `schools` WHERE `school_city` = ?', (city,)).fetchall()
			return result

	def get_all_class(self, school_id):
		with self.connection:
			result = self.cursor.execute('SELECT `class_id`,`number`,`title` FROM `class` WHERE `school_id` = ?', (school_id,)).fetchall()
			return result

	def get_school(self, school_id):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `schools` WHERE `school_id` = ?', (school_id,)).fetchall()
			return result[0]

	def get_class(self, class_id):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `class` WHERE `class_id` = ?', (class_id,)).fetchall()
			return result[0]

	def check_moderation_code(self, code):
		with self.connection:
			result = self.cursor.execute('SELECT `code` FROM `moderation_codes` WHERE `code` = ?', (code,)).fetchall()
			if bool(len(result)):
				self.cursor.execute('DELETE FROM `moderation_codes` WHERE `code` = ?',(code,))
				return True
			else:
				return False
	
	def system_create_codes(self, count=15):
		with self.connection:
			alphabet = list(string.ascii_lowercase) + list(string.ascii_uppercase) + list(string.digits)
			for code in range(count):
				self.cursor.execute(f"INSERT INTO `moderation_codes` (`code`) VALUES(?)",(''.join([random.choice(alphabet) for i in range(10)]),))

	def get_all_info_user(self, telegram_id):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchall()
			return result[0]

	def user_type(self, telegram_id):
		'''True - ???????? ??????????????, False - ???????? ????????????'''
		with self.connection:
			try:
				if self.user_moderation_exists(telegram_id)[0] == 0 and self.user_moderation_exists(telegram_id)[1] == 1:
					return False
				elif self.user_moderation_exists(telegram_id)[0] == 1 and self.user_moderation_exists(telegram_id)[1] == 1:
					return True
			except Exception as e:
				print(e)
				return None

	def add_school(self,school_name, school_city):
		with self.connection:
			self.cursor.execute('INSERT INTO `schools` (`school_name`,`school_city`) VALUES(?,?)',(school_name,school_city))

	def edit_school_id(self, telegram_id, school_id):
		with self.connection:
			self.cursor.execute('UPDATE `users` SET `school_id` = ? WHERE `telegram_id` = ?',(school_id,telegram_id))

	def get_all_info_school(self, school_id):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `schools` WHERE `school_id` = ?', (school_id,)).fetchall()
			return result[0]

	def get_count_schools(self):
		with self.connection:
			result = self.cursor.execute('SELECT COUNT(*) FROM `schools`').fetchone()
			return result[0]

	def add_class(self, title, school_id, number):
		with self.connection:
			self.cursor.execute('INSERT INTO `class` (`title`,`school_id`,`number`) VALUES(?,?,?) ',(title,school_id,number))

	def get_all_member_class(self, school_id, class_id):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `users` WHERE `school_id` = ? AND `class_id` = ? ORDER BY `surname`',(school_id, class_id)).fetchall()

	def get_all_subjects(self, class_number):
		with self.connection:
			return self.cursor.execute(f'SELECT `title_subject` FROM `subjects` WHERE `start_learn` <= {class_number} AND `end_learn` >= {class_number}').fetchall()

	def add_mark(self, subject, mark, date, telegram_id, comment=None):
		with self.connection:
			self.cursor.execute("INSERT INTO `marks` (`subject`,`mark`,`date`,`telegram_id`,`comment`) VALUES(?,?,?,?,?) ",(subject,mark,date,telegram_id,comment))

	def get_all_marks_student(self, subject, telegram_id):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `marks` WHERE `subject` = ? AND `telegram_id` = ? ORDER BY `date`',(subject, telegram_id)).fetchall()

	def get_all_title_subjects(self):
		with self.connection:
			return self.cursor.execute('SELECT `title_subject` FROM `subjects`').fetchall()

	def add_timetable(self, school_id, class_id, monday, tuesday, wednesday, thursday, friday, saturday):
		with self.connection:
			self.cursor.execute('INSERT INTO `timetable` (`school_id`, `class_id`, `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`) VALUES(?,?,?,?,?,?,?,?)',
				(school_id, class_id, monday, tuesday, wednesday, thursday, friday, saturday))

	def get_class_id(self, title, number, school_id):
		with self.connection:
			return self.cursor.execute('SELECT `class_id` FROM `class` WHERE `title` = ? AND `number` = ? AND `school_id` = ?',(title, number, school_id)).fetchall()
	
	def get_timetable(self, school_id, class_id):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `timetable` WHERE `school_id` = ? AND `class_id` = ?',(school_id, class_id)).fetchall()[0]

	def edit_timetable(self, school_id, class_id, day, timetable):
		with self.connection:
			self.cursor.execute(f'UPDATE `timetable` SET `{day}` = ? WHERE `school_id` = ? AND `class_id` = ?',(timetable,school_id,class_id))

	def add_attendance(self, subject, telegram_id):
		with self.connection:
			self.cursor.execute("INSERT INTO `attendance` (`subject`,`date`,`telegram_id`) VALUES(?,datetime('now'),?) ",(subject,telegram_id))

	def add_attendance(self, subject, telegram_id):
		with self.connection:
			self.cursor.execute("INSERT INTO `attendance` (`subject`,`date`,`telegram_id`) VALUES(?,datetime('now'),?) ",(subject,telegram_id))
	
	def add_homework(self, subject, homework):
		with self.connection:
			self.cursor.execute("INSERT INTO `homework` (`subject`,`date`,`homework`) VALUES(?,datetime('now'),?) ",(subject,homework))	

	def add_date_check(self, date, telegram_id):
		with self.connection:
			self.cursor.execute(f'UPDATE `users` SET `date_check` = ? WHERE `telegram_id` = ?',(date, telegram_id))

	def date_check_exists(self, telegram_id):
		with self.connection:
			result = self.cursor.execute('SELECT `date_check` FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchall()
			return bool(result[0][0])

	def check_date(self, telegram_id):
		with self.connection:
			return self.cursor.execute('SELECT `date_check` FROM `users` WHERE `telegram_id` = ?',(telegram_id,)).fetchall()[0]

	def get_marks_order_date(self, telegram_id, start_week_day, end_week_day):
		with self.connection:
			return self.cursor.execute('SELECT `mark`,`date`,`subject` FROM `marks` WHERE `telegram_id` = ? AND `date` BETWEEN ? AND ? ORDER BY `date`', (telegram_id,start_week_day, end_week_day)).fetchall()

	def get_homework_order_date(self, start_week_day, end_week_day):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `homework` WHERE `date` BETWEEN ? AND ? ORDER BY `date`', (start_week_day, end_week_day)).fetchall()

	def get_homework_order_specific_date(self, date):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `homework` WHERE `date` = ?',(date,)).fetchone()

	def get_all_schools_leaderboard(self):
		with self.connection:
			result = self.cursor.execute('SELECT * FROM `schools`').fetchall()
			return result

	def get_all_marks_student_leaderboard(self, telegram_id):
		with self.connection:
			return self.cursor.execute('SELECT avg(`mark`) FROM `marks` WHERE `telegram_id` = ?',(telegram_id,)).fetchall()

	def get_all_student_school(self, school_id):
		with self.connection:
			return self.cursor.execute('SELECT * FROM `users` WHERE `school_id` = ? AND `type` = 0 ORDER BY `rating` DESC', (school_id,)).fetchall()

	def update_rating(self, rating, telegram_id):
		with self.connection:
			self.cursor.execute('UPDATE `users` SET `rating` = ? WHERE `telegram_id` = ?',(rating,telegram_id))

	def get_impact_user(self, telegram_id):
		with self.connection:
			return self.cursor.execute('SELECT `impact` FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchone()

	def get_count_any(self, table):
		with self.connection:
			result = self.cursor.execute(f'SELECT COUNT(*) FROM `{table}`').fetchone()
			return result[0]


			