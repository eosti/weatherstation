# Raspberry Pi Zero W Weatherstation

A Pi Zero W-based weatherstation, capable of monitoring PM1.0, PM2.5, PM10, temperature, and humidity. Uploaded to Adafruit I/O for ease of access! Data usage fits easily within the free tier. I'm also using the same Raspberry Pi to capture ADS-B flight tracking info and send it to various sources. 

## Components
* [Raspberry Pi Zero W](https://www.adafruit.com/product/3400)
* [PM2.5 Air Quality Sensor](https://www.adafruit.com/product/3686)
* [Si7021 Temperature & Humidity Sensor](https://www.adafruit.com/product/3251)
* [3D Printed Stevenson Screen](https://www.thingiverse.com/thing:2970799)

## Prerequisites

This project uses the Adafruit libraries [adafruit-blinka](https://github.com/adafruit/Adafruit_Blinka), [adafruit-circuitpython-si7021](https://github.com/adafruit/Adafruit_CircuitPython_SI7021), [adafruit-circuitpython-pm25](https://github.com/adafruit/Adafruit_CircuitPython_PM25), and [adafruit-io](https://github.com/adafruit/Adafruit_IO_Python). 
It also uses the [python-aqi](https://github.com/hrbonz/python-aqi) library to convert from the native PM2.5 and PM10 values to a more universally known format. 

`pip3 install adafruit-blinka adafruit-circuitpython-si7021 adafruit-circuitpython-pm25 adafruit-io python-aqi` 

Use `sudo raspi-config` to enable I2C, disable the serial login shell, and enable the serial port hardware. 

Wire both sensors to the RPi using the standard I2C (for the Si7021) and UART (for the PM2.5 sensor) pins. Be wary of voltage levels: the Si7021 runs on 3.3V whereas the PM2.5 sensor runs on 5V. 

## Usage
1. Clone repo onto the pi.
2. Create `config.py` inside the weatherstation directory that sets io_api_username and io_api_key to your Adafruit I/O username and API key respectively. Additionally, add the location that you want the log files to go to.
```
# config.py
io_api_username = "YOUR_USERNAME"
io_api_key = "YOUR_APIKEY"
LOG_FILENAME = "/some/file/path/relative/to/execution/point"
```

3. Configure `cron` to execute this script every two minutes, or however often you'd like. Using `crontab -e`, add the line `*/2 * * * * python3 ~pi/weatherstation/weatherstation.py > ~pi/logs/crontab 2&>1`, substituting in your username, script location, and log location.

4. Reboot!
