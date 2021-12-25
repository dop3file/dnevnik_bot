import sqlite3
import random
import string


class Database:
	def __init__(self,database_file):
		self.connection = sqlite3.connect(database_file)
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
			result = self.cursor.execute('SELECT `class_id`,`title` FROM `class` WHERE `school_id` = ?', (school_id,)).fetchall()
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
		'''True - если учитель, False - если ученик'''
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
			result = self.cursor.execute('SELECT * FROM `schools` WHERE `school_id` = ?', (telegram_id,)).fetchall()
			return result[0]

	def get_count_schools(self):
		with self.connection:
			result = self.cursor.execute('SELECT COUNT(*) FROM `schools`').fetchone()
			return result[0]

db = Database('db.db')
