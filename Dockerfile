FROM python:3.8-alpine
COPY ./ /usr/local
WORKDIR /usr/local
RUN pip install -r requirements.txt
ENTRYPOINT [ "python", "/usr/local/scrape_cm1000.py" ]