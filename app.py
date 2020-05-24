from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from chatDownloader import *
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/chat-api')
@cross_origin()
def chat_analysis():
    bucket_name = "capstone-sptt-storage"
    file_name = request.args.get("fileName")
    destination_file_name = "chat.csv"
    download_file(bucket_name, file_name, destination_file_name)
    return jsonify(analysis(bucket_name, file_name))

if __name__ == "__main__":
    app.run()