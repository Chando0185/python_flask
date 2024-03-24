from flask import Flask, render_template, request, redirect, url_for
import firebase_admin
from firebase_admin import credentials, storage, db
import os
import secrets
import datetime

app = Flask(__name__)

# Initialize Firebase
cred = credentials.Certificate("services.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://facemexico-9f5e9-default-rtdb.firebaseio.com',  # Replace with your Firebase Realtime Database URL
    'storageBucket': 'facemexico-9f5e9.appspot.com' 
})
bucket = storage.bucket()
ref = db.reference('users')

from google.cloud import storage

# Initialize Firebase Storage client
storage_client = storage.Client.from_service_account_json("services.json")
bucket = storage_client.bucket("facemexico-9f5e9.appspot.com")

# Directory to store uploaded files
UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    ref = db.reference('users')
    videos = ref.get()
    return render_template('index.html', videos=videos)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    # Check if file is of type video/mp4
    if not file.mimetype.startswith('video/'):
        return 'Only video files are allowed'

    # Save video file to local directory
    filename = secrets.token_hex(8) + '_' + file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Upload video file to Firebase Storage
    blob = bucket.blob(filename)
    blob.upload_from_filename(file_path)

    # Generate video access token
    access_token = secrets.token_hex(16)

    # Get download URL
    video_url = blob.public_url

    # Save user information, video filename, and access token to Firebase Realtime Database
    name = request.form['name']
    telephone = request.form['telephone']
    address = request.form['address']

    user_data = {
        'name': name,
        'telephone': telephone,
        'address': address,
        'video_filename': filename,
        'video_token': access_token,
        'video_url': video_url
    }
    ref.push(user_data)

    os.remove(file_path)

    return redirect(url_for('index'))

@app.route('/generate_signed_url/<filename>')
def generate_signed_url(filename):
    blob = bucket.blob(filename)
    expiration = datetime.timedelta(hours=1)
    signed_url = blob.generate_signed_url(expiration=expiration, version="v4")
    print(signed_url)
    return signed_url

if __name__ == '__main__':
    app.run(debug=True)
