try:
    import struct
except ImportError:
    import ustruct as struct

import time
import board
import busio
import adafruit_si7021

import config
from Adafruit_IO import Client, Feed, RequestError

# refresh time, in seconds.
LOOP_DELAY = 120

# Create an instance of the REST client
print('Setting up Adafruit I/O and sensors...')
aio = Client(config.io_api_username, config.io_api_key)

# Assign feeds
outside_temp_feed = aio.feeds('outside-temp')
outside_humidity_feed = aio.feeds('outside-humidity')
pm_1_feed = aio.feeds('pm-1-dot-0')
pm_2_feed = aio.feeds('pm-2-dot-5')
pm_10_feed = aio.feeds('pm-10')

# Create UART object for air quality
import serial
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)

# Buffer for UART
buffer = []

# Create I2C object
i2c = busio.I2C(board.SCL, board.SDA)
# Create temp/humidity object through I2C
sensor = adafruit_si7021.SI7021(i2c)

print('Connected as ' config.io_api_username)
print('Reading sensors every %d seconds.' % LOOP_DELAY)

while True:
    # print('Reading sensors...')

    # Read air quality
    data = uart.read(32)  # read up to 32 bytes
    data = list(data)
    # print("read: ", data)          # this is a bytearray type

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
        continue

    frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(buffer[4:]))

    pm10_standard, pm25_standard, pm100_standard, pm10_env, \
        pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, \
        particles_25um, particles_50um, particles_100um, skip, checksum = frame

    check = sum(buffer[0:30])

    if check != checksum:
        buffer = []
        continue

    # Read Si7021 
    temp_data = sensor.temperature
    humidity_data = sensor.relative_humidity
    
    try:
        # Data collected, let's send it in!
        # print('Sending data to Adafruit I/O...')
        # print("---------------------------------------")

        # print('Temperature: %0.1f C' % temp_data)
        aio.send(outside_temp_feed.key, temp_data)
        # print('Humidity: %0.1f %%' % humidity_data)
        aio.send(outside_humidity_feed.key, humidity_data)

        # print('PM 1.0: ', pm10_standard)
        aio.send(pm_1_feed.key, pm10_standard)
        # print('PM 2.5: ', pm25_standard)
        aio.send(pm_2_feed.key, pm25_standard)
        # print('PM 10: ', pm100_standard)
        aio.send(pm_10_feed.key, pm100_standard)
    except:
        print('Unable to upload data. Skipping.')
    
    # print()

    # Reset buffer
    buffer = buffer[32:]

    # avoid timeout from adafruit io
    time.sleep(LOOP_DELAY)

