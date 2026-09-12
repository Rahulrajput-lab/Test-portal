import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    results = db.relationship('TestResult', backref='student', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Seed initial test questions if empty
def seed_questions():
    if Question.query.count() == 0:
        sample_questions = [
            Question(
                question_text="Which data structure uses LIFO (Last In First Out)?",
                option_a="Queue", option_b="Stack", option_c="Array", option_d="Tree",
                correct_option="B"
            ),
            Question(
                question_text="What is the time complexity of binary search on a sorted array of size n?",
                option_a="O(n)", option_b="O(n log n)", option_c="O(log n)", option_d="O(1)",
                correct_option="C"
            ),
            Question(
                question_text="Which protocol is primarily used for securely transferring web pages over the internet?",
                option_a="FTP", option_b="HTTP", option_c="HTTPS", option_d="SMTP",
                correct_option="C"
            ),
            Question(
                question_text="In Python, which keyword is used to define an anonymous function?",
                option_a="def", option_b="inline", option_c="lambda", option_d="func",
                correct_option="C"
            )
        ]
        db.session.bulk_save_objects(sample_questions)
        db.session.commit()

# --- Routes ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Choose another.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    results = TestResult.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user=current_user, results=results)

@app.route('/test', methods=['GET', 'POST'])
@login_required
def take_test():
    questions = Question.query.all()
    if request.method == 'POST':
        score = 0
        total = len(questions)

        for q in questions:
            selected = request.form.get(f"q_{q.id}")
            if selected == q.correct_option:
                score += 1

        pct = round((score / total) * 100, 2) if total > 0 else 0
        res = TestResult(user_id=current_user.id, score=score, total_questions=total, percentage=pct)
        db.session.add(res)
        db.session.commit()

        return redirect(url_for('result', result_id=res.id))

    return render_template('test.html', questions=questions)

@app.route('/result/<int:result_id>')
@login_required
def result(result_id):
    res = TestResult.query.filter_by(id=result_id, user_id=current_user.id).first_or_404()
    return render_template('result.html', result=res)

with app.app_context():
    db.create_all()
    seed_questions()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
              
