#!/usr/bin/env python3
import time, board, adafruit_dht, pandas as pd, datetime, os, telebot, dotenv, requests, traceback, logging, io
import matplotlib, matplotlib.pyplot as plt
import threading
from datetime import timedelta
from pathlib import Path

os.chdir(Path(__file__).parent)

logfile = 'temp_sensor.log'

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(logfile),
        logging.StreamHandler()
    ]
)

dotenv.load_dotenv()
CHAT_ID = int(os.environ['CHAT_ID'])
CHAT_ID_ERROR = int(os.environ['CHAT_ID_ERROR'])

now = datetime.datetime.now

dhtDevice = adafruit_dht.DHT11(board.D4, use_pulseio=False)

datafile = Path('temp_sensor.csv')
if datafile.exists():
    data = pd.read_csv(datafile, index_col=0, parse_dates=True).squeeze()
else:
    data = pd.Series([], name='value')

def sensing():
    global data
    ctime = now()
    last_filter = ctime
    last_notification = datetime.datetime.min
    while True:
        try:
            ctime = now()
            if ctime - last_filter > timedelta(hours=1):
                last_filter = ctime
                indices = list(filter(lambda dt: dt + timedelta(weeks=5) > ctime, data.index))
                data = data[indices]
            data.to_csv(datafile, index_label='datetime')
            success = False
            while not success:
                try:
                    temperature_c = dhtDevice.temperature
                    if type(temperature_c) == int:
                        success = True
                    else:
                        time.sleep(1)
                except RuntimeError as error:
                    print(error.args[0])
                    time.sleep(1)
            print(f'Temperatur: {temperature_c}°C')
            new = pd.Series([temperature_c], index=[ctime], name=data.name)
            data = pd.concat([data, new])
            if temperature_c != None and temperature_c <= 50 and ctime - last_notification > timedelta(hours=1):
                bot.send_message(CHAT_ID, f'Die Temperatur wurde unterschritten und beträgt {temperature_c}°C.')
                last_notification = ctime
        except Exception as error:
            log_critical(traceback.format_exc())
            dhtDevice.exit()
            raise error
        time.sleep(60)

bot = telebot.TeleBot(os.environ['API_KEY'])

help_msg = '''\
*A*: Gibt die aktuelle Temperatur aus.
*D*: Sendet ein Diagramm des Temperaturverlaufs. Beispiele: _D3_ sendet die letzten 3 Stunden, _D24_ die letzten 24 Stunden. Im Prinzip ist jede beliebige natürliche Zahl möglich. \
'''

@bot.message_handler()
def info(message):
    global data
    if time.time() - message.date < 5 and message.chat.id in {CHAT_ID, CHAT_ID_ERROR}:   # only messages which are newer than 5 seconds
        if message.text == 'A':
            msg = f'aktuelle Temperatur: {data[-1]}°C'
            bot.send_message(message.chat.id, msg)
        elif message.text.startswith('D') and message.text.strip()[1:].isdecimal():
            hours = int(message.text.strip()[1:])
            if hours == 0:
                return
            indices = list(filter(lambda dt: dt + timedelta(hours=hours) > now(), data.index))
            data_filtered = data[indices]
            fig = plt.figure(dpi=200)
            plt.plot(data_filtered)
            if hours <= 24:
                myFmt = matplotlib.dates.DateFormatter('%H:%M')
            else:
                myFmt = matplotlib.dates.DateFormatter('%-d.%-m %H:%M')
                fig.autofmt_xdate()
            plt.gca().xaxis.set_major_formatter(myFmt)
            plt.xlabel('Uhrzeit')
            plt.ylabel('Grad Celsius')
            plt.ylim([20, 80])
            plt.grid()
            buf = io.BytesIO()
            plt.savefig(buf)
            buf.seek(0)
            bot.send_photo(message.chat.id, buf)
        elif message.text.lower() == 'log':
            with open(logfile, 'rb') as file:
                bot.send_document(message.chat.id, file)
        elif message.text == 'Hilfe':
            bot.send_message(message.chat.id, help_msg, parse_mode='Markdown')
        else:
            msg = 'Ich verstehe dich nicht!\n' + help_msg
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')

def polling():
    last_log = now()
    while True:
        try:
            bot.polling()
        except requests.exceptions.RequestException:
            if now() - last_log > timedelta(minutes=5):
                last_log = now()
                logging.error('No Internet connection!')
            time.sleep(3)
        except Exception:
            log_critical(traceback.format_exc())

def log_critical(exc):
    logging.critical(exc)
    if now() - log_critical.last > timedelta(hours=6):
        log_critical.last = now()
        bot.send_message(CHAT_ID_ERROR, exc.strip().splitlines()[-1])
        with open(logfile, 'rb') as file:
            bot.send_document(CHAT_ID_ERROR, file)

log_critical.last = datetime.datetime.min

t1 = threading.Thread(target=sensing)
t2 = threading.Thread(target=polling)
t1.start()
t2.start()