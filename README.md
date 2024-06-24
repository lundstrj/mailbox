# Mailbox
_Johan Lundström - jl226ki_

A simple setup for knowing if someone (maybe even a mailman) has been fiddling with your mailbox today.

## Overview
### The problem
My current residence get intermittent mail delivery (supposedly every other day for mail, but packages can come any day). Some days you don't get anything even if it is a mail delivery day. The mail also gets deliverd at different times depending on reasons (I suppose), so what does one do? Well you go check your mailbox at least 5+ times per day just to be sure.

If only there was a better way.

### The solution
There is a better way!

Get a microcontroller and some sensors and hook them up to your mailbox. This way you can know if the mailman has been by today or not. You can even get fancy and hook it up to your home automation system to get notifications when mail has been delivered.

### Time to complete
If you have my code, all the hardware and a mailbox, you can probably get this done in an hour or two.

_(it took me significantly longer, but I was also prototyping and testing a lot of things along the way)_

__TODO: picture of mailbox__<br>
__TODO: video of operation__

## Objective
### Why?
I'd like to know if mail has been delivered today or not without having to check the mailbox multiple times per day.
### Purpose
To have a smart mailbox that can tell me if mail has been delivered today or not.
### Insights
To know if mail has been delivered today or not, you need to know if the mailbox has been opened today or not. This can be achieved by having a sensor that can detect if the mailbox has been opened or not. You can also have a sensor that can detect if the mailbox has been tilted or not. By combining these two sensors you can have a pretty good idea if mail has been delivered today or not.

## Bill of materials
Basically you need a microcontroller and a couple of buttons. I used a Raspberry Pi Pico W and some push buttons and a tilt sensor (mainly to be fancy). You can get away with only one push button if you'd like, but I will be using the following:
- [ ] 1x Raspberry Pi Pico W
- [ ] 3x push buttons with low force actuation
- [ ] 1x tilt sensor
- [ ] x assorted wires of varying lengths and colors (your call, you can make then all white if you want)
- [ ] tape is always good to have around

TODO: ADD PICTURES

<details>
<summary>Other useful things</summary>
- <kbd> Breadboard<br>
- <kbd> 3x LEDs<br>
- <kbd> approximately 500 jumper wires<br>
- <kbd> A nice fancy mailbox to keep in your lab so you can test things inside without needing to take your production mailbox down =)<br>
</details>

## Assembly instructions
I used a Pico WH on a breadboard to prototype this. I also added LEDs and a buzzer to help me see the state without hooking up a debugger. You can do that too if you want to, or just skip all of that and wire up the barebones setup in that section :point_down:

### Computer setup
I am not going to go very deep into this, it is instead left mostly as an exercise for the reader. Many guides exist on how to set up a Raspberry Pi Pico, and I am sure you can find one that suits your needs.
You will need some sort of computer to write the code on. You will need something with a USB port so that you can flash the Pico with your code.

#### My setup
- A MacBook Pro
- JetBrains PyCharm (community edition)
- Jetbrains MicroPython plugin
- Thonny (just for adding the MicroPython firmware to the Pico and then not touched again)

#### High level step-by-step instructions on how to setup
- Install Thonny _(I do not recommend pip for this as it resulted in SSL errors for me)_
- Connect the Pico to your computer via USB
- Use Thonny to add the MicroPython firmware to the Pico
- Install PyCharm
- Install the MicroPython plugin for PyCharm
- Write this code in PyCharm
```python
import machine
import utime

led_non_w = machine.Pin(25, machine.Pin.OUT)
led_w = machine.Pin("LED", machine.Pin.OUT)

while True:
    led_non_w.toggle()
    led_w.toggle()
    utime.sleep(1)
```
- use PyCharm to flash the code to the Pico
- Enjoy the little on-board LED blinking
- You are now ready to start working on the mailbox project

### Bare bones setup
_I am sure you won't have any issues, you don't need any of those flashy LEDs ;-)_

__TODO: wiring diagram from Fritzing__

### Full fat breadboard setup
picture of breadboard<br>
__TODO: wiring diagram from Fritzing__

### Sticking it in an actual mailbox
__TODO: Stick it all into an actual mailbox__

### Power draw, expected and actual (and adventures in power management)
__TODO: Measure power draw__
__TODO: Calculate Pico expected power usage__

## Platform
I went with a Raspberry Pi Pico WH running MicroPython since I have previous experience with Python and the tooling around Raspberry devices is usually quite nice to work with.
In addition to the hardware I also use a Home Assistant server (not that it matters but runs in Raspberry Pi4) to visualize the data from the mailbox.

This is local first setup (with the option to pay for Home Assistant Cloud in the future if I should want to).
In order to still get notifications on my phone I have set up a little companion app which subscribes to topic the Pico can post to. I went with https://ntfy.sh/ for this,

### Elaboration
I consider cloud functionality to be an unnecessary attack vector and an inconvenience for most of my use cases. Sure, it might be occasionally nice to have, but I prefer to keep things local and under my control.
This and the truly outstanding tooling around Raspberry Pi devices is why I went with Home Assistant on a Raspberry Pi.

I chose a MacBook Pro for my development environment simply because I have one. Without the MBP I would have used a Linux machine with all the same tooling.
Also, we are in Småland so why pay for a cloud service unless you need to?

(it makes sense to pay for a service such a GCP or AWS for when you don't want to or cant host your own metal. Using a cloud service to see the temperature in the room you are in is almost perverse)

## Code
The code can be found in this repo, you want the main.py file. Stick that on a Pico W (or WH) and watch it go.
I have taken some care to handle different setups from my own (you don't need all of my sensors, the buzzer nor the LEDs). You can also configure the pins to match your setup by editing the `settings.yaml` file.

The code is split into two main parts:
1. initialization / setup
2. main loop

### Initialization / setup
This part of the code is responsible for setting up the Pico and the sensors. It also reads the settings from the `settings.yaml` file and sets up the pins accordingly.
It also connects to wifi, pings external services (such as Home Assistant) and tries to reach the public internet to see which features can be used.

### Loading a yaml file in micro python
Since standard yaml parsers are not available in MicroPython, I had to write my own. It is quite limited and does not handle all yaml files, but it lets me use yaml for settings and gets the job done.
```python
def load_settings(file_name: str) -> dict:
    # with our own homegrown quite limited yaml parser
    # it does handle comments though, sort of
    with open(file_name, 'r') as file:
        _settings = {}
        lines = file.readlines()
        for line in lines:
            if line[0] == '#':
                pass
            elif len(line) == 0:
                pass
            else:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    _settings[key] = value
                elif len(parts) > 2:
                    key = parts[0].strip()
                    value = ":".join(parts[1:]).strip()
                    if "#" in value:
                        value = value.split("#")[0]
                    _settings[key] = value
                print(f"key: {key}, value: {value}")
        return _settings


settings_file_name: str = 'settings.yaml'
settings: dict = load_settings(settings_file_name)
```

### Main loop
The main loop continuously samples the attached sensors and checks if the past x samples can be considered a mail delivery or not. <br>
If a mail delivery is detected, the Pico will send a message to the Home Assistant server, ping the ntfy.sh service and blink the onboard LED and buzz the buzzer (assuming there is one connected)
The system will then enter a sleep mode for a set amount of time before starting the main loop again (this is to save power) the next day.

Since mail presence in the mailbox is a binary state, it makes little sense to continue to monitor the mailbox after a mail delivery has been detected.
If the user would like to wake the mailbox up early, there is also a reset button connected to the Pico which will wake it up from sleep and trigger a restart of the device.

### Determining if mail has been delivered in the last x samples
Since the main loop isn't very interesting on it's own, here is the logic for determining if mail has been delivered in the last x samples.
```python
def check_if_mail_has_been_delivered(list_of_samples: list) -> bool:
    """
        {'counter': counter,
        'lid_open': lid_open,
        'bottom_sensor_active': bottom_sensor_active,
        'tilt_sensor_active': tilt_sensor_active}
    """
    print(f"Checking if mail has been delivered")
    consecutive_tilt_sensor_active = 0
    consecutive_lid_open = 0
    consecutive_bottom_sensor_active = 0
    previous_sample = None
    for sample in list_of_samples:
        if previous_sample is None:
            previous_sample = sample
            continue
        if previous_sample is not None:
            if sample.get('tilt_sensor_active', False) and previous_sample.get('tilt_sensor_active', False):
                consecutive_tilt_sensor_active += 1
            elif not sample.get('tilt_sensor_active', False):
                consecutive_tilt_sensor_active = 0
            if sample.get('lid_open', False) and previous_sample.get('lid_open', False):
                consecutive_lid_open += 1
            elif not sample.get('lid_open', False):
                consecutive_lid_open = 0
            if sample.get('bottom_sensor_active', False) and previous_sample('bottom_sensor_active', False):
                consecutive_bottom_sensor_active += 1
            elif not sample.get('bottom_sensor_active', False):
                consecutive_bottom_sensor_active = 0
            previous_sample = sample
        if (consecutive_tilt_sensor_active > consecutive_tilt_sensor_active_needed_to_trigger
                or consecutive_lid_open > consecutive_lid_open_needed_to_trigger
                or consecutive_bottom_sensor_active > consecutive_bottom_sensor_active_needed_to_trigger):
            print(f"Mail has been delivered")
            return True
    print(f"Mail has not been delivered")
    return False
```

### Handling flaky wifi on the Pico
The Pico can be a bit flaky when it comes to connecting to wifi. I have added a simple retry mechanism to try to connect to wifi a few times before giving up and restarting the device.
```python
def connect() -> network.WLAN:
    print(f"Connecting to WiFi: {ssid}")
    if ssid == 'ssid_not_set' or password == 'password_not_set':  # noqa
        signal_error(ERROR_CODE_WIFI_NOT_CONFIGURED)
        raise ValueError(f"Please set your WiFi SSID and password in {settings_file_name}")
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)  # noqa
    wlan.active(True)
    wlan.connect(ssid, password)
    attempts = 0
    while not wlan.isconnected():
        print(f'Waiting for connection ({attempts}/{max_wifi_connect_attempts_before_resetting_device})...')
        time.sleep(1)
        led_on_board.toggle()  # noqa
        attempts += 1
        if attempts > max_wifi_connect_attempts_before_resetting_device:
            print(
                f"Could not connect to WiFi (after {attempts} attempts), please check your {settings_file_name} file and wifi status")
            signal_error(ERROR_CODE_WIFI_NOT_CONNECTED)
            print("Resetting the device")
            reset()
    print(wlan.ifconfig())
    signal_success(2)
    led_on_board.high()
    print(f"Connected to WiFi: {ssid}")
    return wlan
```

### Testing
#### What has been done
- Mailbox has been extensively tested in my lab as an assembled system.
- I have tested each individual sensor standalone to ensure that they work as expected (before assembly)
- The wifi connection, the Home Assistant connection and the ntfy.sh connection has also been tested in isolation and have simple error handling for common problems.
- There are some basic preflight checks before the main loop starts to ensure that the system is in a good state before starting the main loop.
- The classes imported from the Machine library have been mocked in mock.py which allows tests to be carried out on the logic separately from the hardware.  

#### What has NOT been done
There is little to no error handling for hardware malfunctions at run time (say one sensor out of 3 starts misbehaving, there is currently no logic to handle that)

#### What could have (reasonably) been done
Automated testing in a CI/CD pipeline would have been nice to have. I have not set this up as time is still not infinite and it would require having my own Github Runner in order to have a Pico hooked up to be able to test the whole system. 

## Data visualization
Mailbox is equipped with logic to send data to a Home Assistant server, which can then be used to visualize the data in a pretty straight forward way.<br><br>
__TODO: ADD SCREENSHOT__

## In the end
I have a mailbox that can tell me if mail has been delivered today or not. I can also see this information in Home Assistant and get notifications on my phone if I want to.
Looking back I cannot help but feel like this kind of microcontroller is gross overkill for this project but we need to also factor in speed of development, which is hard to beat for a project with a low low volume of one.

I can probably optimize things a fair bit by only powering on the Pico when the mailbox is opened, immediately going into mail detection mode and trying to connect to the wifi and send the message (mail or no mail) and then shutting down again. That would mean that I'd have a sort of hardware power switch in the lid which can turn the Pico on but not off when the lid closes again.
Since the Pico is a dual core microcontroller, I could also have one core running the main loop and the other core handling the wifi connection and message sending. This would allow me to have purer logic (as the current implementation can in practice miss mail delivery samples if it is in the middle of flashing ligths or buzzing a buzzer since only one thread is used and execution is strictly sequential)
I could implement requests to a somewhat accessible PostNord API to determine if today is a PostNord delivery day or not. This could be displayed as a sensor in Home Assistant too.
I could add a little ultra sound sensor to detect if something is by the mailbox for x seconds (or longer) to try to figure out if the post car has been there or not (it would take at least a solid 5-10 seconds for a mailman to stop, deliver mail and do a burnout).
I could add a little handy button for the mailman to press (if they feel like it) to explicitly trigger a mail delivery event.
Next up after that I reccon we'd be in image processing territory. But really, I 100% expect a system with just one button and an electric flip switch hooked up to a light (which would then stay on) to work just about as well as anything mentioned ☝️

Overall, I am pleased with my setup and choice of tools. Home Assistant performed well and was a dream to setup. Ntfy.sh was also a breeze to setup and use. The Pico can be a bit flaky in terms of connecting to wifi but wasn't difficult to work around with a few lines of code.