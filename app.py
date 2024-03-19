from flask import Flask, render_template, request, redirect, url_for
import cv2
import firebase_admin
from firebase_admin import credentials, storage, db
import os
import threading
import os
import apivideo
from apivideo.apis import VideosApi
from apivideo.exceptions import ApiAuthException

api_key = "CHLsi18A4DEKEKqMucO8tiRpqQDywKRc8nAUcA6hrSY"

# Set up the authenticated client
client = apivideo.AuthenticatedApiClient(api_key)

# if you rather like to use the sandbox environment:
# client = apivideo.AuthenticatedApiClient(api_key, production=False)
client.connect()

videos_api = VideosApi(client)

video_create_payload = {
    "title": "Progressive Test",
    "description": "test",
    "public": False,
    "tags": ["nature"]
}
# Create the container for your video and print the response
response = videos_api.create(video_create_payload)


# Retrieve the video ID, you can upload once to a video ID
video_id = response["video_id"]


session = videos_api.create_upload_progressive_session(video_id)


CHUNK_SIZE = 6000000

# This is our chunk reader. This is what gets the next chunk of data ready to send.
def read_in_chunks(file_object, CHUNK_SIZE):
    while True:
        data = file_object.read(CHUNK_SIZE)
        if not data:
            break
        yield data

# Upload your file by breaking it into chunks and sending each piece
def upload(file):
    content_name = str(file)
    content_path = os.path.abspath(file)

    f = open(content_path, "rb")
    index = 0
    offset = 0
    part_num = 1
    headers = {}

    for chunk in read_in_chunks(f, CHUNK_SIZE):
        offset = index + len(chunk)
        index = offset

        with open('chunk.part.' + str(part_num), 'wb') as chunk_file:
            chunk_file.write(chunk)
            chunk_file.close()

        with open('chunk.part.' + str(part_num), 'rb') as chunk_file:
            try:
                if len(chunk) == CHUNK_SIZE:
                    session.uploadPart(chunk_file)
                elif len(chunk) < CHUNK_SIZE:
                    download_url = session.uploadLastPart(chunk_file)["assets"]["mp4"]
                chunk_file.close()
            except Exception as e:
                print(e)

        os.remove('chunk.part.' + str(part_num))
        part_num += 1
        return download_url
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

    dataresult = upload(f'static/{video_filename}')

    data = {
        "name": name,
        "telephone": telephone,
        "address": address,
        "video_url": dataresult
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

