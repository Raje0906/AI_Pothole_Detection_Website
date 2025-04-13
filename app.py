from flask import Flask, render_template, request, send_file, session, redirect, url_for, flash, send_from_directory, jsonify
from flask_mail import Mail, Message
from functools import wraps
import os
from detect import detect_potholes
from generate_report import generate_report
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')  # Required for session management

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
DETECTION_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'detections')
REPORTS_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'reports')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Configure static folder
app.static_folder = 'static'
app.static_url_path = '/static'

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DETECTION_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login required decorator - MUST BE DEFINED BEFORE ANY ROUTES THAT USE IT
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database functions
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS detection_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        detected_path TEXT,
        report_path TEXT,
        has_potholes BOOLEAN NOT NULL,
        location TEXT,
        latitude TEXT,
        longitude TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def get_user_history(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in c.fetchall()]
    
    base_columns = ['filename', 'detected_path', 'report_path', 'has_potholes', 'date']
    location_columns = ['location', 'latitude', 'longitude']
    select_columns = base_columns + [col for col in location_columns if col in columns]
    
    query = f'''SELECT {", ".join(select_columns)} 
                FROM detection_history 
                WHERE user_id = ? 
                ORDER BY date DESC'''
    
    c.execute(query, (user_id,))
    history = c.fetchall()
    conn.close()
    
    return [
        {
            'filename': h[0],
            'detected_path': h[1],
            'report_path': h[2],
            'has_potholes': h[3],
            'date': datetime.strptime(h[4], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M'),
            'location': h[5] if len(h) > 5 and 'location' in columns else None,
            'latitude': h[6] if len(h) > 6 and 'latitude' in columns else None,
            'longitude': h[7] if len(h) > 7 and 'longitude' in columns else None
        }
        for h in history
    ]

def save_detection_history(user_id, filename, detected_path, report_path, has_potholes, location=None, latitude=None, longitude=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT INTO detection_history 
                 (user_id, filename, detected_path, report_path, has_potholes, location, latitude, longitude)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, filename, detected_path, report_path, has_potholes, location, latitude, longitude))
    conn.commit()
    conn.close()

def send_report_email(email, report_path):
    """Sends the generated report to the user's email."""
    try:
        msg = Message("Pothole Detection Report", recipients=[email])
        msg.body = "Attached is your pothole detection report."
        with app.open_resource(report_path) as pdf:
            msg.attach("pothole_report.pdf", "application/pdf", pdf.read())
        mail.send(msg)
        logger.info(f"Report sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

# Routes
@app.route("/")
def index():
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    return redirect(url_for('login'))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        try:
            if "file" not in request.files:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "No file uploaded"}), 400
                flash("No file uploaded")
                return redirect(request.url)

            file = request.files["file"]
            if file.filename == '':
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "No file selected"}), 400
                flash("No file selected")
                return redirect(request.url)

            if not allowed_file(file.filename):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "File type not allowed"}), 400
                flash("File type not allowed")
                return redirect(request.url)

            location = request.form.get("location")
            latitude = request.form.get("latitude")
            longitude = request.form.get("longitude")
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                is_video = filename.lower().endswith((".mp4", ".avi", ".mov"))
                detected_path, detections = detect_potholes(filepath, is_video)
                
                if detected_path is None:
                    raise Exception("Detection failed")

                has_potholes = len(detections) > 0
                detection_message = "🚧 Pothole Detected!" if has_potholes else "✅ No Potholes Found!"
                report_path = None

                if has_potholes:
                    logger.info("Potholes detected, generating report...")
                    # Get the correct path for the detected image
                    if detected_path.startswith('/static/'):
                        report_image_path = os.path.join(app.root_path, detected_path[1:])
                    else:
                        report_image_path = os.path.join(app.root_path, 'static', 'detections', os.path.basename(detected_path))
                    
                    logger.debug(f"Using image path for report: {report_image_path}")
                    report_path = generate_report(detections, report_image_path, location, latitude, longitude)
                    
                    if report_path:
                        logger.info(f"Report generated successfully: {report_path}")
                        # Get user's email from database
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        c.execute("SELECT email FROM users WHERE id = ?", (session['user_id'],))
                        user_email = c.fetchone()[0]
                        conn.close()
                        
                        # Send email with report
                        try:
                            full_report_path = os.path.join(app.root_path, report_path[1:])  # Remove leading slash
                            logger.debug(f"Sending report from path: {full_report_path}")
                            send_report_email(user_email, full_report_path)
                            logger.info(f"Report sent to {user_email}")
                        except Exception as e:
                            logger.error(f"Failed to send report email: {str(e)}")
                            logger.error(f"Report path: {full_report_path}")
                    else:
                        logger.error("Failed to generate report")
                        logger.error(f"Image path used: {report_image_path}")

                # Save to detection history
                save_detection_history(
                    session['user_id'],
                    filename,
                    detected_path,
                    report_path,
                    has_potholes,
                    location,
                    latitude,
                    longitude
                )

                # Prepare response
                response_data = {
                    "message": detection_message,
                    "detected_path": detected_path,
                    "has_potholes": has_potholes,
                    "success": True
                }
                
                if report_path:
                    response_data["report_path"] = report_path

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(response_data)
                
                flash(detection_message)
                return redirect(url_for('dashboard'))

            except Exception as e:
                logger.error(f"Error in detection process: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": str(e)}), 500
                flash("Error processing the image")
                return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": str(e)}), 500
            flash(f"Upload error: {str(e)}")
            return redirect(request.url)

    # GET request - render dashboard template
    history = get_user_history(session['user_id'])
    return render_template('dashboard.html', history=history)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (username, email, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!')
        finally:
            conn.close()
            
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!')
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        flash('Error downloading file: ' + str(e))
        return redirect(url_for('dashboard'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)

@app.route('/static/detections/<path:filename>')
def serve_detection(filename):
    """Serve detection result images."""
    try:
        return send_from_directory(DETECTION_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving detection file {filename}: {str(e)}")
        return "File not found", 404

@app.route('/reports/<path:filename>')
@login_required
def download_report(filename):
    try:
        return send_from_directory(REPORTS_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error serving report {filename}: {str(e)}")
        flash('Error downloading report')
        return redirect(url_for('dashboard'))

# Initialize the database when the app starts
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)