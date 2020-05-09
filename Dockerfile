FROM ubuntu:16.04
WORKDIR /root
EXPOSE 5000

ENV PROJ_NAME=static-protocol-264107
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY ./*.py /root/ 

RUN apt-get -y update && apt-get -y install python3 python3-pip curl 
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-sdk -y

COPY ./capstone-sptt.json /root/credential_key.json
RUN gcloud auth activate-service-account --key-file=credential_key.json && gcloud config set project $PROJ_NAME

RUN pip3 install --upgrade pip && pip3 install --upgrade google-cloud-storage && pip3 install --upgrade google-cloud-speech && pip3 install flask flask_cors
RUN pip3 install pandas matplotlib

RUN gcloud auth activate-service-account --key-file credential_key.json
ENV GOOGLE_APPLICATION_CREDENTIALS="/root/credential_key.json"

ENTRYPOINT [ "flask", "run" , "--host",  "0.0.0.0"]