from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
import random
from werkzeug.utils import secure_filename
from datetime import datetime
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load questions from Excel file
QUESTIONS_FILE = os.path.join(UPLOAD_FOLDER, 'questions.xlsx')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return []
    df = pd.read_excel(QUESTIONS_FILE)
    questions = []
    for _, row in df.iterrows():
        question = {
            'type': row['type'],
            'question': row['question'],
            'options': [row['option1'], row['option2'], row['option3'], row['option4']],
            'answer': row['answer']
        }
        if row['type'] == 'image' or row['type'] == 'text_image':
            question['image_url'] = row['image_url']
        questions.append(question)
    return questions

def get_db_connection():
    import os
    DATABASE_URL = os.environ.get('DATABASE_URL')
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

@app.route('/')
def home():
    return render_template('register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Collect form data
        name = request.form['name']
        phone = request.form['phone']
        experience = request.form['experience']
        company = request.form['company']
        notice_period = request.form['notice_period']

        # Save data to session
        session['username'] = name

        # Save registration data to PostgreSQL
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                name TEXT,
                phone TEXT,
                experience TEXT,
                company TEXT,
                notice_period TEXT
            )
        ''')
        cur.execute('''
            INSERT INTO registrations (timestamp, name, phone, experience, company, notice_period)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (datetime.now(), name, phone, experience, company, notice_period))
        conn.commit()
        cur.close()
        conn.close()
        """

        # Load and shuffle questions
        questions = load_questions()
        random.shuffle(questions)
        session['questions'] = questions
        session['score'] = 0
        session['q_index'] = 0

        return redirect(url_for('quiz'))

    return render_template('register.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('home'))
    if file and allowed_file(file.filename):
        filename = secure_filename('questions.xlsx')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        flash('File successfully uploaded')
        return redirect(url_for('home'))
    else:
        flash('Invalid file format. Please upload an Excel (.xlsx) file.')
        return redirect(url_for('home'))

@app.route('/quiz')
def quiz():
    questions = session.get('questions', [])
    q_index = session.get('q_index', 0)
    score = session.get('score', 0)

    if not questions or q_index >= len(questions):
        return render_template('result.html', score=score, total=len(questions))

    question = questions[q_index]
    return render_template('quiz.html', question=question, q_index=q_index, score=score)

@app.route('/answer', methods=['POST'])
def answer():
    selected_index = int(request.form['option'])
    q_index = session.get('q_index', 0)
    score = session.get('score', 0)
    questions = session.get('questions', [])

    current_question = questions[q_index]
    selected_answer = current_question['options'][selected_index]
    correct_answer = current_question['answer']

    if selected_answer.strip().lower() == correct_answer.strip().lower():
        score += 1

    session['score'] = score
    session['q_index'] = q_index + 1

    return redirect(url_for('quiz'))


if __name__ == '__main__':
    app.run(debug=True)