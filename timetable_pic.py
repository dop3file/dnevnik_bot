from PIL import Image, ImageDraw, ImageFont


MAX_HOMEWORK_LENGHT = 35

step_lesson = 75.5
cord_x_left_homework = 660
cord_x_left_subject = 310
cord_x_right_homework = 2310
cord_x_right_subject = 1960

cord_x_right_date = 1170
cord_x_left_date = 2810

cord_x_left_mark = 1370
cord_x_right_mark = 3020

cord_x_left_date_month = 2400
cord_x_right_date_month = 1160

left_y_days = [310,926,1542]


# 315 для домашки по y // понедельник
# 77 для перехода на следующий урок

def draw_timetable(days, date_year, date_month, date_day_start, date_day_end):
    im = Image.open('shablon.jpg')
    im = im.convert("RGB")

    font_homework = ImageFont.truetype('font.ttf', size=45)
    font_subject = ImageFont.truetype('font.ttf', size=55)
    font_date = ImageFont.truetype('font.ttf', size=45)
    font_mark = ImageFont.truetype('font.ttf', size=70)
    font_date_month = ImageFont.truetype('font.ttf', size=55)

    # число
    draw_text = ImageDraw.Draw(im)
    draw_text.text(
        (630,80),
        str(date_day_start),
        font=font_date_month,
        fill=('black'))
    draw_text.text(
        (2280,80),
        str(date_day_end),
        font=font_date_month,
        fill=('black'))
    # месяц
    draw_text.text(
        (750,80),
        date_month,
        font=font_date_month,
        fill=('black'))
    draw_text.text(
        (2400,80),
        date_month,
        font=font_date_month,
        fill=('black'))

    # год
    draw_text.text(
        (1160,97),
        str(date_year),
        font=font_date,
        fill=('#1C0606'))
    draw_text.text(
        (2810,97),
        str(date_year),
        font=font_date,
        fill=('#1C0606'))

    # уроки
    for number,day in zip(left_y_days,days[0:3]):
        for count, subject in enumerate(day):
            draw_text.text(
                (310,float(number) + float(count) * step_lesson ),
                subject,
                font=font_subject,
                fill=('#1C0606'))
    for number,day in zip(left_y_days,days[3::]):
        for count, subject in enumerate(day):
            draw_text.text(
                (1960,number + count * step_lesson ),
                subject,
                font=font_subject,
                fill=('#1C0606'))




    #draw_text.text((2310,315),'упражнения 2.38-2.42gkfdhgjdfgghsjg',font=font_homework,fill=('#1C0606'))
    #draw_text.text((3020,300),'9',font=font_mark,fill=('red'))

    im.save('static.png')

def draw_timetable_student(days, date_year, date_month, date_day_start, date_day_end, marks, homework):
    im = Image.open('shablon.jpg')
    im = im.convert("RGB")

    font_homework = ImageFont.truetype('font.ttf', size=45)
    font_subject = ImageFont.truetype('font.ttf', size=55)
    font_date = ImageFont.truetype('font.ttf', size=45)
    font_mark = ImageFont.truetype('font.ttf', size=70)
    font_date_month = ImageFont.truetype('font.ttf', size=55)

    # число
    draw_text = ImageDraw.Draw(im)
    draw_text.text(
        (630,80),
        str(date_day_start),
        font=font_date_month,
        fill=('black'))
    draw_text.text(
        (2280,80),
        str(date_day_end),
        font=font_date_month,
        fill=('black'))
    # месяц
    draw_text.text(
        (750,80),
        date_month,
        font=font_date_month,
        fill=('black'))
    draw_text.text(
        (2400,80),
        date_month,
        font=font_date_month,
        fill=('black'))

    # год
    draw_text.text(
        (1160,97),
        str(date_year),
        font=font_date,
        fill=('#1C0606'))
    draw_text.text(
        (2810,97),
        str(date_year),
        font=font_date,
        fill=('#1C0606'))

    # уроки
    for number,day in zip(left_y_days,days[0:3]):
        for count, subject in enumerate(day):
            draw_text.text(
                (310,float(number) + float(count) * step_lesson ),
                subject,
                font=font_subject,
                fill=('#1C0606'))
    for number,day in zip(left_y_days,days[3::]):
        for count, subject in enumerate(day):
            draw_text.text(
                (1960,number + count * step_lesson ),
                subject,
                font=font_subject,
                fill=('#1C0606'))

    for mark in marks:
        if mark[0] < 3:
            draw_text.text(
            (1370,300 + (72.8 * mark[0] * 8) + (72.8 * mark[1])),
            str(mark[2]),
            font=font_mark,
            fill=('red'))
        else:
            mark[0] -= 3
            draw_text.text(
           (3020,225 + (77 * mark[0] * 8) + (77 * mark[1])),
           str(mark[2]),
           font=font_mark,
           fill=('red'))

    for task in homework:
        if task[0] < 3:
            draw_text.text(
            (660,240 + (77 * task[0] * 8) + (77 * task[1])),
            str(task[2]),
            font=font_homework,
            fill=('#1C0606'))
        else:
            task[0] = task[0] - 3
            draw_text.text(
            (2310,240 + (76 * task[0] * 8) + (76 * task[1])),
            str(task[2]),
            font=font_homework,
            fill=('#1C0606'))


    im.save('student.png')