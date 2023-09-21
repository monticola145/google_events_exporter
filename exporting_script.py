import time
import logging

from os.path import dirname, join

from dotenv import load_dotenv

from GoogleAPI.google_api import GoogleCalendarAPI


logging.basicConfig(
    level=logging.INFO,
    encoding="UTF-8",
    filename="py_log.log",
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
)

logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

RETRY_TIME = 60


def main():
    while True:
        GoogleCalendarAPI()
        logging.info("Скрипт ушёл на отдых")
        time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
