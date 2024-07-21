from flask import Flask, render_template, redirect, url_for, request, jsonify, send_file, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime, time, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from pywebpush import webpush, WebPushException
import pandas as pd
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///checklist.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Make sure to replace this with a strong secret key
db = SQLAlchemy(app)
Bootstrap(app)

# VAPID keys
VAPID_PUBLIC_KEY = "BB_2p_DrLkdo8M4lwm_lvafxlIb-luYjCCJ8kNmedRV9GsIfieIfXbo67o3gPYQgsLbYjPcrB0eT9ufGa5t6Eyk"
VAPID_PRIVATE_KEY = "zqIrwbJ31ZruMgjOvtf46kNiQWP8K6wFIF-OrOCZX3w"
VAPID_CLAIMS = {"sub": "mailto:your_email@example.com"}

PASSWORD = "OtterWiesel"

class Checklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    moral = db.Column(db.Boolean, default=False)
    dedicated_time = db.Column(db.Boolean, default=False)
    helped = db.Column(db.Boolean, default=False)
    said_love = db.Column(db.Boolean, default=False)
    fun = db.Column(db.Boolean, default=False)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String, nullable=False)
    p256dh = db.Column(db.String, nullable=False)
    auth = db.Column(db.String, nullable=False)

def requires_auth(f):
    def decorated(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return "Invalid password", 403
    return render_template('login.html')

@app.route('/')
@requires_auth
def index():
    checklist = get_current_checklist()
    streaks = calculate_streaks()
    time_left = get_time_left()
    return render_template('index.html', checklist=checklist, streaks=streaks, time_left=time_left, vapid_public_key=VAPID_PUBLIC_KEY)


@app.route('/update', methods=['POST'])
@requires_auth
def update_checklist():
    checklist = get_current_checklist()
    checklist.moral = 'moral' in request.form
    checklist.dedicated_time = 'dedicated_time' in request.form
    checklist.helped = 'helped' in request.form
    checklist.said_love = 'said_love' in request.form
    checklist.fun = 'fun' in request.form
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/history')
@requires_auth
def history():
    checklists = Checklist.query.order_by(Checklist.date.desc()).all()
    formatted_checklists = [{
        'date': checklist.date.strftime('%d.%m.%Y'),
        'moral': 'Yes' if checklist.moral else 'No',
        'dedicated_time': 'Yes' if checklist.dedicated_time else 'No',
        'helped': 'Yes' if checklist.helped else 'No',
        'said_love': 'Yes' if checklist.said_love else 'No',
        'fun': 'Yes' if checklist.fun else 'No'
    } for checklist in checklists]
    return render_template('history.html', checklists=formatted_checklists)

@app.route('/export')
@requires_auth
def export():
    checklists = Checklist.query.order_by(Checklist.date).all()
    data = [{
        'Date': checklist.date.strftime('%d.%m.%Y'),
        'Moral': 'Yes' if checklist.moral else 'No',
        'Dedicated Time': 'Yes' if checklist.dedicated_time else 'No',
        'Helped': 'Yes' if checklist.helped else 'No',
        'Said Love': 'Yes' if checklist.said_love else 'No',
        'Fun': 'Yes' if checklist.fun else 'No'
    } for checklist in checklists]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Checklists')
    
    workbook = writer.book
    worksheet = writer.sheets['Checklists']
    date_format = workbook.add_format({'num_format': 'dd.mm.yyyy'})
    worksheet.set_column('A:A', 12, date_format)

    writer.save()
    output.seek(0)
    return send_file(output, download_name='checklists.xlsx', as_attachment=True)

@app.route('/subscribe', methods=['POST'])
@requires_auth
def subscribe():
    subscription_info = request.get_json()
    if not subscription_info:
        return abort(400)
    subscription = Subscription(
        endpoint=subscription_info['endpoint'],
        p256dh=subscription_info['keys']['p256dh'],
        auth=subscription_info['keys']['auth']
    )
    db.session.add(subscription)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/send_notifications', methods=['POST'])
def send_notifications():
    subscriptions = Subscription.query.all()
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                },
                data=json.dumps({"title": "Daily Checklist Reminder", "body": "Have you completed your daily checklist?"}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as ex:
            print("Failed to send notification:", repr(ex))
    return jsonify({'success': True})

def get_current_checklist():
    today = datetime.utcnow().date()
    checklist = Checklist.query.filter_by(date=today).first()
    if not checklist:
        checklist = Checklist(date=today)
        db.session.add(checklist)
        db.session.commit()
    return checklist

def reset_checklist():
    now = datetime.utcnow()
    if now.time() >= time(4, 0):
        tomorrow = now + timedelta(days=1)
        reset_time = datetime.combine(tomorrow, time(4, 0))
        delta = reset_time - now
        if delta.total_seconds() > 0:
            checklist = Checklist.query.filter_by(date=now.date()).first()
            if checklist:
                checklist.moral = False
                checklist.dedicated_time = False
                checklist.helped = False
                checklist.said_love = False
                checklist.fun = False
                db.session.commit()

def send_notifications_scheduler():
    with app.app_context():
        send_notifications()

scheduler = BackgroundScheduler()
scheduler.add_job(reset_checklist, 'interval', hours=24)
scheduler.add_job(send_notifications_scheduler, 'cron', hour='8,12,16,20')
scheduler.start()

def calculate_streaks():
    streaks = {'moral': 0, 'dedicated_time': 0, 'helped': 0, 'said_love': 0, 'fun': 0}
    streaks_end_date = datetime.utcnow().date()
    for field in streaks.keys():
        streak_count = 0
        consecutive_days = 0
        while True:
            checklist = Checklist.query.filter_by(date=streaks_end_date).first()
            if checklist and getattr(checklist, field):
                streak_count += 1
                consecutive_days += 1
                streaks_end_date -= timedelta(days=1)
            else:
                if streak_count < 2:
                    streak_count = 0
                break
        streaks[field] = streak_count
    return streaks

def get_time_left():
    now = datetime.utcnow()
    end_of_day = datetime.combine(now.date() + timedelta(days=1), time(4, 0))
    time_left = end_of_day - now
    return time_left

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_checklist, 'interval', hours=24)
    scheduler.add_job(send_notifications_scheduler, 'cron', hour='8,12,16,20')
    scheduler.start()

    app.run(debug=True)
