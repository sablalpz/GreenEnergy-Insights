
import sys
import os
# Añadir la raíz del proyecto al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from apscheduler.schedulers.blocking import BlockingScheduler
from ejecutar_motor import ejecutar_motor
import logging

# Configura logging para ver los logs del scheduler
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

scheduler = BlockingScheduler()

# Programa la tarea para que se ejecute cada 24 horas
scheduler.add_job(ejecutar_motor, 'interval', hours=24, id='prediccion_diaria')

logging.info('Scheduler iniciado. La predicción se ejecutará cada 24 horas.')

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    logging.info('Scheduler detenido.')
