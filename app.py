from flask import Flask, render_template, request, redirect, url_for, send_file
import firebase_admin
from firebase_admin import credentials, storage, db
import os
import secrets
import csv
import datetime
from flask import jsonify
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
    # Extract user information from the form
    name = request.form['name']
    telephone = request.form['telephone']
    address = request.form['address']

    # Check if user with the same name, telephone, and address already exists
    existing_users = db.reference('users').order_by_child('name').equal_to(name).get()

    if existing_users:
        for user_key, user_data in existing_users.items():
            if user_data.get('telephone') == telephone and user_data.get('address') == address:
                # User with same name, telephone, and address already exists, show alert
                return render_template('alert.html', message='User with the same name, telephone, and address already exists!'), 400

    # If user doesn't exist, proceed with upload
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
    expiration = datetime.timedelta(seconds=604800)
    signed_url = blob.generate_signed_url(expiration=expiration, version="v4")

    # Save user information, video filename, and access token to Firebase Realtime Database
    promotor = request.form['promotor']

    user_data = {
        'name': name,
        'telephone': telephone,
        'address': address,
        'promotor': promotor,
        'video_filename': filename,
        'video_token': access_token,
        'video_url': signed_url
    }
    ref.push(user_data)

    os.remove(file_path)

    return redirect(url_for('index'))

@app.route('/generate_signed_url/<filename>')
def generate_signed_url(filename):
    blob = bucket.blob(filename)
    expiration = datetime.timedelta(hours=1)
    signed_url = blob.generate_signed_url(expiration=expiration, version="v4")
    return signed_url

# Add this route to your Flask app to display all submitted videos
@app.route('/submitted_videos')
def submitted_videos():
    ref = db.reference('users')
    videos = ref.get()
    if not videos:
        videos = {}
    return render_template('submitted_videos.html', videos=videos)

@app.route('/promotor')
def promotor():
    # Get promotor from URL query parameter
    promotor_name = request.args.get('name', '')  # Default to empty string if not provided
    return render_template('index.html', promotor=promotor_name)

@app.route('/export_csv')
def export_csv():
    ref = db.reference('users')
    users_data = ref.get()

    # Define CSV file path
    csv_file_path = 'users_data.csv'

    # Write data to CSV file
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = ['Name', 'Telephone', 'Address']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for key, data in users_data.items():
            writer.writerow({'Name': data['name'], 'Telephone': data['telephone'], 'Address': data['address']})

    # Return the path to the generated CSV file for download
    return send_file(csv_file_path, as_attachment=True)
# Delete video and corresponding entry from Firebase
# Delete video and corresponding entry from Firebase
@app.route('/delete/<string:key>', methods=['POST'])
def delete_video(key):
    database = db.reference('users')
    user_data = database.child(key).get()

    # Delete video file from storage
    filename = user_data.get('video_filename', None)
    if filename:
        blob = bucket.blob(filename)
        blob.delete()

    # Delete database entry
    database.child(key).delete()

    return redirect(url_for('submitted_videos'))
if __name__ == '__main__':
    app.run(debug=True)
