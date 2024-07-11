FROM python:3.8-alpine

RUN pip3 install requests PyYAML flask

EXPOSE 5142 8085

ADD opensyslog_helper.py opensyslog_syslog.py main_opensyslog.py restful_server.py /

ARG GIT_TAG=unknown
LABEL version=$GIT_TAG

CMD ["python", "-u", "./main_opensyslog.py"]
