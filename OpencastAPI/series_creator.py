import codecs
import json
import os
import requests
import logging
from dotenv import load_dotenv


load_dotenv()

url = os.environ.get("OPENCAST_API_URL")


def series_poster(series_name=None, subject=None):
    response = requests.get(
        f"{url}/series/?limit=1000&offset=1210",
        auth=(os.getenv("OPENCAST_API_USER"), os.getenv("OPENCAST_API_PASSWORD")),
    )
    if len(list(filter(lambda x: x["title"] == series_name, response.json()))) > 0:
        logging.info('Серия уже существует')
        return list(filter(lambda x: x["title"] == series_name, response.json()))[0][
            "identifier"
        ]
    else:
        with open("OpencastAPI/the_jsoniest.json") as openfile:
            acl = json.load(openfile)
            acl = acl[0]["acl"]
            acl = json.dumps(acl, ensure_ascii=False)

        with codecs.open(
            "OpencastAPI/the_jsoniest.json", "r", encoding="utf-8"
        ) as openfile:
            metadata = json.load(openfile)
            metadata = metadata[0]["series_metadata"][0]
            metadata[0]["fields"][0]["value"] = series_name
            metadata[0]["fields"][1]["value"] = [subject]
            metadata = json.dumps(metadata, ensure_ascii=False)

            body = {
                "metadata": (None, metadata),
                "acl": (None, acl),
            }
            headers = {
                "content-disposition": "form-data",
                "cache-control": "no-cache",
                "Connection": "close",
            }
            response = requests.post(
                f"{url}/series",
                files=body,
                headers=headers,
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            print(response.status_code)
            identifier = response.json()["identifier"]
            response = requests.get(
                f"{url}/series/{identifier}",
                auth=(
                    os.getenv("OPENCAST_API_USER"),
                    os.getenv("OPENCAST_API_PASSWORD"),
                ),
            )
            logging.info('Создаём серию')
            return identifier
