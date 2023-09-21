from __future__ import print_function

import datetime
import json
import os
import traceback
import time
import logging

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from OpencastAPI.opencast_api import OpencastAPI

logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

class GoogleCalendarAPI:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/calendar"]
        self.service = build("calendar", "v3", credentials=self.auth())
        self.events_ids = []
        self.get_calendars(auth=self.auth())
        self.orphan_finder()

    def orphan_finder(self):
        events_ids_dict = OpencastAPI().events_cleaner()
        for google_event_id in events_ids_dict.keys():
            if google_event_id not in self.events_ids:
                OpencastAPI().delete_event(
                    deleting_event_id=events_ids_dict[google_event_id]
                )
        logging.info("Скрипт завершил итерацию")

    def auth(self):
        """Функция аутентификации: функция возвращает creds,
        которые задействуются при совершении любого действия с Google API
        """
        creds = None
        if os.path.exists("GoogleAPI/token.json"):
            creds = Credentials.from_authorized_user_file(
                "GoogleAPI/token.json", self.scopes
            )
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "GoogleAPI/credentials.json", self.scopes
                )
                creds = flow.run_local_server(port=0)
            with open("GoogleAPI/token.json", "w") as token:
                token.write(creds.to_json())
        return creds

    def get_calendars(self, auth=None):
        with open("OpencastAPI/the_jsoniest.json", "r") as openfile:
            location = json.load(openfile)
            location = location[0]["mapping"][0]
            calendars = list(location)
            service = build("calendar", "v3", credentials=self.auth())
            GET_batch = service.new_batch_http_request()
            now = datetime.datetime.utcnow().isoformat() + "Z"
            for calendar_id in calendars:
                GET_batch.add(
                    service.events().list(
                        calendarId=calendar_id,
                        timeMin=now,
                        maxResults=20,
                        singleEvents=True,
                        orderBy="startTime",
                    ),
                    callback=self.get_events,
                )
            GET_batch.execute()
            return len(calendars)

    def get_events(self, request_id, response, exception):
        if exception is None:
            events_result = response
            events = events_result.get("items", [])
            self.events_exporter(auth=self.auth(), events=events)
        else:
            logging.error(exception)

    def description_formatter(self, raw_description=None):
        words = []
        try:
            raw_description = raw_description.split(";")

            for word in raw_description:
                words.append(word)

            description, isPartOf, creator, subject, contributor, source = words[:6]
            if ", " in contributor:
                contributor = contributor.split(", ")
            else:
                contributor = [contributor]
            if ", " in creator:
                creator = creator.split(", ")
            else:
                creator = [creator]
            return description, isPartOf, creator, subject, contributor, source

        except Exception as error:
            logging.warning("Метаданные оформлены неправильно, возвращаем умолчательные данные")
            return " ", ' ', [], ' ', [], " "

    def events_exporter(
        self,
        auth=None,
        events=None,
    ):
        """Вытаскивает из гугл календаря грядущие event'ы,
        передаёт их метаданные (title, description, id, start_time,
        end_time, дату создания) в функцию создания поста в Opencast,
        получает ответ в виде id event'а в Opencast и передаёт его в
        функцию, которая изменяет описания изначального event'а в
        Google Calendar
        """
        description, subject, isPartOf, creator, contributor, source = (
            None,
            None,
            None,
            None,
            None,
            None,
        )
        try:
            service = build("calendar", "v3", credentials=self.auth())
            POST_batch = service.new_batch_http_request()
            if not events:
                logging.info("Нет грядущих эвентов!")
                return

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                calendar_id = event["organizer"]["email"]
                self.events_ids.append(event["id"])
                summary = event["summary"]
                logging.info(f"Получаем метаданные эвента {summary}")
                raw_description = BeautifulSoup(
                    event.get("description", "-"), "lxml"
                ).text
                (
                    description,
                    isPartOf,
                    creator,
                    subject,
                    contributor,
                    source,
                ) = self.description_formatter(raw_description)
                if (
                    ("успешно" and "экспортировано" and "OpenCast.")
                    in event.get("description", "-").split()
                ) and (
                    OpencastAPI().post_checker(
                        event.get("description", "-").split()[-1]
                    )
                    is True
                ):
                    summary = event["summary"]
                    logging.info(f"Событие {summary} уже экспортировано в Opencast и отображается это указано в Google Calendar!")
                    pass
                elif (
                    ("успешно" and "экспортировано" and "OpenCast.")
                    in event.get("description", "-").split()
                ) and (
                    OpencastAPI().post_checker(
                        event.get("description", "-").split()[-1]
                    )
                    is False
                ):
                    summary = event["summary"]
                    logging.info(f"События {summary} в Opencast НЕТ, но в описании эвента Google Calendar он фигурирует! Запускаем его экспорт в Opencast")
                    logging.info(f"Постим событие {summary} со следующими метаданными:\nОписание: {description}\nСерия: {isPartOf}\nПрезентер: {creator}\nSubject: {subject}\nКонтрибьютор: {contributor}\nИсточник: {source}")
                    outcome = self.google_event_changer(
                        calendar_id=calendar_id,
                        auth=self.auth(),
                        opencast_event_id=OpencastAPI().post_event(
                            calendar_id=calendar_id,
                            title=event["summary"],
                            description=description,
                            subject=subject,
                            isPartOf=isPartOf,
                            creator=creator,
                            contributor=contributor,
                            source=source,
                            google_event_id=event["id"],
                            start_time=start,
                            end_time=end,
                            created=event["created"],
                        ),
                        google_event_id=event["id"],
                    )
                    POST_batch.add(
                        service.events().update(
                            calendarId=calendar_id, eventId=event["id"], body=outcome
                        )
                    )
                    time.sleep(5)
                else:
                    summary = event["summary"]
                    logging.info(f"Данные из events_exporter() ушли в post_event(): {summary}")
                    logging.info(f"Постим событие {summary} со следующими метаданными:\nОписание: {description}\nСерия: {isPartOf}\nПрезентер: {creator}\nSubject: {subject}\nКонтрибьютор: {contributor}\nИсточник:{source}")
                    outcome = self.google_event_changer(
                        calendar_id=calendar_id,
                        auth=self.auth(),
                        opencast_event_id=OpencastAPI().post_event(
                            calendar_id=calendar_id,
                            title=event["summary"],
                            description=description,
                            subject=subject,
                            isPartOf=isPartOf,
                            creator=creator,
                            contributor=contributor,
                            source=source,
                            google_event_id=event["id"],
                            start_time=start,
                            end_time=end,
                            created=event["created"],
                        ),
                        google_event_id=event["id"],
                    )
                    POST_batch.add(
                        service.events().update(
                            calendarId=calendar_id, eventId=event["id"], body=outcome
                        )
                    )
                    time.sleep(5)
            POST_batch.execute()
            logging.info("Batch запрос успешно выполнен. Календарь обработан")
        except HttpError as error:
            error_msg = f"Error: {error}\n{traceback.format_exc()}"
            logging.error(error_msg)

    def google_event_changer(
        self, calendar_id=None, auth=None, opencast_event_id=None, google_event_id=None
    ):
        """Принимает id event'а из Opencast и вставляет его в описания
        event'а в Google Calendar, чьи метаданные были задействованы при
        создании event'а в Opencast
        """
        if opencast_event_id is None:
            return None
        logging.info(f"google_event_changer() успешно получил ID евента из Opencast: {opencast_event_id}")
        try:
            service = build("calendar", "v3", credentials=auth)
            event = (
                service.events()
                .get(calendarId=calendar_id, eventId=google_event_id)
                .execute()
            )
            if (
                ("успешно" or "УСПЕШНО") and "экспортировано" and "OpenCast."
            ) in event.get("description", "-").split():
                event["description"] = (
                    event["description"][:-202]
                    + f"------------- \nДанное событие УСПЕШНО экспортировано в OpenCast. \nСсылка: https://video.miem.hse.ru/paella/ui/watch.html?id={opencast_event_id} \nID: {opencast_event_id}"
                )
            else:
                event["description"] = (
                    event.get("description", "-")
                    + f"------------- \nДанное событие успешно экспортировано в OpenCast. \nСсылка: https://video.miem.hse.ru/paella/ui/watch.html?id={opencast_event_id} \nID: {opencast_event_id}"
                )
            logging.info("google_event_changer() запросил смену описания евента в Google calendar")
            return event

        except HttpError as error:
            error_msg = f"Error: {error}\n{traceback.format_exc()}"
            logging.error(error_msg)