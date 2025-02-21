
import os
import cv2
import numpy as np
import sqlite3
import threading
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from slack_sdk import WebClient
import logging

# הגדרות Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './static/uploads'
app.config["DEBUG"] = True

# הגדרת חיבור Slack API
slack_client = WebClient(token="your-slack-api-token")
SLACK_CHANNEL = "#alerts"

# ודא שהתיקיה קיימת
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# אתחול לוגים
logging.basicConfig(level=logging.DEBUG)

# פונקציה לאתחול מסד הנתונים
def init_db():
    try:
        conn = sqlite3.connect('animal_monitoring.db')
        cur = conn.cursor()

        cur.execute('''CREATE TABLE IF NOT EXISTS animals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        species TEXT NOT NULL
                    );''')

        cur.execute('''CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        animal_id INTEGER REFERENCES animals(id),
                        image_path TEXT NOT NULL,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        change_score REAL,
                        detected_species TEXT,
                        issue_detected TEXT
                    );''')

        conn.commit()
        cur.close()
        conn.close()
        logging.info("Database initialized successfully")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")

# פונקציה לזיהוי חיות בתמונה
def detect_animal(image_path):
    try:
        animal_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalcatface.xml')
        img = cv2.imread(image_path)
        if img is None:
            logging.error(f"Failed to load image at {image_path}")
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        animals = animal_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        detected_species = []
        for (x, y, w, h) in animals:
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            detected_species.append("Cat")

        return detected_species
    except Exception as e:
        logging.error(f"Error in animal detection: {e}")
        return []

# פונקציה לאיתור אזורי בעיה בעור
def detect_skin_issues(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            logging.error(f"Failed to load image at {image_path}")
            return "Error detecting skin issues"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contour_count = len(cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0])

        if contour_count > 10:
            return "Potential skin issue detected"
        return "No issues detected"
    except Exception as e:
        logging.error(f"Error in skin issue detection: {e}")
        return "Error detecting skin issues"

# פונקציה להשוואת תמונות
def compare_images(img1_path, img2_path):
    try:
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        if img1 is None or img2 is None:
            logging.error(f"Failed to load images for comparison: {img1_path}, {img2_path}")
            return 0
        img1_resized = cv2.resize(img1, (500, 500))
        img2_resized = cv2.resize(img2, (500, 500))
        diff = cv2.absdiff(img1_resized, img2_resized)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        score = np.sum(gray_diff)

        logging.debug(f"Comparison score: {score}")
        return score
    except Exception as e:
        logging.error(f"Error comparing images: {e}")
        return 0

# שמירת מידע תמונה במסד הנתונים
def save_image_data(animal_id, image_path, change_score, detected_species, issue_detected):
    try:
        conn = sqlite3.connect('animal_monitoring.db')
        cur = conn.cursor()

        cur.execute(''' 
            INSERT INTO images (animal_id, image_path, upload_date, change_score, detected_species, issue_detected)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (animal_id, image_path, datetime.now(), change_score, detected_species, issue_detected))

        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Image data saved for animal_id {animal_id} at {image_path}")
    except sqlite3.Error as e:
        logging.error(f"Error saving image data: {e}")

# שליחת התראות דרך Slack
def send_slack_alert(animal_name, change_score):
    try:
        message = f"*Alert:* Significant change detected in {animal_name} (Change Score: {change_score})"
        slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
        logging.info(f"Slack alert sent for {animal_name} with change score: {change_score}")
    except Exception as e:
        logging.error(f"Error sending Slack alert: {e}")

# פונקציה לקבלת התמונה האחרונה של בעל חיים
def get_last_image(animal_id):
    try:
        conn = sqlite3.connect('animal_monitoring.db')
        cur = conn.cursor()
        cur.execute("SELECT image_path FROM images WHERE animal_id = ? ORDER BY upload_date DESC LIMIT 1", (animal_id,))
        last_image = cur.fetchone()
        conn.close()
        if last_image:
            return last_image[0]
        else:
            return None
    except sqlite3.Error as e:
        logging.error(f"Error fetching last image: {e}")
        return None

# API להעלאת תמונות
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Debugging - להדפיס את הנתונים שמתקבלים ב-POST
        logging.debug(f"Received form data: {request.form}")
        logging.debug(f"Received files: {request.files}")

        # לוודא שיש animal_id ב-form data
        if 'animal_id' not in request.form:
            logging.error("animal_id is missing from the form data")
            return jsonify({"error": "animal_id is required"}), 400

        animal_id = request.form['animal_id']
        file = request.files.get('file')

        # לוודא שהועלתה תמונה
        if not file:
            logging.error("No file uploaded")
            return jsonify({"error": "No file uploaded"}), 400

        # טיפול בשגיאות אם הקובץ לא תקין
        if file and file.filename != '' and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ['jpg', 'jpeg', 'png']:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Debugging - לבדוק אם הקובץ נשמר כראוי
            logging.debug(f"Saving file to: {filepath}")

            # בדוק אם התמונה הועלתה בהצלחה
            if not os.path.exists(filepath):
                logging.error(f"Uploaded file not found at {filepath}")
                return jsonify({"error": "Uploaded file not found"}), 500

            # קבלת התמונה האחרונה להשוואה
            previous_image_path = get_last_image(animal_id)
            detected_species = detect_animal(filepath)
            issue_detected = detect_skin_issues(filepath)

            # השוואה בין התמונות במידה וישנה תמונה קודמת
            if previous_image_path:
                change_score = compare_images(previous_image_path, filepath)
                save_image_data(animal_id, filepath, change_score, ", ".join(detected_species), issue_detected)

                if change_score > 50000:
                    threading.Thread(target=send_slack_alert, args=("Elephant", change_score)).start()
                    return jsonify({"message": "Significant change detected", "change_score": change_score, "detected_species": detected_species, "issue": issue_detected})
                else:
                    return jsonify({"message": "No significant change", "change_score": change_score, "detected_species": detected_species, "issue": issue_detected})
            else:
                save_image_data(animal_id, filepath, 0, ", ".join(detected_species), issue_detected)
                return jsonify({"message": "No previous image for comparison", "detected_species": detected_species, "issue": issue_detected})
        else:
            logging.error("Invalid file type")
            return jsonify({"error": "Invalid file type"}), 400

    except Exception as e:
        logging.error(f"Error in image upload: {e}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

# route לדף הבית
@app.route('/')
def home():
    return render_template('index.html')  # החזר דף HTML

# רוץ את האפליקציה
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
