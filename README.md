# Raspberry Pi Zero W Weatherstation

A Pi Zero W-based weatherstation, capable of monitoring PM1.0, PM2.5, PM10, temperature, and humidity. Uploaded to Adafruit I/O for ease of access! Data usage fits easily within the free tier. I'm also using the same Raspberry Pi to capture ADS-B flight tracking info and send it to various sources. 

## Components
* [Raspberry Pi Zero W](https://www.adafruit.com/product/3400)
* [PM2.5 Air Quality Sensor](https://www.adafruit.com/product/3686)
* [Si7021 Temperature & Humidity Sensor](https://www.adafruit.com/product/3251)
* [3D Printed Stevenson Screen](https://www.thingiverse.com/thing:2970799)

## Prerequisites

This project uses the Adafruit libraries [adafruit-blinka](https://github.com/adafruit/Adafruit_Blinka), [adafruit-circuitpython-si7021](https://github.com/adafruit/Adafruit_CircuitPython_SI7021), and [adafruit-io](https://github.com/adafruit/Adafruit_IO_Python). 

`pip3 install adafruit-blinka adafruit-circuitpython-si7021 adafruit-io` 

Use `sudo raspi-config` to enable I2C, disable the serial login shell, and enable the serial port hardware. 

Wire both sensors to the RPi using the standard I2C and UART pins. Be wary of voltage levels: the Si7021 runs on 3.3V whereas the PM2.5 sensor runs on 5V. 

## Usage
1. Clone repo onto the pi.
2. Create `config.py` inside the weatherstation directory that sets io_api_username and io_api_key to your Adafruit I/O username and API key respectively.
```
# config.py
io_api_username = YOUR_USERNAME
io_api_key = YOUR_APIKEY
```
3. Tell the pi to run `weatherstation.py` at boot. I used `crontab` to do this, but there are other options.  
4. Reboot!
