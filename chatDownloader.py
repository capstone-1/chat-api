import requests
import json
import sys
import time
import csv
import pandas as pd
import numpy as np
from importlib import reload
from google.cloud import storage
from collections import OrderedDict

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

def convert_to_sec(time) : 
    splited_time = time.split(':')
    hours = int(splited_time[0])
    minutes = int(splited_time[1])
    seconds = int(splited_time[2])
    return (hours * 3600) + (minutes * 60) + seconds 

def convert_to_interval(idx) :
    end = idx * 120
    start = end - 120
    return str(start) + " - " + str(end)
def convert_to_start(time) :
    strip_str = time.strip()
    start = strip_str.split('-')[0]
    return int(start)
def convert_to_end(time) :
    strip_str = time.strip()
    end = strip_str.split('-')[1]
    return int(end)
  
def analysis(bucket_name,file_name):     
    chat_response = OrderedDict()
    #Chat Frequency Graph
    print("Start Analysis")
    df = pd.read_csv("chat.csv", names=['time', 'name', 'chat'])
    timeCountDf = df.groupby('time').count()['chat']  # 정렬 안되어 있는것
    sortedTimeCountDf = df['time'].value_counts()  # 시간별 채팅횟수 내림차순
    ax = timeCountDf.plot(title='chat numbers', figsize=(15, 5))
    fig = ax.get_figure()
    fig.savefig(str(file_name)+'.png')
    chat_frequency_url = upload_to_GCS(bucket_name, file_name)
    chat_response["chat_frequency_url"] = chat_frequency_url

    # Chat Edit Point
    time_df = pd.read_csv("chat.csv", names=['time', 'name', 'chat'])
    time_df['time'] = time_df['time'].apply(lambda x : convert_to_sec(x))
    
    max_time = time_df['time'].max()
    bins = np.arange(0,max_time,120)
    ind = np.digitize(time_df["time"], bins)
    time_df["idx"] = ind
    
    #Intermediate Result
    new_df = time_df["idx"].value_counts().rename_axis('time_index').reset_index(name='count_chat')
    new_df["time_index"] = new_df["time_index"].apply(lambda x : convert_to_interval(x))
    mask = new_df['time_index'].isin(['0 - 120', '120 - 240', '240 - 360'])
    new_df = new_df[~mask]
    count_mean = int(new_df["count_chat"].mean())
    new_df = new_df[new_df.count_chat > count_mean]

    ### For Response
    response_df = new_df.copy()
    response_df["start"] = response_df["time_index"].apply(lambda x : convert_to_start(x))
    response_df["end"] = response_df["time_index"].apply(lambda x : convert_to_end(x))

    response_df = response_df.drop(columns=['count_chat', 'time_index']).sort_values(by=["start"])
    chat_response["chat_edit_list"] = response_df.to_json(orient='records')
    print(chat_response)
    return chat_response
    
'''
    output = sortedTimeCountDf[sortedTimeCountDf == sortedTimeCountDf.max()]
    timeList = output.index.values
    timeList.sort()
    with open(str(file_name)+'_time.txt','w') as file:
        for time in timeList:
            file.write(time+'\n')
    print("Stop Analysis")

'''
    
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
    return file_name+ "/result/chat-frequency.png"

