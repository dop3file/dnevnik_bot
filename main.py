import logging
import random
import sqlite3
from datetime import datetime, timedelta, date
import locale
import os

from aiogram import *
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.utils.exceptions import ChatNotFound 
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
import sys_func
import timetable_pic as pic

locale.setlocale(locale.LC_ALL, "") 

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
				user_data['profile_city'], user_data['profile_school_id'], message.from_user.id, user_data['profile_class_id'], False, False, None)
	
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
			now = date.today()
			ct = date(2022,6,16)
			final = str(ct - now)

			button_dnevnik = KeyboardButton('Дневник🗓') 
			button_timer = KeyboardButton(f'До ЦТ - {final.split(" ")[0]} дня')

			menu = ReplyKeyboardMarkup()
			menu.add(button_dnevnik, button_timer)
			await message.answer(f'Здравствуйте {db.get_all_info_user(message.from_user.id)[1]}!\n\nВас приветствует телеграм бот {config.NAME_PROJECT}\nЗдесь вы сможете увидеть свои оценки, домашнее задание, расписание и многое другое',reply_markup=menu)
		elif db.user_type(message.from_user.id):
			button_school = KeyboardButton('Школа🏫') 
			button_marks = KeyboardButton('Оценки📚')
			button_homework = KeyboardButton('Домашнее задания📝')
			button_attendance = KeyboardButton('Посещаемость🗃')
			button_timetable = KeyboardButton('Расписание🗓')
			button_communication = KeyboardButton('Коммуникация🗣')

			menu = ReplyKeyboardMarkup()
			menu.add(button_school, button_marks, button_homework, button_attendance, button_timetable, button_communication)

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
		try:
			await state.update_data(number=int(message.text))

			await message.answer('Теперь введите букву вашего класса: ')
			await CreateClass.next()
		except ValueError:
			await message.answer('Нужно ввести номер класса, только цифру')
			await state.finish()
			await add_class(message)

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
	date = State()
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

@dp.message_handler(state=AddMark.date)
async def choose_date_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		await state.update_data(marks=message.text)
		user_data = await state.get_data()

		button_today = KeyboardButton('Сегодня')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_today)

		await message.answer('Введите дату урока на который нужно поставить оценки\nПример: 26.01.2022',reply_markup=menu)
		
		await AddMark.next()

@dp.message_handler(state=AddMark.mark)
async def add_marks(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await exit(message,state)
	else:
		try:
			await state.update_data(date=message.text)
			user_data = await state.get_data()

			subject = db.get_all_subjects(db.get_class(user_data['id_class'])[3])[user_data['subject_id'] - 1][0]
			
			for mark in user_data['marks'].split('\n'):
				id_user = int(mark.split('-')[0].replace(' ',''))
				mark_user = int(mark.split('-')[1].replace(' ',''))
				if user_data['date'].lower() == 'сегодня':
					date_mark = datetime.strptime(str(datetime.now()).split(' ')[0],'%Y-%m-%d')
				else:
					date_mark = datetime.strptime(user_data['date'],'%d.%m.%Y')


				if len(mark.split('-')) == 3:
					comment = mark.split('-')[2][1::]
				else:
					comment = None

				telegram_id_user = db.get_all_info_user(db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[id_user - 1][5])[5]
				try:
					await bot.send_message(telegram_id_user,f'{db.get_all_info_user(message.from_user.id)[1]} {db.get_all_info_user(message.from_user.id)[9]} поставил вам {mark_user} по предмету {subject}')
				except Exception:
					pass

				db.add_mark(subject=subject, mark=mark_user, date=date_mark, telegram_id=telegram_id_user, comment=comment)
				db.update_rating(sys_func.rating_formula(db.get_impact_user(telegram_id_user)[0],db.get_all_marks_student_leaderboard(telegram_id_user)[0][0]), telegram_id_user)


			await message.answer('Прекрасно!\nОценки выставлены')
			await state.finish()
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

@dp.message_handler(lambda message: message.text == 'Расписание звонков', state='*')
async def call_timetable(message: types.Message):
	await message.answer('1 смена\n\n1 урок | 08:00 - 08:40\n2 урок | 08:55 - 08:40\n3 урок | 09:50 - 10:30\n4 урок | 10:45 - 11:25\n5 урок | 11:40 - 12:20\n6 урок | 12:30 - 13:10')
	await message.answer('2 смена\n\n1 урок | 14:00 - 14:40\n2 урок | 15:00 - 15:40\n3 урок | 16:00 - 16:40\n4 урок | 16:50 - 17:30\n5 урок | 17:40 - 18:20\n6 урок | 18:30 - 19:10')

# TODO TODAY
@dp.message_handler(lambda message: message.text == 'Учебное расписание', state='*')
async def education_timetable_menu(message: types.Message):
	if db.user_type(message.from_user.id): 
		button_add_timetable = KeyboardButton('Добавить расписание')
		button_edit_timetable = KeyboardButton('Изменить расписание')
		button_check_timetable = KeyboardButton('Посмотреть расписание')
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_add_timetable, button_edit_timetable, button_check_timetable, button_exit)

		await message.answer('Учебное расписание\nДобавь, измени или посмотри',reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

class AddTimetable(StatesGroup):
	class_title = State()
	timetable = State()

@dp.message_handler(lambda message: message.text == 'Добавить расписание', state='*')
async def add_timetable(message: types.Message):
	if db.user_type(message.from_user.id): 
		await message.answer('Введи класс для создания расписания')
		await AddTimetable.class_title.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=AddTimetable.class_title)
async def add_timetable_class(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await education_timetable_menu(message)
	else:
		await state.update_data(class_title=message.text)
		await message.answer('Прекрасно\nТеперь введи расписание уроков\nПример:\n\nПонедельник\n...\n...\nВторник\n...\n...')
		await AddTimetable.next()

@dp.message_handler(state=AddTimetable.timetable)
async def add_timetable_days(message: types.Message, state: FSMContext):
	await state.update_data(days=message.text)
	user_data = await state.get_data()

	days_rus = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота']
	subjects = db.get_all_title_subjects()
	try:
		days_timetable = []
		circle = -1
		for el in user_data['days'].split('\n'):
			el = el.strip(' ')
			if el in days_rus:
				circle += 1
				days_timetable.append([])
			elif (el,) in subjects:
				days_timetable[circle].append(el)
			else:
				await message.answer('Вы неправильно ввели расписание')
				await state.finish()
				await add_timetable(message)
				break

		school_id = db.get_all_info_user(message.from_user.id)[4]
		class_title = int(user_data['class_title'][:-1])
		class_id = db.get_class_id(user_data['class_title'][-1], class_title, school_id)[0][0]

		db.add_timetable(school_id, class_id, '\n'.join(days_timetable[0]),'\n'.join(days_timetable[1]),'\n'.join(days_timetable[2]),'\n'.join(days_timetable[3]),'\n'.join(days_timetable[4]),'\n'.join(days_timetable[5]))
		await message.answer('Ваше расписание добавлено!')
		await state.finish()
		await education_timetable_menu(message)
	except Exception as e:
		print(e)
		await message.answer('Что то пошло не так')
		await state.finish()
		await education_timetable_menu(message)

class CheckTimetable(StatesGroup):
	class_title = State()
	action = State()

@dp.message_handler(lambda message: message.text == 'Посмотреть расписание', state='*')
async def check_timetable(message: types.Message):
	if db.user_type(message.from_user.id): 
		await message.answer('Введите класс для просмотра расписания')
		await CheckTimetable.class_title.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=CheckTimetable.class_title)
async def view_timetable(message: types.Message, state: FSMContext):
	try:
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_exit)

		await state.update_data(class_title=message.text)
		user_data = await state.get_data()

		week_days = ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")
		now = datetime.now()
		day = week_days[now.weekday()] 
		start_week = datetime.now() - timedelta(now.weekday())
		end_week = start_week + timedelta(5)
		month = datetime.now().strftime('%B')
		year = str(datetime.now().year)[2:]

		school_id = db.get_all_info_user(message.from_user.id)[4]
		class_id = db.get_class_id(user_data['class_title'][-1], int(user_data['class_title'][:-1]), school_id)[0][0]

		timetable = db.get_timetable(school_id, class_id)
		timetable = list(map(lambda item: item.split('\n'),timetable[2::]))
		timetable = list(map(lambda item: sys_func.reduce_subjects_titles(item), timetable))

		pic.draw_timetable(timetable,year,month,start_week.day,end_week.day)

		photo = open('static.png', 'rb')
		await bot.send_photo(message.from_user.id, photo)


		await message.answer('Расписание',reply_markup=menu)
		await CheckTimetable.next()
	except IndexError as e:
		print(e)
		await message.answer('Такого класса не существует')
		await state.finish()
		await check_timetable(message)
	except ValueError as e:
		print(e)
		await message.answer('Такого класса не существует')
		await state.finish()
		await check_timetable(message)

@dp.message_handler(state=CheckTimetable.action)
async def timetable_action(message: types.Message, state: FSMContext):
	await state.finish()
	await start(message)

@dp.message_handler(lambda message: message.text == 'Дневник🗓', state='*')
async def dnevnik(message: types.Message):
	if not db.date_check_exists(message.from_user.id):
		db.add_date_check(date(datetime.now().year, datetime.now().month, datetime.now().day), message.from_user.id)

	button_back = KeyboardButton('Назад◀️')
	button_forward = KeyboardButton('Вперёд▶️')
	button_exit = KeyboardButton('Выйти')

	menu = ReplyKeyboardMarkup()
	menu.add(button_back, button_forward, button_exit)	

	school_id = db.get_all_info_user(message.from_user.id)[4]
	class_id = db.get_all_info_user(message.from_user.id)[6]

	week_days = ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")
	now = datetime.strptime(db.check_date(message.from_user.id)[0], "%Y-%m-%d")
	day = week_days[now.weekday()] 
	start_week = now - timedelta(now.weekday())
	end_week = start_week + timedelta(5)
	month = now.strftime('%B')
	year = str(now.year)[2:]
	

	try:
		marks = db.get_marks_order_date(message.from_user.id, start_week, end_week)
	except Exception:
		marks = []

	final_marks = []
	for mark in marks:
		try:
			mark_day = datetime.strptime(mark[1], "%Y-%m-%d %H:%M:%S").weekday()
			subject_number = db.get_timetable(school_id, class_id)[1 + mark_day + 1].split('\n').index(mark[2]) + 1
			final_marks.append([mark_day,subject_number,mark[0]])
		except Exception as e:
			print(e)

	try:
		homework = db.get_homework_order_date(start_week - timedelta(7), end_week - timedelta(7))
	except Exception as e:
		homework = []

	final_homework = []
	for task in homework:
		try:
			task_day = datetime.strptime(task[1], "%Y-%m-%d %H:%M:%S").weekday()
			subject_number = db.get_timetable(school_id, class_id)[1 + task_day + 1].split('\n').index(task[0]) + 1
			homework = task[2]
			final_homework.append([task_day, subject_number, homework])
		except Exception as e:
			print(e)

	timetable = db.get_timetable(school_id, class_id)		
	timetable = list(map(lambda item: item.split('\n'),timetable[2::]))
	timetable = list(map(lambda item: sys_func.reduce_subjects_titles(item), timetable))

	pic.draw_timetable_student(timetable,year,month,start_week.day,end_week.day,final_marks,final_homework)

	photo = open('student.png', 'rb')
	await bot.send_photo(message.from_user.id, photo)


	await message.answer('Расписание',reply_markup=menu)

@dp.message_handler(lambda message: message.text == 'Вперёд▶️', state='*')
async def forward(message: types.Message):
	now = datetime.strptime(db.check_date(message.from_user.id)[0], "%Y-%m-%d")
	db.add_date_check(date(now.year, now.month, now.day) + timedelta(7), message.from_user.id)
	await dnevnik(message)

@dp.message_handler(lambda message: message.text == 'Назад◀️', state='*')
async def forward(message: types.Message):
	now = datetime.strptime(db.check_date(message.from_user.id)[0], "%Y-%m-%d")
	db.add_date_check(date(now.year, now.month, now.day) - timedelta(7), message.from_user.id)
	await dnevnik(message)




class EditTimetable(StatesGroup):
	class_title = State()
	day = State()
	timetable = State()

@dp.message_handler(lambda message: message.text == 'Изменить расписание', state='*')
async def edit_timetable(message: types.Message):
	if db.user_type(message.from_user.id): 
		await message.answer('Введите класс для изменения расписания')
		await EditTimetable.class_title.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=EditTimetable.class_title)
async def edit_timetable_day(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await education_timetable_menu(message)
	else:
		await state.update_data(class_title=message.text)
		await message.answer('Введите день недели для которого вы хотите изменить расписание')
		await EditTimetable.next()

@dp.message_handler(state=EditTimetable.day)
async def edit_timetable_timetable(message: types.Message, state: FSMContext):
	await state.update_data(day=message.text)
	await message.answer('Теперь введите новое расписание для этого дня')
	await EditTimetable.next()

@dp.message_handler(state=EditTimetable.timetable)
async def edit_timetable_finish(message: types.Message, state: FSMContext):
	await state.update_data(timetable=message.text)
	user_data = await state.get_data()
	
	try:
		school_id = db.get_all_info_user(message.from_user.id)[4]
		class_id = db.get_class_id(user_data['class_title'][-1], int(user_data['class_title'][:-1]), school_id)[0][0]

		db.edit_timetable(school_id, class_id, sys_func.get_eng_day(user_data['day']),user_data['timetable'])
		await message.answer('Вы успешно изменили расписание!')
		await state.finish()
		await education_timetable_menu(message)


	except Exception:
		await message.answer('Что то пошло не так')
		await state.finish()
		await education_timetable_menu(message)

class Attendance(StatesGroup):
	class_title = State()
	subject = State()
	final = State()

@dp.message_handler(lambda message: message.text == 'Посещаемость🗃', state='*')
async def attendance(message: types.Message):
	if db.user_type(message.from_user.id):
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_exit)

		await message.answer('Введите класс что бы проставить посещаемость',reply_markup=menu)
		await Attendance.class_title.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=Attendance.class_title)
async def attendance_class_title(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await start(message)
	else:
		await state.update_data(class_title=message.text)
		user_data = await state.get_data()
		all_subjects = ''

		for id_subject, subject in enumerate(db.get_all_subjects(int(user_data['class_title'][:-1]))):
			all_subjects += f'{id_subject + 1} | {subject[0]}\n'

		await message.answer(f'Введите номер предмета:\n{all_subjects}')
		await Attendance.next()

@dp.message_handler(state=Attendance.subject)
async def attendance_students(message: types.Message, state: FSMContext):
	try:
		if message.text == 'Выйти':
			await state.finish()
			await start(message)
		else:
			await state.update_data(subject=int(message.text))
			user_data = await state.get_data()

			id_class = db.get_class_id(user_data['class_title'][-1], int(user_data['class_title'][:-1]), db.get_all_info_user(message.from_user.id)[4])[0][0]
			all_members_class, all_members_class_db = check_members_class(message.from_user.id, id_class)

			if len(all_members_class_db) > 0:
				await message.answer(f'<b><i>Ученики данного класса</i></b>\nКоличество учеников - {len(all_members_class_db)}\n\n{all_members_class}')
				await message.answer('Введите номера учеников через перенос строки\nПример:\n3\n5')

				await Attendance.next()
			else:
				await message.answer('В этом классе пока нет учеников')
				await state.finish()
				await start(message)
	except Exception:
		await message.answer('Что то пошло не так')
		await state.finish()
		await start(message)

@dp.message_handler(state=Attendance.final)
async def attendance_final(message: types.Message, state: FSMContext):
	try:
		await state.update_data(id_students=message.text)
		user_data = await state.get_data()

		students = list(map(int,user_data['id_students'].split('\n')))
		subject = db.get_all_subjects(int(user_data['class_title'][:-1]))[user_data['subject'] - 1][0]
		class_id = db.get_class_id(user_data['class_title'][-1], int(user_data['class_title'][:-1]), db.get_all_info_user(message.from_user.id)[4])[0][0]
		for student in students:
			telegram_id_user = db.get_all_info_user(db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], class_id)[student - 1][5])[5]
			await bot.send_message(telegram_id_user,f'{db.get_all_info_user(message.from_user.id)[1]} {db.get_all_info_user(message.from_user.id)[9]} поставил вам пропуск по предмету {subject}')
			db.add_attendance(subject, telegram_id_user)
		
		await message.answer('Прекрасно!')
		await state.finish()
		await start(message)
	except Exception:
		await message.answer('Что то пошло не так')
		await state.finish()
		await start(message)

class Homework(StatesGroup):
	class_id = State()
	subject = State()
	final = State()

@dp.message_handler(lambda message: message.text == 'Домашнее задания📝', state='*')
async def homework_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_exit)

		await message.answer(f'<b><i>Введите номер класса что бы проставить домашнее задание:</i></b> \n\n{check_all_class(message.from_user.id)}',reply_markup=menu)
		await Homework.class_id.set()
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(state=Homework.class_id)
async def homework_class_id(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await start(message)
	else:
		try:
			await state.update_data(class_id=int(message.text))
			user_data = await state.get_data()

			all_subjects = ''
			all_members_class, all_members_class_db = check_members_class(message.from_user.id, user_data['class_id'])

			for id_subject, subject in enumerate(db.get_all_subjects(db.get_class(user_data['class_id'])[3])):
				all_subjects += f'{id_subject + 1} | {subject[0]}\n'

			await message.answer(f'Введите номер предмета:\n{all_subjects}')
			await Homework.next()
		except IndexError:
			await message.answer('Такого класса не существует')
			await state.finish()
			await homework_menu(message)
		except Exception as e:
			print(e)
			await message.answer('Что то пошло не так')
			await state.finish()
			await start(message)

@dp.message_handler(state=Homework.subject)
async def homework_subject(message: types.Message, state: FSMContext):
	if message.text == 'Выйти':
		await state.finish()
		await start(message)
	else:
		try:
			await state.update_data(subject=int(message.text))

			await message.answer('Введите домашнее задание\nПример: упражнения 2.33-2.40')
			await Homework.next()
		except Exception:
			await message.answer('Что то пошло не так')
			await state.finish()
			await start(message)

@dp.message_handler(state=Homework.final)
async def homework_final(message: types.Message, state: FSMContext):
	try:
		await state.update_data(homework=message.text)
		user_data = await state.get_data()

		subject = db.get_all_subjects(db.get_class(user_data['class_id'])[3])[user_data['subject'] - 1][0]

		db.add_homework(subject, user_data['homework'])

		await message.answer('Прекрасно!')
		await state.finish()
		await start(message)
	except Exception:
		await message.answer('Что то пошло не так')
		await state.finish()
		await start(message)

@dp.message_handler(lambda message: message.text.startswith('До ЦТ - '), state='*')
async def ct(message: types.Message):
	now = date.today()
	ct = date(2022,6,16)
	final = str(ct - now)

	await message.answer(f'''
До ЦТ - {final.split(" ")[0]} дня

График ЦТ в основные дни:

<b>16 июня</b> – белорусский язык;
<b>18 и 19 июня</b> – русский язык;
<b>21 июня</b> – обществоведение;
<b>23 и 24 июня</b> – математика;
<b>26 июня</b> – биология;
<b>28 июня</b> – иностранный язык (английский, немецкий, французский, испанский, китайский);
<b>30</b> июня – химия;
<b>2 июля</b> – физика;
<b>4 июля</b> – история Беларуси;
<b>6 июля</b> – география;
<b>8 июля</b> – всемирная история (новейшее время).

Начало всех тестов ЦТ-2022 в 11-00
''') 

@dp.message_handler(lambda message: message.text == 'Коммуникация🗣', state='*')
async def communication_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		button_events = KeyboardButton('Мероприятия')
		button_communication = KeyboardButton('Сообщить что-либо')
		button_inform_test = KeyboardButton('Напомнить о контрольной')
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_events, button_communication, button_inform_test, button_exit)

		await message.answer('Общайтесь со своим классом или со всей школой сразу!',reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

@dp.message_handler(lambda message: message.text == 'Сообщить что-либо', state='*')
async def inform_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		button_inform_class = KeyboardButton('Сообщить классу')
		button_inform_school = KeyboardButton('Сообщить школе')
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_inform_class, button_inform_school, button_exit)

		await message.answer('Сообщите что-либо классу или всей школе', reply_markup=menu)
	else:
		await message.answer('У вас нет прав на данную функцию')

class InformSchool(StatesGroup):
	message = State()

@dp.message_handler(lambda message: message.text == 'Сообщить школе', state='*')
async def inform_school(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer('Напишите ваше сообщение для всей школы\n<b>P.S Не злоупотребляйте этой функцией :)</b>')
		await InformSchool.message.set()

	else:
		await message.answer('У вас нет прав на данную функцию')


@dp.message_handler(state=InformSchool.message)
async def inform_school_message(message: types.Message, state: FSMContext):
	await state.update_data(message_text=message.text)
	user_data = await state.get_data()

	for user in db.get_all_student_school(db.get_all_info_user(message.from_user.id)[4]):
		try:
			await bot.send_message(user[5], f'Сообщения от {db.get_all_info_user(message.from_user.id)[1]}а {db.get_all_info_user(message.from_user.id)[9]}а\n{user_data["message_text"]}')
		except ChatNotFound:
			pass

	await message.answer('Прекрасно!\nСообщения было отправлено')
	await state.finish()
	await start(message)

class InformClass(StatesGroup):
	class_ = State()
	message = State()

@dp.message_handler(lambda message: message.text == 'Сообщить классу', state='*')
async def inform_class(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer(f'<b><i>Введите номер класса:</i></b> \n\n{check_all_class(message.from_user.id)}')
		await InformClass.class_.set()
	else:
		await message.answer('У вас нет прав на данную функцию') 

@dp.message_handler(state=InformClass.class_)
async def inform_class_id(message: types.Message, state: FSMContext):
	await state.update_data(id_class=int(message.text))
	await message.answer('Теперь введите сообщения для вашего класса')
	await InformClass.next()

@dp.message_handler(state=InformClass.message)
async def inform_class_message(message: types.Message, state: FSMContext):
	await state.update_data(message_text=message.text)
	user_data = await state.get_data()

	all_users_class = db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])

	for user in all_users_class:
		try:
			await bot.send_message(user[5], f'Сообщения от {db.get_all_info_user(message.from_user.id)[1]}а {db.get_all_info_user(message.from_user.id)[9]}а\n{user_data["message_text"]}')
		except ChatNotFound:
			pass

	await message.answer('Прекрасно!\nСообщения было отправлено')
	await state.finish()
	await start(message)

class InformTest(StatesGroup):
	class_id = State()
	subject = State()
	date = State()

@dp.message_handler(lambda message: message.text == 'Напомнить о контрольной', state='*')
async def inform_test(message: types.Message):
	if db.user_type(message.from_user.id):
		await message.answer(f'<b><i>Введите номер класса:</i></b> \n\n{check_all_class(message.from_user.id)}')
		await InformTest.class_id.set()
	else:
		await message.answer('У вас нет прав на данную функцию') 	

@dp.message_handler(state=InformTest.class_id)
async def inform_test_class_id(message: types.Message, state: FSMContext):
	await state.update_data(id_class=int(message.text))
	user_data = await state.get_data()

	class_id = db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[0][6]

	all_subjects = ''
	for id_subject, subject in enumerate(db.get_all_subjects(db.get_class(class_id)[3])):
		all_subjects += f'{id_subject + 1} | {subject[0]}\n'

	await message.answer(f'Введите номер предмета:\n{all_subjects}')
	await InformTest.next()

@dp.message_handler(state=InformTest.subject)
async def inform_test_subject(message: types.Message, state: FSMContext):
	await state.update_data(id_subject=int(message.text))

	await message.answer(f'Введите дату проведения контрольной работы\nПример - 26.01.2022')
	await InformTest.next()	

@dp.message_handler(state=InformTest.date)
async def inform_test_date(message: types.Message, state: FSMContext):
	await state.update_data(date=message.text)
	user_data = await state.get_data()
	
	class_id = db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], user_data['id_class'])[0][6]
	all_users_class = db.get_all_member_class(db.get_all_info_user(message.from_user.id)[4], class_id)
	subject_title = db.get_all_subjects(db.get_class(class_id)[3])[user_data['id_subject'] - 1][0]

	for user in all_users_class:
		try:
			await bot.send_message(user[5], f'Учитель {db.get_all_info_user(message.from_user.id)[1]} {db.get_all_info_user(message.from_user.id)[9]} напоминает вам о <b><i>контрольной работе</i></b>\nОна пройдёт <i>{user_data["date"]}</i> по предмету <b>{subject_title}</b>')
		except ChatNotFound as e:
			print(e)

	await message.answer('Прекрасно!\nНапоминания отправлены')
	await state.finish()	
	await start(message)

@dp.message_handler(lambda message: message.text == 'Мероприятия', state='*')
async def events_menu(message: types.Message):
	if db.user_type(message.from_user.id):
		button_add_event = KeyboardButton('Добавить мероприятие')
		button_upcoming_events = KeyboardButton('Ближайшие мероприятия')
		button_inform_event = KeyboardButton('Напомнить о мероприятии')
		button_exit = KeyboardButton('Выйти')

		menu = ReplyKeyboardMarkup(one_time_keyboard=True)
		menu.add(button_add_event, button_upcoming_events, button_inform_event, button_exit)

		message.answer(f'Вы можете добавить новое меропрития или напомнить своим ученикам о ближайшем мероприятии ',reply_markup=menu)
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
