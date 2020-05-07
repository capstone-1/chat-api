from flask import Flask, request
from chatDownloader import *
app = Flask(__name__)
@app.route('/chat-api')
def chat_analysis():
    bucket_name = "capstone-sptt-storage"
    file_name = request.args.get("fileName")
    destination_file_name = "chat.csv"
    download_file(bucket_name, file_name, destination_file_name)
    return analysis(bucket_name, file_name)

if __name__ == "__main__":
    app.run()