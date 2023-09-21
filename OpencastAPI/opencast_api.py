import codecs
import json
import os
import traceback
from datetime import datetime, timedelta
import logging
from os.path import dirname, join

import pytz
import requests
from dotenv import load_dotenv

from OpencastAPI.series_creator import series_poster

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


class OpencastAPI:
    def __init__(self):
        self.api_url = os.getenv("OPENCAST_API_URL")

    def time_transformer(self, time=None):
        try:
            if "Z" not in time:
                return (
                    "T".join(
                        (
                            str(
                                datetime.strptime(
                                    time.split("+")[0], "%Y-%m-%d"
                                ).astimezone(pytz.UTC)
                            )[:19]
                        ).split(" ")
                    )
                    + ".000Z"
                )
            else:
                return (
                    "T".join(
                        str(
                            datetime.strptime(
                                " ".join(time.split("Z")[0].split("T")),
                                "%Y-%m-%d %H:%M:%S",
                            )
                            + timedelta(hours=0)
                        ).split(" ")
                    )
                    + ".000Z"
                )
                #  создатели опенкаста обожают туда-сюда дёргать время, поэтому редактируйте timedelta(hours=n) в зависимости от смещения от целевого времени при постинге
        except Exception:
            return (
                "T".join(
                    (
                        str(
                            datetime.strptime(
                                time.split("+")[0], "%Y-%m-%dT%H:%M:%S"
                            ).astimezone(pytz.UTC)
                        )[:19]
                    ).split(" ")
                )
                + ".000Z"
            )
            pass

    def events_cleaner(self):
        logging.info("НАЧИНАЕТСЯ ЧИСТКА ЭВЕНТОВ")
        try:
            google_events_ids = []
            opencast_events_ids = []
            response_check = requests.get(
                f"{self.api_url}/events/",
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            for event in list(
                filter(
                    lambda x: x["start"]
                    >= datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000"),
                    response_check.json(),
                )
            ):
                if len(event["description"].split("ID: ")) > 1:
                    google_events_ids.append(event["description"].split("ID: ")[1])
                    opencast_events_ids.append(event["identifier"])
            return dict(zip(google_events_ids, opencast_events_ids))

        except Exception as error:
            error_msg = f"Error: {error}\n{traceback.format_exc()}"
            logging.error(error_msg)

    def delete_event(self, deleting_event_id=None):
        try:
            logging.info("При чисте обнаружен эвент-сирота")
            response = requests.delete(
                f"{self.api_url}/events/{deleting_event_id}",
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            if response.status_code == 204:
                logging.info("Эвент удалён\n")
            else:
                logging.info("Что-то пошло не так при удалении эвента, пропускаем")
                pass

        except Exception as error:
            error_msg = f"Error: {error}\n{traceback.format_exc()}"
            logging.error(error_msg)
            pass

    def post_event(
        self,
        title=None,
        description=None,
        subject=None,
        rightsHolder=None,
        loicense=None,
        isPartOf=None,
        creator=None,
        contributor=None,
        source=None,
        google_event_id=None,
        calendar_id=None,
        start_time=None,
        end_time=None,
        created=None,
    ):
        """Принимает метаданные event'а из Google Calendar и
        использует их при создании event'а в Opencast, затем
        возвращает id созданного event'а
        """
        try:
            response_check = requests.get(
                f"{self.api_url}/events/",
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            with open("OpencastAPI/the_jsoniest.json", "r") as openfile:
                location = json.load(openfile)
                location = location[0]["mapping"][0][calendar_id]

            with open("OpencastAPI/the_jsoniest.json") as openfile:
                acl = json.load(openfile)
                acl = acl[0]["acl"]
                acl = json.dumps(acl, ensure_ascii=False)
            with codecs.open(
                "OpencastAPI/the_jsoniest.json", "r", encoding="utf-8"
            ) as openfile:
                metadata = json.load(openfile)
                metadata = metadata[0]["metadata"]
                metadata[0]["fields"][0]["value"] = title
                metadata[0]["fields"][1]["value"] = [subject]
                metadata[0]["fields"][2]["value"] = description
                metadata[0]["fields"][4]["value"] = rightsHolder
                metadata[0]["fields"][5]["value"] = loicense
                if isPartOf != 'Null' and subject != 'Null' and (len(isPartOf.strip())>0) is not False and (len(subject.strip())>0) is not False:
                    metadata[0]["fields"][6]["value"] = series_poster(
                        series_name=isPartOf, subject=subject
                    )
                metadata[0]["fields"][7]["value"] = creator
                metadata[0]["fields"][8]["value"] = contributor
                metadata[0]["fields"][9]["value"] = self.time_transformer(start_time)
                metadata[0]["fields"][12]["value"] = source

                metadata = json.dumps(metadata, ensure_ascii=False)

            with open("OpencastAPI/the_jsoniest.json", "r") as openfile:
                scheduling = json.load(openfile)
                scheduling = scheduling[0]["scheduling"][0]
                scheduling["start"] = self.time_transformer(start_time)
                scheduling["end"] = self.time_transformer(end_time)
                scheduling["agent_id"] = location
                scheduling = json.dumps(scheduling, ensure_ascii=False)

            with open("OpencastAPI/the_jsoniest.json", "r") as openfile:
                processing = json.load(openfile)
                processing = processing[0]["processing"][0]
                processing["workflow"] = os.getenv("OPENCAST_WORKFLOW_ID")
                processing = json.dumps(processing, ensure_ascii=False)

            body = {
                "metadata": (None, metadata),
                "acl": (None, acl),
                "processing": (None, processing),
                "scheduling": (None, scheduling),
            }

            headers = {
                "content-disposition": "form-data",
                "cache-control": "no-cache",
                "Connection": "close",
            }

            response = requests.post(
                f"{self.api_url}/events",
                files=body,
                headers=headers,
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            if response.status_code == 409:
                logging.info("ЗАМЕЧЕНО ПЕРЕСЕЧЕНИЕ ЭВЕНТОВ")

                if (
                    len(
                        list(
                            filter(lambda x: x["title"] == title, response_check.json())
                        )
                    )
                    == 0
                ):
                    logging.info("Данное время уже занято! Переходим к следующему")

                elif (
                    len(
                        list(
                            filter(lambda x: x["title"] == title, response_check.json())
                        )
                    )
                    > 0
                    and list(
                        filter(lambda x: x["title"] == title, response_check.json())
                    )[0]["title"]
                    == title
                ):
                    logging.info(f"Событие {title} есть в Opencast, но его НЕТ в описании эвента Google Calendar! Запускаем его экспорт в Google Calendar"
                    )
                    body = {"onlyWithWriteAccess": True}

                    headers = {
                        "content-disposition": "form-data",
                        "cache-control": "no-cache",
                        "Connection": "close",
                    }
                    response = requests.get(
                        f"{self.api_url}/events/",
                        auth=(
                            os.getenv("OPENCAST_API_USER"),
                            os.getenv("OPENCAST_API_PASSWORD"),
                        ),
                    )
                    return list(filter(lambda x: x["title"] == title, response.json()))[
                        0
                    ]["identifier"]

                elif (
                    len(
                        list(
                            filter(lambda x: x["title"] == title, response_check.json())
                        )
                    )
                    > 0
                    and len(
                        list(
                            filter(
                                lambda x: x["start"]
                                == self.time_transformer(start_time),
                                response_check.json(),
                            )
                        )
                    )
                    == 0
                ):
                    logging.info("ДУБЛИКАТ:", list(filter(lambda x: x["title"] == title, response_check.json()))[0]["title"])
                    deleting_event_id = list(
                        filter(lambda x: x["title"] == title, response_check.json())
                    )[0]["identifier"]
                    response = requests.delete(
                        f"{self.api_url}/events/{deleting_event_id}",
                        auth=(
                            os.getenv("OPENCAST_API_USER"),
                            os.getenv("OPENCAST_API_PASSWORD"),
                        ),
                    )
                    response.status_code
                    logging.info(f"Дубликат удалён: {response.status_code}, приступаем к постингу актуального эвента",
                    )
                    response = requests.post(
                        f"{self.api_url}/events",
                        files=body,
                        headers=headers,
                        auth=(
                            os.getenv("OPENCAST_API_USER"),
                            os.getenv("OPENCAST_API_PASSWORD"),
                        ),
                    )
                    logging.info("Событие добавлено в Opencast.")
                    if not type(response.json()) == "str":
                        logging.info("post_event вернул ID:", response.json()["identifier"])
                        self.post_description_updater(
                            response.json()["identifier"], google_event_id
                        )
                        return response.json()["identifier"]
                    else:
                        return logging.error("Что-то пошло не так при постинге эвента в Opencast")
            else:
                logging.info("Событие добавлено в Opencast")
                if not type(response.json()) == "str":
                    logging_id = response.json()["identifier"]
                    logging.info(f"post_event вернул ID: {logging_id }")
                    self.post_description_updater(
                        response.json()["identifier"], google_event_id
                    )
                    return response.json()["identifier"]
                else:
                    return "Что-то пошло не так при постинге эвента в Opencast"
        except Exception as error:
            error_msg = f"Error: {error}\n{traceback.format_exc()}"
            logging.error(error_msg)
            pass

    def post_description_updater(self, opencast_event_id=None, google_event_id=None):
        """Добавляет к существующему описанию event'a id события из
        Google Calendar, которое уже было экспортировано в Opencast
        """
        logging.info(f"post_description_update() получил ID опенкаста из post_event(): {opencast_event_id}")

        api_url = os.getenv("OPENCAST_API_URL")

        metadata = requests.get(
            f"{self.api_url}/events/{opencast_event_id}/metadata",
            auth=(os.getenv("OPENCAST_API_USER"), os.getenv("OPENCAST_API_PASSWORD")),
        )

        metadata = metadata.json()

        metadata[0]["fields"][2]["value"] = (
            metadata[0]["fields"][2]["value"]
            + "\n"
            + f"\nДанное событие импортировано из Google Календаря. \nID: {google_event_id}"
        )
        if metadata[0]["fields"][15]["value"] != "Google Events Exporter":
            metadata[0]["fields"][15]["value"] = "Google Events Exporter"

        metadata = json.dumps(metadata)

        body = {"metadata": (None, metadata)}
        headers = {
            "content-disposition": "form-data",
            "cache-control": "no-cache",
            "Connection": "close",
        }

        requests.post(
            f"{api_url}/events/{opencast_event_id}",
            files=body,
            headers=headers,
            auth=(os.getenv("OPENCAST_API_USER"), os.getenv("OPENCAST_API_PASSWORD")),
        )
        logging.info(f"post_description_updater() успешно поменял описание эвента в Opencast на id эвента гугла: {google_event_id}")

    def post_checker(self, opencast_event_id=None):
        """Проверяет существование эвеента по его ID"""
        if (
            requests.get(
                f"{self.api_url}/events/{opencast_event_id}",
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            ).status_code
            == 200
        ):
            return True
        else:
            return False
