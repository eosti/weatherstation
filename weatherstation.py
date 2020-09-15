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
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=config.LOG_FILENAME,
    filemode='w',
)

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

logger.info('Connected as %s' % config.io_api_username)

logger.info(datetime.now())

# Create UART object for air quality
import serial
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

# Buffer for UART
buffer = []

# Create I2C object
i2c = busio.I2C(board.SCL, board.SDA)
# Create temp/humidity object through I2C
sensor = adafruit_si7021.SI7021(i2c)

logger.info('Reading sensors every %d seconds.' % LOOP_DELAY)
try:
    while True:
        logger.debug('Reading sensors...')

        # Read air quality
        try:
            logger.debug(uart.in_waiting)
            uart.flushInput()       # Required to get the most current data
            time.sleep(3)
            data = uart.read(32)  # read up to 32 bytes
        except Exception as e:
            logger.warning('UART connection error. Skipping.')
            # possible that sometimes the flushing happens inbetween packets thus messing with the recieves
            logger.exception("Exception occurred")


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
            logger.warning('Incorrect UART packet length. Skipping.')
            continue
        try:
            frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(buffer[4:]))

            pm10_standard, pm25_standard, pm100_standard, pm10_env, \
                pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, \
                particles_25um, particles_50um, particles_100um, skip, checksum = frame

            check = sum(buffer[0:30])

            if check != checksum:
                buffer = []
                logger.warning('UART checksum error. Skipping.')
                continue

        except Exception as e:
            logger.warning('Error in UART parsing.')
            logger.exception("Exception occurred")

        try:
            # Convert PM values to AQI
            current_aqi = aqi.to_aqi([
                (aqi.POLLUTANT_PM25, pm25_env),
                (aqi.POLLUTANT_PM10, pm100_env),
            ])
        except Exception as e:
            logger.warning('PM conversion failed. Skipping.')
            logger.exception("Exception occurred")

        try:
            # Read Si7021 
            temp_data = sensor.temperature
            humidity_data = sensor.relative_humidity
        except Exception as e:
            logger.warning('Si7021 read error. Skipping.')
            logger.exception("Exception occurred")


        try:
            # Data collected, let's send it in!
            logger.debug('Sending data to Adafruit I/O...')
            logger.debug("---------------------------------------")

            logger.debug('Temperature: %0.1f C' % temp_data)
            aio.send(outside_temp_feed.key, temp_data)
            logger.debug('Humidity: %0.1f %%' % humidity_data)
            aio.send(outside_humidity_feed.key, humidity_data)

            logger.debug('PM 1.0: %0i' % pm10_env)
            aio.send(pm_1_feed.key, pm10_env)
            logger.debug('PM 2.5: %0i' % pm25_env)
            aio.send(pm_2_feed.key, pm25_env)
            logger.debug('PM 10: %0i' % pm100_env)
            aio.send(pm_10_feed.key, pm100_env)
            logger.debug('AQI: %0i' % float(current_aqi))
            aio.send(aqi_feed.key, float(current_aqi))
        except Exception as e:
            logger.error('Unable to upload data. Skipping.')
            logger.exception("Exception occurred")
            logger.info('Resetting Adafruit I/O Connection')
            aio = Client(config.io_api_username, config.io_api_key)

        # Reset buffer
        buffer = buffer[32:]

        # avoid timeout from adafruit io
        time.sleep(LOOP_DELAY)

except Exception as e:
    logger.critical('Something very bad just happened.')
    logger.exception('Exception occurred')
