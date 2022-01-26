import math
from flask import Flask, render_template, url_for, request, redirect, flash, request
from database import Database
import sys_func


app = Flask(__name__)
db = Database('db.db')

def get_avg_marks(telegram_id):
	db_result = db.get_all_marks_student_leaderboard(telegram_id)
	try:
		return round(db_result[0][0], 2)
	except TypeError:
		return None

@app.route('/')
def index():
	return render_template('index.html', count_schools=db.get_count_schools(),count_class=db.get_count_any('class'),count_student=db.get_count_any('users'), ct=sys_func.get_days_before_ct())

@app.route('/rating')
def rating():
	return render_template('choose_school.html',schools=db.get_all_schools_leaderboard())

@app.route('/ct')
def ct():
	return render_template('ct.html', ct=sys_func.get_days_before_ct())

@app.route('/rating/<path:school_id>')
def school_rating(school_id):
	school_info = db.get_all_info_school(int(school_id))
	all_students = db.get_all_student_school(school_info[0])


	return render_template('school.html',school=school_info, students=all_students)



app.jinja_env.globals.update(avg_marks=get_avg_marks)


if __name__ == "__main__":
	app.run(debug=True)