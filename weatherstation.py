# TODO: Make this operate as a oneshot through cron
try:
    import struct
except Exception as e:
    import ustruct as struct

import logging
import logging.handlers as handlers
import board
import busio
import serial
import adafruit_si7021
from adafruit_pm25.uart import PM25_UART
import aqi
import config
from Adafruit_IO import Client, Feed, RequestError

# Logging Config
logger = logging.getLogger('weatherstation')
logger.setLevel(logging.INFO)

# Format, max size 5MB, 4 backups
formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s - %(funcName)s: %(message)s')
logHandler = handlers.RotatingFileHandler(config.LOG_FILENAME, maxBytes=5*1024*1024, backupCount=4)
logHandler.setLevel(logging.INFO)
logger.addHandler(logHandler)

logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Make it obvious we started
logger.info('\n')

# Create an instance of the REST client
logger.info('Setting up Adafruit I/O and sensors...')
aio = Client(config.io_api_username, config.io_api_key)

# Assign feeds
outside_temp_feed = aio.feeds('outside-temp')
outside_humidity_feed = aio.feeds('outside-humidity')
pm_1_feed = aio.feeds('pm-1-dot-0')
pm_2_feed = aio.feeds('pm-2-dot-5')
pm_10_feed = aio.feeds('pm-10')
aqi_feed = aio.feeds('aqi')

logger.debug('Connected as %s' % config.io_api_username)

# Create UART PM2.5 device
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
reset_pin = None
pm25 = PM25_UART(uart, reset_pin)

# Create I2C SI7021 device
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_si7021.SI7021(i2c)

time.sleep(1)

logger.info('Reading sensors...')

# Read air quality
try:
    aqdata = pm25.read()
except Exception as e:
    logger.warning('Unable to read air quality data. Skipping.')
    logger.exception("Exception occurred")

# Convert PM values to AQI
try:
    current_aqi = aqi.to_aqi([
        (aqi.POLLUTANT_PM25, aqdata["pm25 env"]),
        (aqi.POLLUTANT_PM10, aqdata["pm100 env"]),
    ])
except Exception as e:
    logger.warning('PM conversion failed. Skipping.')
    logger.exception("Exception occurred")

# Read Si7021 
try:
    temp_data = sensor.temperature
    humidity_data = sensor.relative_humidity
except Exception as e:
    logger.warning('Si7021 read error. Reloading library. Skipping.')
    logger.exception("Exception occurred")

# Data collected, let's send it in!
try:
    logger.info('Sending data to Adafruit I/O...')
    logger.debug("---------------------------------------")

    logger.debug('Temperature: %0.1f C' % temp_data)
    aio.send(outside_temp_feed.key, temp_data)
    logger.debug('Humidity: %0.1f %%' % humidity_data)
    aio.send(outside_humidity_feed.key, humidity_data)

    logger.debug('PM 1.0: %0i' % aqdata["pm10 env"])
    aio.send(pm_1_feed.key, aqdata["pm10 env"])
    logger.debug('PM 2.5: %0i' % aqdata["pm25 env"])
    aio.send(pm_2_feed.key, aqdata["pm25 env"])
    logger.debug('PM 10: %0i' % aqdata["pm100 env"])
    aio.send(pm_10_feed.key, aqdata["pm100 env"])
    logger.debug('AQI: %0i' % float(current_aqi))
    aio.send(aqi_feed.key, float(current_aqi))
except Exception as e:
    logger.error('Unable to upload data. Skipping.')
    logger.exception("Exception occurred")
