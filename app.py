
from flask import Flask, render_template, request, redirect, url_for
import cv2
import firebase_admin
from firebase_admin import credentials, storage, db
import os
import threading

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("services.json")  # Replace with the path to your Firebase credentials file
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://facemexico-9f5e9-default-rtdb.firebaseio.com',  # Replace with your Firebase Realtime Database URL
    'storageBucket': 'facemexico-9f5e9.appspot.com'  # Replace with your Firebase Storage bucket name
})

# Firebase Storage
bucket = storage.bucket()

# Firebase Database
database = db.reference()
import uuid
# Video capture function
def capture_video(name, telephone, address):
    cap = cv2.VideoCapture(0)
    codec = cv2.VideoWriter_fourcc(*'XVID')
    video_filename = str(uuid.uuid4()) + '.avi'
    out = cv2.VideoWriter(f'static/{video_filename}', codec, 20.0, (640, 480))
    recording_time = 10  # in seconds
    start_time = cv2.getTickCount()

    while True:
        ret, frame = cap.read()
        out.write(frame)
        current_time = cv2.getTickCount()
        if (current_time - start_time) / cv2.getTickFrequency() > recording_time:
            break

    cap.release()
    out.release()

    # Upload video to Firebase Storage
    blob = bucket.blob(f"videos/{video_filename}")
    blob.upload_from_filename(f'static/{video_filename}')

    # Get the download URL of the uploaded video
    download_url = blob.generate_signed_url(expiration=3600)

    # Save information to Firebase Database
    data = {
        "name": name,
        "telephone": telephone,
        "address": address,
        "video_url": download_url
    }
    database.child("contacts").push(data)

    # Remove temporary video file
    os.remove(f'static/{video_filename}')


@app.route('/')
def index():
    ref = db.reference('contacts')
    videos = ref.get()
    return render_template('index.html', videos=videos)

@app.route('/submit', methods=['POST'])
def submit():
    # Extract form data
    name = request.form['name']
    telephone = request.form['telephone']
    address = request.form['address']

    # Start recording video in a separate thread
    threading.Thread(target=capture_video, args=(name, telephone, address)).start()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

