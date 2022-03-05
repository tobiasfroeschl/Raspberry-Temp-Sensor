#!/usr/bin/env python3
import time, board, adafruit_dht, pandas as pd, datetime, os, telebot, dotenv, requests
import matplotlib, matplotlib.pyplot as plt
import threading
from datetime import timedelta
from pathlib import Path

dotenv.load_dotenv()

now = datetime.datetime.now

dhtDevice = adafruit_dht.DHT11(board.D4, use_pulseio=False)

os.chdir(Path(__file__).parent)

datafile = Path('temp_sensor.csv')
if datafile.exists():
    data = pd.read_csv(datafile, index_col=0, parse_dates=True).squeeze()
else:
    data = pd.Series([], name='value')

def sensing():
    global data
    ctime = now()
    last_write = ctime
    last_filter = ctime
    last_notification = datetime.datetime.min
    while True:
        ctime = now()
        if ctime - last_write > timedelta(minutes=1):
            last_write = ctime
            if ctime - last_filter > timedelta(hours=1):
                last_filter = ctime
                indices = list(filter(lambda dt: dt + timedelta(days=7) > ctime, data.index))
                data = data[indices]
            data.to_csv(datafile, index_label='datetime')
        try:
            temperature_c = dhtDevice.temperature
            print(f'Temperatur: {temperature_c}°C')
            new = pd.Series([temperature_c], index=[ctime], name=data.name)
            data = pd.concat([data, new])
            if temperature_c >= 30 and ctime - last_notification > timedelta(hours=1):
                bot.send_message(os.environ['chat_id'], f'Die Temperatur wurde überschritten und beträgt {temperature_c}°C.')
                last_notification = ctime
        except RuntimeError as error:
            print(error.args[0])
        except Exception as error:
            dhtDevice.exit()
            raise error
        time.sleep(5)

bot = telebot.TeleBot(os.environ['API_KEY'])

help_msg = '''\
Aktuell: Gibt die aktuelle Temperatur aus.
Diagramm: Sendet ein Diagramm des Temperaturverlaufs der letzten 3 Stunden.\
'''

plotfile = 'plot.png'

@bot.message_handler()
def info(message):
    global data
    if time.time() - message.date < 5:   # only messages which are newer than 5 seconds
        if message.text == 'Aktuell':
            msg = f'aktuelle Temperatur: {data[-1]}°C'
            bot.send_message(message.chat.id, msg)
        elif message.text == 'Diagramm':
            indices = list(filter(lambda dt: dt + timedelta(hours=3) > now(), data.index))
            data_filtered = data[indices]
            plt.figure()
            plt.plot(data_filtered)
            myFmt = matplotlib.dates.DateFormatter('%H:%M')
            plt.gca().xaxis.set_major_formatter(myFmt)
            plt.xlabel('Uhrzeit')
            plt.ylabel('Grad Celsius')
            plt.ylim([10, 70])
            plt.savefig(plotfile)
            with open(plotfile, 'rb') as photo:
                bot.send_photo(message.chat.id, photo)
        elif message.text == 'Hilfe':
            bot.send_message(message.chat.id, help_msg)
        else:
            msg = 'Ich verstehe dich nicht!\n' + help_msg
            bot.send_message(message.chat.id, msg)

def polling():
    success = False
    while not success:
        try:
            bot.polling()
            success = True
        except requests.exceptions.RequestException:
            print('No Internet connection -> no polling')
            time.sleep(3)

t1 = threading.Thread(target=sensing)
t2 = threading.Thread(target=polling)
t1.start()
t2.start()