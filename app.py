from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/eventbooking'
app.config['SECRET_KEY'] = 'secretkey'
mongo = PyMongo(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Ensure image folder exists
if not os.path.exists('static/images'):
    os.makedirs('static/images')

# User class
class User(UserMixin):
    def __init__(self, user_id, username, password, role):
        self.id = user_id
        self.username = username
        self.password = password
        self.role = role

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data['_id'], user_data['username'], user_data['password'], user_data['role'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')



# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        mongo.db.users.insert_one({'username': username, 'password': hashed_password, 'role': role})
        flash("Registration successful! Please log in.", 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            logged_in_user = User(user['_id'], user['username'], user['password'], user['role'])
            login_user(logged_in_user)
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# Admin Dashboard
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    if request.method == 'POST':
        event_name = request.form['event_name']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        time = request.form['time']
        organizing = request.form['organizing']
        tickets_available = request.form['tickets_available']
        fee_payment = request.form['fee_payment']
        picture = request.files['picture']

        picture_path = f"static/images/{picture.filename}"
        picture.save(picture_path)

        event_data = {
            "event_name": event_name,
            "start_date": start_date,
            "end_date": end_date,
            "time": time,
            "organizing": organizing,
            "tickets_available": tickets_available,
            "fee_payment": fee_payment,
            "picture": f"images/{picture.filename}",
            "status": "upcoming",
            "feedbacks": [],
            "live_link": ""
        }

        mongo.db.events.insert_one(event_data)
        flash("Event posted successfully!", 'success')

    events = mongo.db.events.find()
    return render_template('admin_dashboard.html', events=events)

# User Dashboard
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if current_user.role != 'user':
        return redirect(url_for('home'))
    events = mongo.db.events.find()
    return render_template('user_dashboard.html', events=events)

# Event Details
@app.route('/event/<event_id>', methods=['GET', 'POST'])
@login_required
def event_detail(event_id):
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    if request.method == 'POST':
        feedback = request.form['feedback']
        mongo.db.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$push": {"feedbacks": feedback}}
        )
        flash("Feedback submitted successfully.", 'success')
    return render_template('event_detail.html', event=event)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']
        message = request.form['message']

        mongo.db.contacts.insert_one({
            "name": name,
            "email": email,
            "address": address,
            "message": message,
            "timestamp": datetime.utcnow()
        })

        flash("Your message has been received. We'll get back to you soon!", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
