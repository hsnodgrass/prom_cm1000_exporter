FROM python:3.8-alpine
COPY ./requirements.txt /usr/local/
WORKDIR /usr/local
RUN pip install -r requirements.txt
COPY ./scrape_cm1000.py /usr/local/
ENTRYPOINT [ "python", "/usr/local/scrape_cm1000.py" ]