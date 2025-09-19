from flask import Flask, request, render_template, redirect, url_for
import telebot
import psycopg2
from datetime import datetime
from threading import Thread
import uuid
import os

app = Flask(__name__)

BOT_TOKEN = "8379265885:AAESETRnifM5OgwisOfs0iC9hhzJf0S88vA"
bot = telebot.TeleBot(BOT_TOKEN)

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="Dag",
        user="postgres",
        password="root", 
        port="8887"
    )
    return conn

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Здравствуйте! Чтобы подать заявку, напишите сообщение в формате:\nФИО, Дата подачи заявки, Описание проблемы")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        
        text = message.text
        parts = text.split(',', 2)  
        
        if len(parts) != 3:
            bot.reply_to(message, "Неверный формат! Пожалуйста, используйте: ФИО, Дата, Описание")
            return
            
        full_name = parts[0].strip()
        app_date = parts[1].strip()
        problem_desc = parts[2].strip()
        
        
        try:
            date_obj = datetime.strptime(app_date, '%d.%m.%Y').date()
        except ValueError:
            bot.reply_to(message, "Неверный формат даты! Используйте ДД.ММ.ГГГГ")
            return
        
        
        unique_id = str(uuid.uuid4())[:8]  
        
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO applications (id, full_name, application_date, problem_description, status, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (unique_id, full_name, date_obj, problem_desc, 'новая', message.from_user.id)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        bot.reply_to(message, f"Заявка успешно сохранена! Ваш ID заявки: {unique_id}")
        
    except Exception as e:
        bot.reply_to(message, "Произошла ошибка при обработке заявки")

@app.route('/')
def index():
    
    show_completed = request.args.get('show_completed', 'false')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if show_completed == 'true':
        
        cur.execute("SELECT id, full_name, application_date, problem_description, status FROM applications WHERE status = 'выполнена' ORDER BY application_date DESC")
        applications = cur.fetchall()
        view_type = 'completed'
    else:
        
        cur.execute("SELECT id, full_name, application_date, problem_description, status FROM applications WHERE status != 'выполнена' ORDER BY application_date DESC")
        applications = cur.fetchall()
        view_type = 'active'
    
    cur.close()
    conn.close()
    
    return render_template('index.html', applications=applications, view_type=view_type)

@app.route('/set_in_progress', methods=['POST'])
def set_in_progress():
    application_id = request.form['application_id']
    
   
    conn = get_db_connection()
    cur = conn.cursor()
    
    
    cur.execute("SELECT user_id FROM applications WHERE id = %s", (application_id,))
    result = cur.fetchone()
    
    if result:
        user_id = result[0]
        cur.execute("UPDATE applications SET status = 'в работе' WHERE id = %s", (application_id,))
        conn.commit()
        
        
        try:
            bot.send_message(user_id, f"Ваша заявка с ID {application_id} теперь в работе!")
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
    
    cur.close()
    conn.close()
    
    
    return redirect(url_for('index', show_completed='false'))

@app.route('/set_completed', methods=['POST'])
def set_completed():
    application_id = request.form['application_id']
    
    
    conn = get_db_connection()
    cur = conn.cursor()
    
   
    cur.execute("SELECT user_id FROM applications WHERE id = %s", (application_id,))
    result = cur.fetchone()
    
    if result:
        user_id = result[0]
        cur.execute("UPDATE applications SET status = 'выполнена' WHERE id = %s", (application_id,))
        conn.commit()
        
        
        try:
            bot.send_message(user_id, f"Ваша заявка с ID {application_id} выполнена!")
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
    
    cur.close()
    conn.close()
    
   
    return redirect(url_for('index', show_completed='false'))

@app.route('/edit_status', methods=['POST'])
def edit_status():
    application_id = request.form['application_id']
    new_status = request.form['new_status']
    
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = %s WHERE id = %s", (new_status, application_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('index', show_completed='true'))

@app.route('/delete_application', methods=['POST'])
def delete_application():
    application_id = request.form['application_id']
    
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM applications WHERE id = %s", (application_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('index', show_completed='true'))

def run_bot():
    print("Бот запущен!")
    bot.polling()

if __name__ == "__main__":
    
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        bot_thread = Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
    
    app.run(debug=True)