from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# Настройка базы данных
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'banketam.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели (таблицы БД)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Новая')
    reviews = db.relationship('Review', backref='booking', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)

# Маршруты
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']

        if len(login) < 6:
            flash('Логин должен быть минимум 6 символов', 'error')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash('Пароль должен быть минимум 8 символов', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(login=login).first():
            flash('Такой логин уже существует', 'error')
            return redirect(url_for('register'))

        new_user = User(login=login, password_hash=generate_password_hash(password),
                        full_name=full_name, phone=phone, email=email)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.query.filter_by(login=login).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Вы вошли!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверный логин или пароль', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    bookings = Booking.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', user=user, bookings=bookings)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        room = request.form['room']
        date = request.form['date']
        payment = request.form['payment']
        new_booking = Booking(user_id=session['user_id'], room_name=room, start_date=date, payment_method=payment)
        db.session.add(new_booking)
        db.session.commit()
        flash('Заявка создана!', 'success')
        return redirect(url_for('profile'))
    return render_template('booking.html')

@app.route('/add_review/<int:booking_id>', methods=['POST'])
def add_review(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    booking = Booking.query.get(booking_id)
    if booking and booking.user_id == session['user_id'] and booking.status != 'Новая':
        text = request.form['review_text']
        new_review = Review(booking_id=booking.id, text=text)
        db.session.add(new_review)
        db.session.commit()
        flash('Отзыв успешно добавлен!', 'success')
    return redirect(url_for('profile'))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.login != 'Admin26':
        flash('Доступ только для администратора', 'error')
        return redirect(url_for('profile'))
    
    # Логика фильтрации и сортировки
    status_filter = request.args.get('status', 'Все')
    sort_order = request.args.get('sort', 'desc')

    query = Booking.query
    if status_filter != 'Все':
        query = query.filter_by(status=status_filter)
    
    if sort_order == 'asc':
        query = query.order_by(Booking.start_date.asc())
    else:
        query = query.order_by(Booking.start_date.desc())

    all_bookings = query.all()
    return render_template('admin.html', bookings=all_bookings, current_status=status_filter, current_sort=sort_order)

@app.route('/admin/status/<int:booking_id>/<status>')
def change_status(booking_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.login != 'Admin26':
        return redirect(url_for('profile'))
    booking = Booking.query.get(booking_id)
    if booking:
        booking.status = status
        db.session.commit()
        flash('Статус изменен', 'success')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(login='Admin26').first():
            admin = User(login='Admin26', password_hash=generate_password_hash('Demo20'),
                         full_name='Администратор', phone='+7 999 000-00-00', email='admin@banketam.net')
            db.session.add(admin)
            db.session.commit()
    print('Сервер запущен: http://127.0.0.1:5000')
    app.run(debug=True)