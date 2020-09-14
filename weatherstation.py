try:
    import struct
except Exception as e:
    import ustruct as struct

import time
import logging
import logging.handlers
import board
import busio
import adafruit_si7021
from datetime import datetime
import aqi

import config
from Adafruit_IO import Client, Feed, RequestError

# refresh time, in seconds.
LOOP_DELAY = 120

# Logging stuff
my_logger = logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=config.LOG_FILENAME,
    filemode='w',
)

handler = logging.handlers.RotatingFileHandler(
              config.LOG_FILENAME, maxBytes=10*1024*1024, backupCount=5)
my_logger.addHandler(handler)


# Create an instance of the REST client
logging.info('Setting up Adafruit I/O and sensors...')
aio = Client(config.io_api_username, config.io_api_key)

# Assign feeds
outside_temp_feed = aio.feeds('outside-temp')
outside_humidity_feed = aio.feeds('outside-humidity')
pm_1_feed = aio.feeds('pm-1-dot-0')
pm_2_feed = aio.feeds('pm-2-dot-5')
pm_10_feed = aio.feeds('pm-10')
aqi_feed = aio.feeds('aqi')

logging.info('Connected as %s' % config.io_api_username)

logging.info(datetime.now())

# Create UART object for air quality
import serial
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

# Buffer for UART
buffer = []

# Create I2C object
i2c = busio.I2C(board.SCL, board.SDA)
# Create temp/humidity object through I2C
sensor = adafruit_si7021.SI7021(i2c)

logging.info('Reading sensors every %d seconds.' % LOOP_DELAY)
try:
    while True:
        logging.debug('Reading sensors...')

        # Read air quality
        try:
            logging.debug(uart.in_waiting)
            uart.flushInput()       # Required to get the most current data
            time.sleep(3)
            data = uart.read(32)  # read up to 32 bytes
        except Exception as e:
            logging.warning('UART connection error. Skipping.')
            # possible that sometimes the flushing happens inbetween packets thus messing with the recieves
            logging.exception("Exception occurred")


        data = list(data)
        buffer += data

        while buffer and buffer[0] != 0x42:
            buffer.pop(0)

        if len(buffer) > 200:
            buffer = []  # avoid an overrun if all bad data
        if len(buffer) < 32:
            continue

        if buffer[1] != 0x4d:
            buffer.pop(0)
            continue

        frame_len = struct.unpack(">H", bytes(buffer[2:4]))[0]
        if frame_len != 28:
            buffer = []
            logging.warning('Incorrect UART packet length. Skipping.')
            continue
        try:
            frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(buffer[4:]))

            pm10_standard, pm25_standard, pm100_standard, pm10_env, \
                pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, \
                particles_25um, particles_50um, particles_100um, skip, checksum = frame

            check = sum(buffer[0:30])

            if check != checksum:
                buffer = []
                logging.warning('UART checksum error. Skipping.')
                continue

        except Exception as e:
            logging.warning('Error in UART parsing.')
            logging.exception("Exception occurred")

        try:
            # Convert PM values to AQI
            current_aqi = aqi.to_aqi([
                (aqi.POLLUTANT_PM25, pm25_env),
                (aqi.POLLUTANT_PM10, pm100_env),
            ])
        except Exception as e:
            logging.warning('PM conversion failed. Skipping.')
            logging.exception("Exception occurred")

        try:
            # Read Si7021 
            temp_data = sensor.temperature
            humidity_data = sensor.relative_humidity
        except Exception as e:
            logging.warning('Si7021 read error. Skipping.')
            logging.exception("Exception occurred")


        try:
            # Data collected, let's send it in!
            logging.debug('Sending data to Adafruit I/O...')
            logging.debug("---------------------------------------")

            logging.debug('Temperature: %0.1f C' % temp_data)
            aio.send(outside_temp_feed.key, temp_data)
            logging.debug('Humidity: %0.1f %%' % humidity_data)
            aio.send(outside_humidity_feed.key, humidity_data)

            logging.debug('PM 1.0: ', pm10_env)
            aio.send(pm_1_feed.key, pm10_env)
            logging.debug('PM 2.5: ', pm25_env)
            aio.send(pm_2_feed.key, pm25_env)
            logging.debug('PM 10: ', pm100_env)
            aio.send(pm_10_feed.key, pm100_env)
            logging.debug('AQI: ', float(current_aqi))
            aio.send(aqi_feed.key, float(current_aqi))
        except Exception as e:
            logging.error('Unable to upload data. Skipping.')
            logging.exception("Exception occurred")
            logging.info('Resetting Adafruit I/O Connection')
            aio = Client(config.io_api_username, config.io_api_key)

        # Reset buffer
        buffer = buffer[32:]

        # avoid timeout from adafruit io
        time.sleep(LOOP_DELAY)

except Exception as e:
    logging.critical('Something very bad just happened.')
    logging.exception('Exception occurred')
