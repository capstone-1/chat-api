'''
선정 방법 
1. Median Filter를 사용해  noise 제거 - OK
2. Local Minimum 구하기 (30분 간격을 나누기)
3. 임계값 이상의 값 구하기 (Local Minimum 중 가장 작은 값으로 선정)
4. 간격? 기존 : 앞뒤로 1분
5. 1분 간격에 위의 구간에 만족하는 피크가 있는 경우 구간 연결
'''
import math
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
  
def median_filter(data,filter_size) :
    for x in range(len(data)) : 
        median_list = []
        for index in range(x-filter_size, x+filter_size+1) : 
            if (index >= 0 and index < len(data)) :     
                median_list.append(data[index])
        data[x] =  get_median_value(median_list)
    return data

def get_median_value(median_list) : 
    median_idx = len(median_list)//2
    median_list.sort()
    return median_list[median_idx]

def get_frequency_graph_url(timeCountSeries, file_name, bucket_name) :
    ax = timeCountSeries.plot(title='chat numbers', figsize=(20, 5))
    fig = ax.get_figure()
    fig.savefig(str(file_name)+'.png')
    return upload_to_GCS(bucket_name, file_name)
    
def get_local_maximum_df(time_count_df):
    max_time = time_count_df['time'].max()
    bins = np.arange(0,max_time,900)
    ind = np.digitize(time_count_df["time"], bins)
    time_count_df["location"] = ind
    location_groups = time_count_df.groupby('location')
    local_maximum_df = pd.DataFrame(columns = ['time','chat_count', 'location'])
    for location, location_group in location_groups:
        local_maximum = location_group.sort_values(by='chat_count').tail(1)
        local_maximum_df = local_maximum_df.append(local_maximum)
    return local_maximum_df

def get_increase_df(time_count_df) :

    increase_threshold = math.ceil(time_count_df['chat_count'].mean())-1
    cond = ( time_count_df["chat_count"] - time_count_df["chat_count"].shift(-1) ) > increase_threshold
    increase_df = time_count_df[cond]
    print(increase_df)
    return increase_df

def get_interval_list(peak_df, local_maximum_df, time_count_df):
    peak_time_list = peak_df['time'].to_list()
    result_json = []
    for time in peak_time_list :
        start = time-60
        end = time+60
        local_maximum_list = local_maximum_df.query('time<=@time')['chat_count'].tail(1).to_list()
		
        # if (len(local_maximum_list) > 0) :
        #     local_maximum = local_maximum_list[0]

        #     end_result_df = time_count_df.query('time>@end & time< @end+60')
        #     end_result = end_result_df.query('chat_count>=@local_maximum')

        #     if (len(end_result['time'].to_list()) == 0) :
        #         print("Origin End : ", end)
        #     else :
        #         end = end_result['time'].to_list()[0]
        #         peak_time_list.append(end+60)
        #         print("Changed End : ", end)
        chat_interval = OrderedDict()
        chat_interval['start'] = start
        chat_interval['end'] = end
        result_json.append(chat_interval)
    return result_json

def remove_duplicate_interval(result_json):
    response_json = []
    for idx, val in enumerate(result_json) :
        if (idx == len(result_json)-1) : continue
        start = val['start']
        end = val['end']
        next_start = result_json[idx+1]['start']
        next_end = result_json[idx+1]['end']
        chat_interval = OrderedDict()

        if (next_start <= end) : 
            end = next_end
            chat_interval['start'] = start
            chat_interval['end'] = end
            result_json[idx+1] = chat_interval
        else:
            chat_interval['start'] = start
            chat_interval['end'] = end
            response_json.append(chat_interval)
            
    return response_json

def analysis(bucket_name,file_name):     
    chat_response = OrderedDict()
    ############### Chat Frequency Graph
    print("Start Analysis")
    df = pd.read_csv("chat.csv", names=['time', 'name', 'chat'])
    timeCountSeries = df.groupby('time').count()['chat'] 
    timeCountSeries = median_filter(timeCountSeries, 5)
    chat_response["chat_frequency_url"] = get_frequency_graph_url(timeCountSeries, file_name, bucket_name)

    time_count_df = timeCountSeries.to_frame().reset_index()
    time_count_df.columns=['time','chat_count']
    time_count_df['time'] = time_count_df['time'].apply(lambda x: convert_to_sec(x))
    time_count_df = time_count_df.query('time>300 & time < (time.max()-300)')
    ############### Local Minimum
    local_maximum_df = get_local_maximum_df(time_count_df)

    ############### Chat Edit Point
    increase_df = get_increase_df(time_count_df)
    
    '''구간 선출
        minimum : 앞뒤 1분 
        겸치는 구간은 합침   
        1분사이에 localminumum이랑 같은거 있으면 더 늘려야 하는데
    '''
    peak_df = increase_df.append(local_maximum_df)
    peak_df = peak_df.sort_values(by='time').drop_duplicates('time', keep='first')    
    result_json = get_interval_list(peak_df, local_maximum_df, time_count_df)
    print ("result_json : " + str(result_json))
    response_json = remove_duplicate_interval(result_json)
    chat_response["chat_edit_list"] = response_json 

    # convert_to_json(response_df)
    return chat_response


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

