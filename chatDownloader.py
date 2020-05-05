import requests
import json
import sys
import time
import csv
import pandas as pd
from importlib import reload
from google.cloud import storage

def doubleDigit(num):
    if num < 10 :
        return '0'+str(num)
    else:
        return str(num)


def main(v_id,c_id):
    if sys.version_info[0] == 2:
        reload(sys)
        sys.setdefaultencoding('utf-8')
    
    
    videoId = v_id
    clientId = c_id
    

    chat = []
    time = []
    user = []
    
    nextCursor = ''
    
    params = {}
    params['client_id'] = clientId
    
    
    i = 0
    while True :
        if i == 0 :
            URL = 'https://api.twitch.tv/v5/videos/'+videoId+'/comments?content_offset_seconds=0' 
            i += 1
        else:
            URL = 'https://api.twitch.tv/v5/videos/'+videoId+'/comments?cursor=' 
            URL +=  nextCursor   
            

        response = requests.get(URL, params=params)
        
        j = json.loads(response.text)
        # with open('api.json','a',encoding='utf-8') as file:
        #     json.dump(j,file,indent='\t',ensure_ascii=False)
        for k in range(0,len(j["comments"])):
            timer = j["comments"][k]["content_offset_seconds"]
            
            timeMinute = int(timer/60)

            if timeMinute >= 60 :
                timeHour = int(timeMinute/60)
                timeMinute %= 60
            else :
                timeHour = int(timeMinute/60)
    
            timeSec = int(timer%60)
            
            time.append(doubleDigit(timeHour)+':'+doubleDigit(timeMinute)+':'+doubleDigit(timeSec))
            user.append(j["comments"][k]["commenter"]["display_name"])
            chat.append(j["comments"][k]["message"]["body"])
        if '_next' not in j:
            break
        
        nextCursor = j["_next"]

    f = open(videoId+".csv", mode='w',encoding='utf-8-sig',newline='')
    wr = csv.writer(f)
    for x in range(0, len(time)):
        tmp = [str(time[x]), str(user[x]), str(chat[x])]
        wr.writerow(tmp)
    f.close()

def analysis(file_name):    
    print("Start Analysis")
    df = pd.read_csv("chat.csv", names=['time', 'name', 'chat'])
    timeCountDf = df.groupby('time').count()['chat']  # 정렬 안되어 있는것
    sortedTimeCountDf = df['time'].value_counts()  # 시간별 채팅횟수 내림차순
    ax = timeCountDf.plot(title='chat numbers', figsize=(15, 5))
    fig = ax.get_figure()
    fig.savefig(str(file_name)+'.png')
    output = sortedTimeCountDf[sortedTimeCountDf == sortedTimeCountDf.max()]
    timeList = output.index.values
    timeList.sort()
    with open(str(file_name)+'_time.txt','w') as file:
        for time in timeList:
            file.write(time+'\n')
    print("Start Analysis")
     
def download_file(bucket_name, file_name, destination_file_name):
    print("Start Download File")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    source_blob_name= file_name+ "/source/" + file_name + ".csv"
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print("End Download File")

def upload_to_GCS(bucket_name, file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    png_blob_name = bucket.blob(file_name+ "/result/chat-frequency.png")
    png_blob_name.upload_from_filename( str(file_name) + ".png" )

    chat_edit_point_blob_name = bucket.blob(file_name + "/result/chat-edit-point.txt")
    chat_edit_point_blob_name.upload_from_filename(str(file_name) + "_time.txt")