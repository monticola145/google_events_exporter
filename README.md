# Google Events Exporter
## _Yandiev Ruslan_ & _Boyarsky Andrey_

Events Exporter - это приложение для автоматизированного экспорта 
эвентов из Google Calendar в Opencast

## Принцип работы

- Приложение проверяет 20 грядущих событий в Google Calendar
- Метаданные событий передаются в Opencast
- События постятся в Opencast, возвращая ID новоиспечённого события
- Описание события в Google Calendar обновляется с использованием вышеописанного ID
- В описаниях событий и в Google Calendar, и в Opencast появляется отметка об успешном экспорте



## Установка и использование (для сервера)

- Скопируйте репозиторий себе на устройство
```
git clone https://git.miem.hse.ru/19102/google_events_exporter.git
```

- Создайте и разверните виртуальное окружения; установите зависимости
```
python -m venv venv && source venv/Scripts/activate && pip install -r requirements.txt
```

- Для запуска программы вставте в терминал следующую команду:
```
python exporting_script.py
```
- Для корректного использования необходимо сознать нужное количество календарей и поместить их в качестве ключа их в json-файл с меткой "mapping", указав в качестве значения название Capture Agent
- Желательно не изменять json-файл, за исключением изменения календарей

## Использование пользователем
Для успешного использования приложения пользователем необходимо следовать следующему алгоритму:
- Пользователь должен создать событие в одном из обрабатываемых календарей
- В раздел "описание" пользователь должен вставить информацию используя режим списка по следующему примеру:
        1) Описание;
        2) Серия;
        3) Презентер, Презентер;
        4) Subject;
        5) Контрибьютор, Контрибьютор;
        6) Источник;
При желании можно не заполнять информацией тот или иной пункт, однако сам пункт должен присутствовать в списке и содержать ; (точка с запятой)

Пример правильного оформления:

        1) Пара по дисциплине "Введение в скриптостроение";
        2) Введение в скриптостроение;
        3) Елена Анатольевна Головач, Антон Павлович Фекалис;
        4) Скрипты, Программирование, Вводная лекция;
        5) Иван Иванович, Пётр Петрович;
        6) Запись с камеры №3826;

Пример правильного оформления с пропусками:

        1) Пара по дисциплине "Введение в скриптостроение";
        2) ;
        3) Елена Анатольевна Головач, Антон Павлович Фекалис;
        4) ;
        5) Иван Иванович, Пётр Петрович;
        6) ;


## .env файл
Для корректной работы необходимо заполнить .env файл следующей информацией:
```
OPENCAST_API_URL= *ссылка на Opencast**
OPENCAST_API_USER= **логин сервисного аккаунта**
OPENCAST_API_PASSWORD= **пароль сервисного аккаунта**
OPENCAST_API_ROLE= **роль сервисного аккаунта**
OPENCAST_WORKFLOW_ID=schedule-and-upload **вид постинга, лучше не менять**
#google
API_KEY= **api-ключ Вашего приложения**
CLIENT_ID= **ID Вашего приложения**
CLIEST_SECRET= **Passphrase Вашего приложения**
```
## Features

Особенности и "фишки" скрипта:

- Не беспокойтесь, если что-то пойдёт не так и эвенты пропадут из Opencast. Программа заметит это и справит при следующей итерации
- Эвент в Opencast появился, но скрипт не успел/не смог обновить описание эвента в Google Calendar? Ничего страшного! Мы предусмотрели это и добавили автопроверку на факт экспорта. Всё будет исправлена при следующей итерации
- Если эвент экспортирован по всем правилам:
```
Есть в Opencast и в описании указан ID эвента в Google Calendar
```
```
Отметка об успешном экспорте и ссылка в описании эвента в Google Calendar
```
- то он не будет дублироваться
