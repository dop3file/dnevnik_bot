import logging
import random
import sqlite3
from datetime import datetime

from aiogram import *
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode, InputMediaPhoto, InputMediaVideo, ChatActions
from aiogram.types import ReplyKeyboardRemove,ReplyKeyboardMarkup, KeyboardButton, \
                          InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.markdown import hlink

import config
from database import Database

bot = Bot(token=config.API_TOKEN,parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot,storage=MemoryStorage())


db = Database('db.db')

@dp.message_handler(commands=['start'], state='*')
async def start(message: types.Message):
	if not db.user_exists(message.from_user.id):
		button_student = KeyboardButton('Ученик👨‍🎓') 
		button_teacher = KeyboardButton('Учитель👩‍🏫')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_student, button_teacher)

		await message.answer(f'Привет!\nЭто телеграм бот {config.NAME_PROJECT}\nЗдесь ты сможешь отслеживать свои оценки, смотреть рассписания, делиться домашним заданием и ещё много чего другого\n\nНо для начала тебе нужно зарегистрироватсья, выбери свой тип профиля⬇️',reply_markup=menu)
	else:
		await profile(message)

@dp.message_handler(commands=['help'], state='*')
async def help(message: types.Message):
	await message.answer('Все команды: \n/profile - посмотреть свой профиль')

class CreateProfile(StatesGroup):
	name = State()
	surname = State()
	city = State()
	school_id = State()
	class_id = State()
	all_info = State()
	finish_ = State()

@dp.message_handler(lambda message: message.text == 'Ученик👨‍🎓', state='*')
async def student_registration(message):
	if db.user_exists(message.from_user.id):
		await message.answer('Вы уже зарегистрированы!')
	else:
		button_exit = KeyboardButton('Выйти') 

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_exit)


		await message.answer('Введите ваше имя',reply_markup=menu)
		await CreateProfile.name.set()

@dp.message_handler(state=CreateProfile.name)
async def create_profile_name(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message, state)
		await state.finish()
	else:
		await state.update_data(profile_name=message.text.title())
		await message.reply(message.text.title() + ',введите вашу фамилию')
		await CreateProfile.city.set()

@dp.message_handler(state=CreateProfile.city)
async def create_profile_city(message: types.Message, state: FSMContext):
	await state.update_data(profile_surname=message.text.title())
	await message.answer('Теперь введите ваш город')
	await CreateProfile.next()

@dp.message_handler(state=CreateProfile.school_id)
async def create_profile_school(message: types.Message, state: FSMContext):
	await state.update_data(profile_city=message.text.title())
	user_data = await state.get_data()
	
	all_schools = ''
	for school in db.get_all_schools(user_data["profile_city"]):
		school = [str(i) for i in school]
		all_schools += ' | '.join(school)
		all_schools += '\n'
	if all_schools == '':
		await message.answer(f'К сожалению в вашем городе нет школ')
		await message.answer('Введите ещё раз')
		await CreateProfile.school_id.set()
	else:
		await message.answer(f'Теперь введите номер своей школы из списка\n\n{all_schools}')
		await CreateProfile.next()

@dp.message_handler(state=CreateProfile.class_id)
async def create_profile_class(message: types.Message, state: FSMContext):
	try:
		db.get_school(int(message.text))

		await state.update_data(profile_school_id=message.text)
		user_data = await state.get_data()

		all_class = ''
		for classes in db.get_all_class(user_data["profile_school_id"]):
			classes = [str(i) for i in classes]
			all_class += f'{classes[0]} | {classes[1] + classes[2]}\n'

		await message.answer(f'А теперь введите номер своего класса\n\n{all_class}')
		await CreateProfile.next()

	except IndexError:
		await message.answer(f'Школы с таким номером не существует')
		await student_registration(message)

@dp.message_handler(state=CreateProfile.all_info)
async def create_profile_all_info(message: types.Message, state: FSMContext):
	button_accept = KeyboardButton('Правильно✅') 
	button_decline = KeyboardButton('Заполнить заново❌')
	button_exit = KeyboardButton('Выйти')

	menu = ReplyKeyboardMarkup(one_time_keyboard=True)
	menu.add(button_accept, button_decline, button_exit)

	await state.update_data(profile_class_id=message.text)
	user_data = await state.get_data()
	all_info = f"Имя - {user_data['profile_name']}\nФамилия - {user_data['profile_surname']}\nГород - {user_data['profile_city']}\nШкола - {db.get_school(user_data['profile_school_id'])[1]}\nКласс - {db.get_class(user_data['profile_class_id'])[1]}"
	await message.answer(f'Прекрасно!\nУдостоверьтесь что все заполнено верно: \n{all_info}',reply_markup=menu)
	await CreateProfile.next()

@dp.message_handler(state=CreateProfile.finish_)
async def create_profile_finish(message: types.Message, state: FSMContext):
	if message.text == 'Заполнить заново❌':
		await state.finish()
		await student_registration(message)

	elif message.text == 'Выйти':
		await start(message)
		await state.finish()

	else:
		user_data = await state.get_data()
		db.add_user(user_data['profile_name'], user_data['profile_surname'], 
				user_data['profile_city'], user_data['profile_school_id'], message.from_user.id, user_data['profile_class_id'], True, False, None)
	
		await state.finish()
		await message.answer('Ваша заявка отправлена на модерацию вашему учителю')

@dp.message_handler(lambda message: message.text == 'Учитель👩‍🏫', state='*')
async def teacher_registration(message):
	if db.user_exists(message.from_user.id):
		await message.answer('Вы уже зарегистрированы!')
	else:
		button_exit = KeyboardButton('Выйти') 

		menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
		menu.add(button_exit)


		await message.answer('Введите ваше код',reply_markup=menu)
		await CreateProfileTeacher.code.set()

class CreateProfileTeacher(StatesGroup):
	code = State()
	name = State()
	surname = State()
	patronymic = State()
	city = State()
	finish_ = State()	

@dp.message_handler(state=CreateProfileTeacher.code)
async def create_profile_teacher_code(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await exit(message, state)
	else:
		if db.check_moderation_code(message.text):
			await message.answer('Прекрасно!\nВаш код был использован')
			await message.answer('Теперь введите ваше имя: ')
			await CreateProfileTeacher.next()
		else:
			await message.answer(f'К сожалению такого кода не существует, попробуйте снова')
			await CreateProfileTeacher.code.set()

@dp.message_handler(state=CreateProfileTeacher.name)
async def create_profile_teacher_name(message: types.Message, state: FSMContext):
	await state.update_data(profile_name=message.text.title())
	await message.reply(message.text.title() + ',введите вашу фамилию')
	await CreateProfileTeacher.next()

@dp.message_handler(state=CreateProfileTeacher.surname)
async def create_profile_teacher_name(message: types.Message, state: FSMContext):
	await state.update_data(profile_surname=message.text.title())
	await message.answer('Введите пожалуйста ваше отчество')
	await CreateProfileTeacher.next()

@dp.message_handler(state=CreateProfileTeacher.patronymic)
async def create_profile_teacher_city(message: types.Message, state: FSMContext):
	await state.update_data(profile_patronymic=message.text.title())
	await message.answer('Теперь введите ваш город')
	await CreateProfileTeacher.next()

@dp.message_handler(state=CreateProfileTeacher.city)
async def create_profile_all_info(message: types.Message, state: FSMContext):
	await state.update_data(profile_city=message.text.title())

	button_accept = KeyboardButton('Правильно✅') 
	button_decline = KeyboardButton('Заполнить заново❌')
	button_exit = KeyboardButton('Выйти')

	menu = ReplyKeyboardMarkup(one_time_keyboard=True)
	menu.add(button_accept, button_decline, button_exit)

	await state.update_data(profile_class_id=message.text)
	user_data = await state.get_data()
	all_info = f"Имя - {user_data['profile_name']}\nФамилия - {user_data['profile_surname']}\nОтчество - {user_data['profile_patronymic']}\nГород - {user_data['profile_city']}"
	await message.answer(f'Прекрасно!\nУдостоверьтесь что все заполнено верно: \n{all_info}',reply_markup=menu)
	await CreateProfileTeacher.next()

@dp.message_handler(state=CreateProfileTeacher.finish_)
async def create_profile_finish(message: types.Message, state: FSMContext):
	if message.text == 'Заполнить заново❌':
		await state.finish()
		await teacher_registration(message)
	elif message.text == 'Выйти':
		await state.finish()
		await start(message)
	else:
		user_data = await state.get_data()
		db.add_user(user_data['profile_name'], user_data['profile_surname'], 
				user_data['profile_city'], None, message.from_user.id, None, True, True, user_data['profile_patronymic'])
	
		await state.finish()
		await message.answer('Прекарсно!\nВы прошли регистрацию\n')
		await profile(message)

@dp.message_handler(commands=['profile'],state='*')
async def profile(message: types.Message):
	try:
		if not db.user_type(message.from_user.id):
			await message.answer('Привет ученик!')
		elif db.user_type(message.from_user.id):
			button_school = KeyboardButton('Школа🏫') 
			button_marks = KeyboardButton('Оценки📚')
			button_homework = KeyboardButton('Домашнее задания📝')
			button_attendance = KeyboardButton('Посещаемость🗃')
			button_timetable = KeyboardButton('Расписание🗓')

			menu = ReplyKeyboardMarkup()
			menu.add(button_school, button_marks, button_homework, button_attendance, button_timetable)

			await message.answer(f"Здравствуйте {db.get_all_info_user(message.from_user.id)[1]} {db.get_all_info_user(message.from_user.id)[9]}!\n\nВас приветствует телеграм бот {config.NAME_PROJECT}\nЗдесь вы сможете проставлять оценки ученикам, анализировать успеваемость класса и следить за выполнением домашнего задания"
				,reply_markup=menu)
		else:
			await message.answer('Вы ещё не зарегистрировались или ваша заявка не прошла модерацию')
	except IndexError as e:
		print(e)
		await message.answer('Вы ещё не зарегистрировались или ваша заявка не прошла модерацию')

@dp.message_handler(lambda message: message.text == 'Школа🏫', state='*')
async def schools(message: types.Message):
	if db.user_type(message.from_user.id):
		if db.get_all_info_user(message.from_user.id)[4] == None:
			button_choose_school = KeyboardButton('Выбрать школу из списка📂')
			button_add_school = KeyboardButton('Добавить школу✅')
			button_exit = KeyboardButton('Выйти')

			menu = ReplyKeyboardMarkup(one_time_keyboard=True)
			menu.add(button_add_school, button_choose_school,button_exit)

			await message.answer('Добавьте или выберите школу',reply_markup=menu)
		else: 
			button_choose_class = KeyboardButton('Посмотреть класс из списка📂')
			button_add_class = KeyboardButton('Добавить класс✅')
			button_exit = KeyboardButton('Выйти')

			menu = ReplyKeyboardMarkup(one_time_keyboard=True)
			menu.add(button_add_class, button_choose_class,button_exit)

			await message.answer('Добавьте или выберите класс',reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

def check_members_class(user_id, class_id):
	all_members_class = ''
	all_members_class_db = db.get_all_member_class(db.get_all_info_user(user_id)[4], class_id)
	for count,members in enumerate(all_members_class_db):
		member = [str(i) for i in members]
		all_members_class += f'{count + 1} | {member[2] + " " + member[1]}\n'

	return [all_members_class, all_members_class_db]

def check_all_class(user_id):
	all_class = ''
	for classes in db.get_all_class(db.get_all_info_user(user_id)[4]):
		classes = [str(i) for i in classes]
		all_class += f'{classes[0]} | {classes[1] + classes[2]}\n'

	return all_class

class CreateSchool(StatesGroup):
	name = State()

@dp.message_handler(lambda message: message.text == 'Добавить школу✅', state='*')
async def add_school(message: types.Message):
	if message.text == 'Выйти':
		await exit(message,state)
	elif db.user_type(message.from_user.id):
		if db.get_all_info_user(message.from_user.id)[4] == None:
			await message.answer('Введите название школы: ')
			await CreateSchool.name.set()
		else:
			await message.answer('У вас уже добавлена школа')
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=CreateSchool.name)
async def name_school(message: types.Message, state: FSMContext):
	await state.update_data(name=message.text)
	user_data = await state.get_data()
	count_schools = db.get_count_schools()

	db.add_school(user_data['name'],db.get_all_info_user(message.from_user.id)[3])

	await message.answer('Прекрасно!\nВаша школа добавлена✅')
	db.edit_school_id(message.from_user.id, count_schools + 1)
	await state.finish()
	await schools(message)

class ChooseSchool(StatesGroup):
	id_ = State()

@dp.message_handler(lambda message: message.text == 'Выбрать школу из списка📂', state='*')
async def choose_school(message: types.Message):
	if db.user_type(message.from_user.id):
		if db.get_all_info_user(message.from_user.id)[4] == None:
			all_schools = ''
			for school in db.get_all_schools(db.get_all_info_user(message.from_user.id)[3]):
				school = [str(i) for i in school]
				all_schools += ' | '.join(school)
				all_schools += '\n'
			if all_schools == '':
				await message.answer(f'К сожалению в вашем городе нет школ')
				await schools(message)
			else:
				await message.answer(f'Теперь введите номер своей школы из списка\n\n{all_schools}')
				await ChooseSchool.id_.set()
		else:
			await message.answer('У вас уже добавлена школа')
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=ChooseSchool.id_)
async def id_school(message: types.Message, state: FSMContext):
	await state.update_data(id=message.text)
	user_data = await state.get_data()

	await message.answer('Прекрасно!\nВаша школа добавлена✅')
	db.edit_school_id(message.from_user.id, int(user_data['id']))
	await state.finish()
	await schools(message)

class CreateClass(StatesGroup):
	number = State()
	title = State()

@dp.message_handler(lambda message: message.text == 'Добавить класс✅', state='*')
async def add_class(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer('Введите номер класса: ')
		await CreateClass.number.set()	
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=CreateClass.number)
async def number_class(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(number=int(message.text))

		await message.answer('Теперь введите букву вашего класса: ')
		await CreateClass.next()

@dp.message_handler(state=CreateClass.title)
async def title_class(message: types.Message, state: FSMContext):
	await state.update_data(title=message.text)
	user_data = await state.get_data()

	await message.answer('Прекрасно!\nКласс добавлен')
	db.add_class(user_data['title'], db.get_all_info_user(message.from_user.id)[4], user_data['number'])
	await state.finish()

class ChooseClass(StatesGroup):
	id_class = State()
	id_member = State()

@dp.message_handler(lambda message: message.text == 'Посмотреть класс из списка📂', state='*')
async def choose_class(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer(f'<b><i>Введите номер класса:</i></b> \n\n{check_all_class(message.from_user.id)}')
		await ChooseClass.id_class.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=ChooseClass.id_class)
async def choose_id_class(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)

	await state.update_data(id_class=int(message.text))
	user_data = await state.get_data()

	all_members_class, all_members_class_db = check_members_class(message.from_user.id, user_data['id_class'])

	if len(all_members_class_db) > 0:
		await message.answer(f'<b><i>Ученики данного класса</i></b>\nКоличество учеников - {len(all_members_class_db)}\n\n{all_members_class}')
		await message.answer('Введите номер заинтересовавшего вас ученика:')

		await ChooseClass.next()
	else:
		await message.answer('В этом классе пока нету учеников')
		await state.finish()
		await choose_class(message)

@dp.message_handler(state=ChooseClass.id_member)
async def choose_id_member(message: types.Message, state: FSMContext):
	try:
		if message.text == 'Выйти':
			await exit(message,state)
		else:
			await state.update_data(id_member=int(message.text))
			user_data = await state.get_data()
			
			info_user = db.get_all_info_user(db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[user_data['id_member'] - 1][5])

			await message.answer(f'Имя - {info_user[1]}\nФамилия - {info_user[2]}')
	except IndexError:
		await message.answer('Ученика с таким номером не существует в данном классе')

@dp.message_handler(lambda message: message.text == 'Оценки📚', state='*')
async def marks_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		if db.get_all_info_user(message.from_user.id)[4] == None:
			await message.answer('У вас не выбрана школа')
		else: 
			button_add_mark = KeyboardButton('Поставить оценки')
			button_check_mark = KeyboardButton('Посмотреть оценки')
			button_exit = KeyboardButton('Выйти')

			menu = ReplyKeyboardMarkup(one_time_keyboard=True)
			menu.add(button_add_mark, button_check_mark,button_exit)

			await message.answer('Просмотрите или поставьте оценки',reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

class AddMark(StatesGroup):
	id_class = State()
	subject = State()
	mark = State()

@dp.message_handler(lambda message: message.text == 'Поставить оценки', state='*')
async def add_marks(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer(f'<b><i>Введите номер класса:</i></b> \n\n{check_all_class(message.from_user.id)}')
		await AddMark.id_class.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=AddMark.id_class)
async def choose_subject(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(id_class=int(message.text))
		user_data = await state.get_data()

		all_subjects = ''

		for id_subject, subject in enumerate(db.get_all_subjects(db.get_class(user_data['id_class'])[3])):
			all_subjects += f'{id_subject + 1} | {subject[0]}\n'

		await message.answer(f'Введите номер предмета:\n{all_subjects}')
		await AddMark.next()

@dp.message_handler(state=AddMark.subject)
async def choose_id_class_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(subject_id=int(message.text))
		user_data = await state.get_data()

		all_members_class, all_members_class_db = check_members_class(message.from_user.id, user_data['id_class'])
		
		if len(all_members_class_db) > 0:
			await message.answer('Введите номер ученика и его оценку\nПример: 3 - 7 - комментарий по желанию (где 3 это номер ученика, а 7 это оценка)\n\nЕсли хотите поставить больше одной оценки то разделяйте учеников переносом на следующую строку\nПример:\n1 - 9\n2 - 7')
			await message.answer(f'<b><i>Ученики данного класса</i></b>\nКоличество учеников - {len(all_members_class_db)}\n\n{all_members_class}')

			await AddMark.next()
		else:
			await message.answer('В этом классе пока нету учеников')
			await state.finish()
			await marks_menu(message)

@dp.message_handler(state=AddMark.mark)
async def add_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		try:
			await state.update_data(marks=message.text)
			user_data = await state.get_data()

			subject = db.get_all_subjects(db.get_class(user_data['id_class'])[3])[user_data['subject_id'] - 1][0]
			
			for mark in user_data['marks'].split('\n'):
				id_user = int(mark.split('-')[0].replace(' ',''))
				mark_user = int(mark.split('-')[1].replace(' ',''))

				if len(mark.split('-')) == 3:
					comment = mark.split('-')[2][1::]
				else:
					comment = None

				telegram_id_user = db.get_all_info_user(db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[id_user - 1][5])[5]
				db.add_mark(subject=subject, mark=mark_user, telegram_id=telegram_id_user, comment=comment)


			await message.answer('Прекрасно!\nОценки выставлены')
			await marks_menu(message)
		except Exception as e:
			print(e)
			await message.answer('Что то пошло не так')
			await state.finish()
			await marks_menu(message)

class CheckMark(StatesGroup):
	id_class = State()
	subject = State()
	check_mark = State()

@dp.message_handler(lambda message: message.text == 'Посмотреть оценки', state='*')
async def check_marks(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer(f'<b><i>Введите номер класса:</i></b> \n\n{check_all_class(message.from_user.id)}')
		await CheckMark.id_class.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=CheckMark.id_class)
async def choose_subject_check_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(id_class=int(message.text))
		user_data = await state.get_data()

		all_subjects = ''

		for id_subject, subject in enumerate(db.get_all_subjects(db.get_class(user_data['id_class'])[3])):
			all_subjects += f'{id_subject + 1} | {subject[0]}\n'

		await message.answer(f'Введите номер предмета:\n{all_subjects}')
		await CheckMark.next()

@dp.message_handler(state=CheckMark.subject)
async def choose_id_class_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(subject_id=int(message.text))
		user_data = await state.get_data()

		all_members_class, all_members_class_db = check_members_class(message.from_user.id, user_data['id_class'])
		
		if len(all_members_class_db) > 0:
			await message.answer(f'<b><i>Ученики данного класса</i></b>\nКоличество учеников - {len(all_members_class_db)}\n\n{all_members_class}')
			await message.answer('Введите номер ученика что бы посмотреть его оценки')

			await CheckMark.next()
		else:
			await message.answer('В этом классе пока нету учеников')
			await state.finish()
			await marks_menu(message)

@dp.message_handler(state=CheckMark.check_mark)
async def check_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		try:
			await state.update_data(user_id=int(message.text))
			user_data = await state.get_data()

			subject = db.get_all_subjects(db.get_class(user_data['id_class'])[3])[user_data['subject_id'] - 1][0]
			
			info_user = db.get_all_info_user(db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[user_data['user_id'] - 1][5])

			header = 'Дата' + ' ' * 10 + 'Оценка'
			all_marks = ''
			if not len(db.get_all_marks_student(subject, info_user[5])):
				await message.answer(f'У {info_user[2]} {info_user[1]} нет оценок по этому предмету')
				await marks_menu(message)
			else:
				for mark in db.get_all_marks_student(subject, info_user[5]):
					date = datetime.strptime(mark[2], "%Y-%m-%d %H:%M:%S")
					

					comment = f" | {mark[4]}" if mark[4] else ''
					all_marks += f"{date.strftime('%d.%m.%y')} | {mark[1]} {comment}\n"

				await message.answer(f'Оценки {info_user[2]} {info_user[1]}:\n{header}\n{all_marks}')
				await marks_menu(message)
		except Exception as e:
			print(e)
			await message.answer('Что то пошло не так')
			await state.finish()
			await marks_menu(message)

@dp.message_handler(lambda message: message.text == 'Расписание🗓', state='*')
async def timetable_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		button_call_timetable = KeyboardButton('Расписание звонков')
		button_education_timetable = KeyboardButton('Учебное расписание')
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_call_timetable, button_education_timetable,button_exit)

		await message.answer('Расписание звонков и учебное расписание🗓',reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(commands=['exit'],state='*')
async def exit(message: types.Message, state: FSMContext):
	await state.finish()
	await start(message)

@dp.message_handler(lambda message: message.text == 'Выйти',state='*')
async def exit_text(message: types.Message, state: FSMContext):
	await state.finish()
	await start(message)

@dp.message_handler()
async def any_command(message : types.Message):
	'''Функция непредсказумогого ответа'''
	await message.answer('Хм, незнаю что с этим делать\nПопробуй команду /help')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
