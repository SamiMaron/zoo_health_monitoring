import os
import cv2
import numpy as np
import psycopg2
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from datetime import datetime


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './static/uploads'

# Create DAta Base PostgreSQL
def init_db(): 
    conn = psycopg2.connect("dbname=animal_monitoring user=postgres password=yourpassword")
    cur = conn.cursor()
    
    # Create Tables 
    cur.execute('''CREATE TABLE IF NOT EXISTS animals 
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    species TEXT NOT NULL
                  );''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    animal_id INT REFERENCES animals(id),
                    image_path TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_score REAL
                  );''')
    
    conn.commit()
    cur.close()
    conn.close()


def save_image_data(animal_id, image_path, change_score):
    conn = psycopg2.connect("dbname=animal_monitoring user=postgres password=yourpassword")
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO images (animal_id, image_path, upload_date, change_score)
        VALUES (%s, %s, %s, %s)
    ''', (animal_id, image_path, datetime.now(), change_score))
    
    conn.commit()
    cur.close()
    conn.close()


def compare_images(img1_path, img2_path):
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)
    
    img1_resized = cv2.resize(img1, (500, 500))
    img2_resized = cv2.resize(img2, (500, 500))
    
    diff = cv2.absdiff(img1_resized, img2_resized)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    score = np.sum(gray_diff)
    
    return score


def detect_skin_issues(image_path):
    img = cv2.imread(image_path)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_img, cv2.CV_64F).var()
    
    if laplacian_var < 50:
        return "Potential skin issue detected"
    return "No skin issues detected"


import smtplib
from email.mime.text import MIMEText

def send_alert_email(animal_name, change_score):
    sender_email = "zoo@zoo.com"
    receiver_email = "staff@zoo.com"
    subject = f"Health Alert: Significant change detected in {animal_name}"
    body = f"A significant change was detected with a score of {change_score}."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    with smtplib.SMTP("smtp.zoo.com", 587) as server:
        server.starttls()
        server.login(sender_email, "password")
        server.sendmail(sender_email, receiver_email, msg.as_string())

# Api Uploud Phothos
@app.route('/upload', methods=['POST'])
def upload_image():
    animal_id = request.form['animal_id']
    file = request.files['file']
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Compare Phothos
        previous_image_path = get_last_image(animal_id)
        if previous_image_path:
            change_score = compare_images(previous_image_path, filepath)
            save_image_data(animal_id, filepath, change_score)
            
            if change_score > 50000:
                send_alert_email("Elephant", change_score)
                return jsonify({"message": "Significant change detected", "change_score": change_score})
            else:
                return jsonify({"message": "No significant change", "change_score": change_score})
        else:
            save_image_data(animal_id, filepath, 0)
            return jsonify({"message": "No previous image for comparison"})

# Main Page
@app.route('/')
def index():
    return render_template('index.html')


def get_last_image(animal_id):
    conn = psycopg2.connect("dbname=animal_monitoring user=postgres password=yourpassword")
    cur = conn.cursor()
    
    cur.execute('''SELECT image_path FROM images WHERE animal_id = %s ORDER BY upload_date DESC LIMIT 1''', (animal_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result[0] if result else None

if __name__ == '__main__':
    init_db()  # Create Data Base
    app.run(debug=True)
