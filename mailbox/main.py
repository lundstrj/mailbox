import time
from machine import Pin, reset, lightsleep, idle
# from mock import Pin
import network
import urequests
import ujson

# Define error codes
ERROR_CODE_WIFI_NOT_CONNECTED = 2
ERROR_CODE_HOME_ASSISTANT_NOT_CONNECTED = 4
ERROR_CODE_KEYBOARD_INTERRUPT = 6
ERROR_CODE_WIFI_NOT_CONFIGURED = 8
ERROR_CODE_NO_SENSORS_CONNECTED = 12
GOING_TO_SLEEP = 10
RESETTING = 1

# VERBOSITY LEVELS
ALWAYS_PRINT = -1
DEBUG = 1

# Potentially useful globals
NOT_SET = -1
has_mail_been_delivered: bool = False
previous_has_mail_been_delivered: bool = False
lid_open: bool = False
bottom_sensor_active: bool = False
tilt_sensor_active: bool = False
reset_sensor_active: bool = False
verbose_level: int = 5
wlan: network.WLAN


def debug_print(message: str, level: int = 0) -> None:
    if verbose_level >= level:
        print(message)


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
                debug_print(f"key: {key}, value: {value}")
        return _settings


settings_file_name: str = 'settings.yaml'
settings: dict = load_settings(settings_file_name)

# set the SSID and password of your WiFi along with other useful settings
ssid: str = settings.get('wifi_ssid', 'ssid_not_set')
password: str = settings.get('wifi_password', 'wifi_password_not_set')
ntfy_topic: str = settings.get('ntfy_topic', 'not_set')
if ntfy_topic == 'not_set':
    debug_print(f"Please set your NTFY topic in {settings_file_name}")
    debug_print(f"Will run mailbox without NTFY integration")
else:
    debug_print(f"ntfy_topic: {ntfy_topic}")
home_assistant_url: str = settings.get('home_assistant_url', 'http://homeassistant.local:8123/')
home_assistant_token: str = settings.get('home_assistant_bearer_token', 'not_set')
home_assistant_is_configured = True
if home_assistant_token == 'not_set' or home_assistant_token == 'your_home_assistant_bearer_token' or len(
        home_assistant_token) < 40:
    debug_print(f"Please set your Home Assistant Bearer Token in {settings_file_name}")
    debug_print(f"Will run mailbox without Home Assistant integration")
    home_assistant_is_configured = False
home_assistant_unique_id: str = settings.get('home_assistant_unique_id', 'net_set')
home_assistant_entity_id: str = settings.get('home_assistant_entity_id', 'not_set')
consecutive_tilt_sensor_active_needed_to_trigger: int = int(
    settings.get('consecutive_tilt_sensor_active_needed_to_trigger', 5))
consecutive_lid_open_needed_to_trigger: int = int(settings.get('consecutive_lid_open_needed_to_trigger', 5))
consecutive_bottom_sensor_active_needed_to_trigger: int = int(settings.get(
    'consecutive_bottom_sensor_active_needed_to_trigger', 10))
max_wifi_connect_attempts_before_resetting_device: int = int(
    settings.get('max_wifi_connect_attempts_before_resetting_device', 10))
sliding_window_size: int = int(settings.get('sliding_window_size', 60))
sampling_interval: float = float(settings.get('sampling_interval', 0.5))

led_green_pin: int = int(settings.get('led_green_pin', NOT_SET))
led_yellow_pin: int = int(settings.get('led_yellow_pin', NOT_SET))
led_red_pin: int = int(settings.get('led_red_pin', NOT_SET))
buzzer_pin: int = int(settings.get('buzzer_pin', NOT_SET))

# Define the pins for output
led_on_board: Pin = Pin("LED", Pin.OUT)
output_pins = [led_on_board]
if led_green_pin != NOT_SET:
    debug_print(f"led_green_pin: {led_green_pin}")
    led_green: Pin = Pin(led_green_pin, Pin.OUT)
    output_pins.append(led_green)
else:
    debug_print(f"No led_green_pin set in {settings_file_name}")
if led_yellow_pin != NOT_SET:
    debug_print(f"led_yellow_pin: {led_yellow_pin}")
    led_yellow: Pin = Pin(led_yellow_pin, Pin.OUT)
    output_pins.append(led_yellow)
else:
    debug_print(f"No led_yellow_pin set in {settings_file_name}")
if led_red_pin != NOT_SET:
    debug_print(f"led_red_pin: {led_red_pin}")
    led_red: Pin = Pin(led_red_pin, Pin.OUT)
    output_pins.append(led_red)
else:
    debug_print(f"No led_red_pin set in {settings_file_name}")
if buzzer_pin != NOT_SET:
    debug_print(f"buzzer_pin: {buzzer_pin}")
    buzzer: Pin = Pin(buzzer_pin, Pin.OUT)
else:
    debug_print(f"No buzzer_pin set in {settings_file_name}")

sensor_bottom_pin: int = int(settings.get('sensor_bottom_pin', NOT_SET))
sensor_tilt_pin: int = int(settings.get('sensor_tilt_pin', NOT_SET))
sensor_lid_pin: int = int(settings.get('sensor_lid_pin', NOT_SET))
sensor_reset_pin: int = int(settings.get('sensor_reset_pin', NOT_SET))
wake_source_pin: int = int(settings.get('wake_source_pin', NOT_SET))
proximity_sensor_pin: int = int(settings.get('proximity_sensor_pin', NOT_SET))

# Define the pins for input
if sensor_bottom_pin != NOT_SET:
    debug_print(f"sensor_bottom_pin: {sensor_bottom_pin}")
    sensor_bottom: Pin = Pin(sensor_bottom_pin, Pin.IN, pull=Pin.PULL_UP)
else:
    debug_print(f"No sensor_bottom_pin set in {settings_file_name}")
if sensor_tilt_pin != NOT_SET:
    debug_print(f"sensor_tilt_pin: {sensor_tilt_pin}")
    sensor_tilt: Pin = Pin(sensor_tilt_pin, Pin.IN, pull=Pin.PULL_UP)
else:
    debug_print(f"No sensor_tilt_pin set in {settings_file_name}")
if sensor_lid_pin != NOT_SET:
    debug_print(f"sensor_lid_pin: {sensor_lid_pin}")
    sensor_lid: Pin = Pin(sensor_lid_pin, Pin.IN, pull=Pin.PULL_UP)
else:
    debug_print(f"No sensor_lid_pin set in {settings_file_name}")
if sensor_reset_pin != NOT_SET:
    debug_print(f"sensor_reset_pin: {sensor_reset_pin}")
    sensor_reset: Pin = Pin(sensor_reset_pin, Pin.IN, pull=Pin.PULL_UP)
else:
    debug_print(f"No sensor_reset_pin set in {settings_file_name}")
if wake_source_pin != NOT_SET:
    debug_print(f"wake_source_pin: {wake_source_pin}")
    wake_source: Pin = Pin(wake_source_pin, Pin.IN, pull=Pin.PULL_UP)
    wake_source.irq(handler=None, trigger=Pin.IRQ_RISING)
else:
    debug_print(f"No wake_source_pin set in {settings_file_name}")
if proximity_sensor_pin != NOT_SET:
    debug_print(f"proximity_sensor_pin: {proximity_sensor_pin}")
    proximity_sensor: Pin = Pin(proximity_sensor_pin, Pin.IN, pull=Pin.PULL_UP)
else:
    debug_print(f"No proximity_sensor_pin set in {settings_file_name}")

"""
assert ssid != 'your_ssid', f"Please set your WiFi SSID in {settings_file_name}" # noqa
assert password != 'your_password', f"Please set your WiFi password in {settings_file_name}"  # noqa
assert home_assistant_token != 'your_token', f"Please set your Home Assistant Bearer Token in {settings_file_name}" # noqa
assert home_assistant_unique_id != 'net_set', f"Please set your Home Assistant Unique ID in {settings_file_name}" # noqa
assert home_assistant_entity_id != 'not_set', f"Please set your Home Assistant Entity ID in {settings_file_name}" # noqa
"""


def has_bottom_sensor() -> bool:
    try:
        sensor_bottom.value()
        return True
    except AttributeError:
        return False


def has_tilt_sensor() -> bool:
    try:
        sensor_tilt.value()
        return True
    except AttributeError:
        return False


def has_lid_sensor() -> bool:
    try:
        sensor_lid.value()
        return True
    except AttributeError:
        return False


def has_reset_sensor() -> bool:
    try:
        sensor_reset.value()
        return True
    except AttributeError:
        return False


def has_wake_source() -> bool:
    try:
        wake_source.value()
        return True
    except AttributeError:
        return False


def has_buzzer() -> bool:
    try:
        buzzer.value()
        return True
    except AttributeError:
        return False


def set_all_output_pins(to_low: bool = True, to_high: bool = False) -> None:
    for pin in output_pins:
        if to_low:
            pin.low()
        elif to_high:
            pin.high()


def flash_led(led: Pin, flashes: int = 5, flash_duration: float = 0.1) -> None:
    debug_print(f'flashing led: {flashes} times for {flash_duration} seconds each')
    for i in range(flashes):
        led.high()
        time.sleep(flash_duration)
        led.low()
    debug_print('flashing led: done')


def slow_flash_led(led: Pin, flashes: int = 5, flash_duration: float = 1) -> None:
    flash_led(led, flashes, flash_duration)


def buzz_buzzer(buzzes: int = 5, buzz_duration: float = 0.1) -> None:
    if has_buzzer():
        debug_print(f'buzzing the buzzer: {buzzes} times for {buzz_duration} seconds each')
        for i in range(buzzes):
            buzzer.high()
            time.sleep(buzz_duration)
            buzzer.low()
        debug_print('buzzing the buzzer: done')
    else:
        debug_print("No buzzer connected")


def cycle_lights(cycles: int = 5) -> None:
    for i in range(cycles):
        debug_print(f'toggling lights: {i}/{cycles}')
        for led in output_pins:
            led.toggle()
            time.sleep(0.1)
        leds = output_pins.copy()
        leds.reverse()
        for led in leds:
            led.toggle()
            time.sleep(0.1)
    debug_print('toggling lights: done')


def signal_error(error_code: int = 1) -> None:
    debug_print(f"Signaling error code: {error_code}")
    buzz_buzzer(5)
    flash_led(led_on_board, 5)
    buzz_buzzer(5)
    slow_flash_led(led_on_board, error_code)
    debug_print(f"Signaling error code: {error_code} done")


def signal_success(success_code: int = 1) -> None:
    debug_print(f"Signaling success: {success_code}")
    buzz_buzzer(2, buzz_duration=0.05)
    flash_led(led_on_board, 2)
    buzz_buzzer(2, buzz_duration=0.05)
    slow_flash_led(led_on_board, success_code)
    debug_print(f"Signaling success: {success_code} done")


def connect() -> network.WLAN:
    debug_print(f"Connecting to WiFi: {ssid}")
    if ssid == 'ssid_not_set' or password == 'password_not_set':  # noqa
        signal_error(ERROR_CODE_WIFI_NOT_CONFIGURED)
        raise ValueError(f"Please set your WiFi SSID and password in {settings_file_name}")
    # Connect to WLAN
    wlan_ = network.WLAN(network.STA_IF)  # noqa
    wlan_.active(True)
    wlan_.connect(ssid, password)
    attempts = 0
    while not wlan_.isconnected():
        debug_print(f'Waiting for connection ({attempts}/{max_wifi_connect_attempts_before_resetting_device})...')
        time.sleep(1)
        led_on_board.toggle()  # noqa
        attempts += 1
        if attempts > max_wifi_connect_attempts_before_resetting_device:
            debug_print(
                f"Could not connect to WiFi (after {attempts} attempts), please check your {settings_file_name} file and wifi status")
            signal_error(ERROR_CODE_WIFI_NOT_CONNECTED)
            debug_print("Resetting the device")
            reset()
    debug_print(wlan_.ifconfig())
    signal_success(2)
    led_on_board.high()
    debug_print(f"Connected to WiFi: {ssid}")
    return wlan_


def send_telemetry_to_ha(mail_has_been_delivered: bool) -> None:
    if not home_assistant_is_configured:
        debug_print(f"Home Assistant Bearer Token is not set, please set it in {settings_file_name}")
        signal_error(ERROR_CODE_HOME_ASSISTANT_NOT_CONNECTED)
        return None
    state = 0
    if mail_has_been_delivered:
        state = 1
    debug_print(f"Sending telemetry to Home Assistant: {state} mail in box")
    data = {
        "state": state,
        "attributes": {
            "device_class": "enum",
            "friendly_name": "Smart Mailbox",
            "unit_of_measurement": "Mail in box",
            "state_class": None,
            "unique_id": home_assistant_unique_id
        }
    }
    headers = {
        "Authorization": f"Bearer {home_assistant_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    json = ujson.dumps(data).encode('utf-8')
    url = f"{home_assistant_url}api/states/{home_assistant_entity_id}"
    response = urequests.post(url, data=json, headers=headers)  # noqa
    debug_print(f"Response from Home Assistant: {response.status_code}")
    debug_print(response.text)


def send_telemetry_to_ntfy(mail_has_been_delivered: bool = False, optional_message: str = None) -> urequests.Response:
    debug_print(f"Sending telemetry to NTFY")
    if ntfy_topic == 'not_set':
        debug_print(f"Please set your NTFY topic in {settings_file_name}")
        return
    else:
        debug_print(f"Sending telemetry to NTFY: {ntfy_topic} - Mail has been delivered: {mail_has_been_delivered}")
    url_str = f"https://ntfy.sh/{ntfy_topic}"
    if optional_message is not None:
        debug_print(f"Sending telemetry to NTFY: {optional_message}")
        response = urequests.post(url_str, data=optional_message)
    else:
        if mail_has_been_delivered:
            debug_print(f"Sending telemetry to NTFY: Mail has been delivered")
            response = urequests.post(url_str, data=b"Mail has been delivered")
        else:
            debug_print(f"Sending telemetry to NTFY: Mail has not been delivered")
            response = urequests.post(url_str, data=b"Mail has not been delivered")
    debug_print(f"Response from NTFY: {response.status_code}")
    return response


def check_if_mail_has_been_delivered(list_of_samples: list) -> bool:
    """
        {'lid_open': lid_open,
        'bottom_sensor_active': bottom_sensor_active,
        'tilt_sensor_active': tilt_sensor_active}
    """
    debug_print(f"Checking if mail has been delivered")
    consecutive_tilt_sensor_active = 0
    consecutive_lid_open = 0
    consecutive_bottom_sensor_active = 0
    previous_sample = None
    if len(list_of_samples) < 10:
        debug_print(f"Too few samples to determine if mail has been delivered")
        return False
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
            if sample.get('bottom_sensor_active', False) and previous_sample.get('bottom_sensor_active', False):
                consecutive_bottom_sensor_active += 1
            elif not sample.get('bottom_sensor_active', False):
                consecutive_bottom_sensor_active = 0
            previous_sample = sample
        if (consecutive_tilt_sensor_active > consecutive_tilt_sensor_active_needed_to_trigger
                or consecutive_lid_open > consecutive_lid_open_needed_to_trigger
                or consecutive_bottom_sensor_active > consecutive_bottom_sensor_active_needed_to_trigger):
            debug_print(f"Mail has been delivered")
            return True
    debug_print(f"Mail has not been delivered")
    return False


def goto_sleep(duration: int = 0) -> None:
    """
    Failed attempt at using Raspberry Pi Pico's deepsleep.
    This was cut from scope in order to ship the project.
    Leaving it here for possible future use.
    :param duration:
    :return:
    """
    global wlan
    if duration > 0:
        debug_print(f"Going to sleep for {duration} seconds ({duration / 60 / 60} hours or {duration * 1000} milliseconds)")
        signal_success(GOING_TO_SLEEP)
        half_hour_sleeps = int(duration / (30*60))  # 30 minutes
        debug_print(f"That will be {half_hour_sleeps} half hour sleeps")
        debug_print("But first wifi needs to be disconnected")
        wlan.disconnect()
        debug_print("Wifi disconnected")

        debug_print(f"Entering first sleep out of {half_hour_sleeps}...")
        for i in range(half_hour_sleeps):
            debug_print(f"Sleeping for 30 minutes ({i}/{half_hour_sleeps})")
            milliseconds = 30 * 60 * 1000
            debug_print(f"Going to sleep for 30 minutes: {milliseconds} milliseconds")
            lightsleep(milliseconds)
            debug_print(f"Waking up from sleep {i}")
    else:
        if has_wake_source():
            debug_print("Going to deep sleep forever (until interrupted)")
            signal_success(GOING_TO_SLEEP)
            lightsleep()
        else:
            debug_print("Going to sleep for 20 hours (since there is no wake source)")
            signal_success(GOING_TO_SLEEP)
            lightsleep(20 * 60 * 60 * 1000)
    debug_print("Waking up from sleep")
    time.sleep(1)
    wake_source.low()


def main():
    global wlan, has_mail_been_delivered, reset_sensor_active, tilt_sensor_active, bottom_sensor_active, lid_open, previous_has_mail_been_delivered
    debug_print("Starting main")
    set_all_output_pins(to_low=True)
    cycle_lights()

    if not has_lid_sensor() and not has_bottom_sensor() and not has_tilt_sensor():
        debug_print("You need at least one sensor connected in order to run this program")
        signal_error(ERROR_CODE_NO_SENSORS_CONNECTED)
        idle()
    try:
        debug_print("Trying to connect to WLAN")
        wlan = connect()
        debug_print("Connected to WLAN")
    except KeyboardInterrupt:
        debug_print("KeyboardInterrupt")
        signal_error(ERROR_CODE_KEYBOARD_INTERRUPT)
        reset()
    except ValueError as e:
        debug_print(f"ValueError: {e}")
        led_on_board.high()
        reset()

    past_samples = []
    attempts = 0
    max_attempts = 10
    while True:
        if attempts > max_attempts:
            debug_print(f"Could not send telemetry to Home Assistant after {max_attempts} attempts")
            signal_error(ERROR_CODE_HOME_ASSISTANT_NOT_CONNECTED)
            raise Exception(f"Could not send telemetry to Home Assistant despite {attempts} attempts")
        try:
            send_telemetry_to_ha(False)  # resetting the state in Home Assistant
            break
        except OSError:
            attempts += 1
            time.sleep(1)

    while True:
        """
        # Failed attempt at getting the current time from NTP.
        # Leaving the code here for possible future use
        # check the local time and if it is between 10pm and 6am, go to sleep until 6am
        current_time = time.localtime()
        if current_time[3] >= 18 or current_time[3] < 6:
            debug_print("It is between 18:00 and 06:00, going to sleep until 06:00")
            # calculate the time until 6am
            hours_until_6am = 6 - current_time[3]
            minutes_until_6am = 60 - current_time[4]
            seconds_until_6am = 60 - current_time[5]
            seconds_until_6am += minutes_until_6am * 60
            seconds_until_6am += hours_until_6am * 60 * 60
            goto_sleep(seconds_until_6am)
        else:
            debug_print("It is not between 18:00 and 06:00, continuing with the program")
        """
        time.sleep(sampling_interval)
        flash_led(led_on_board, 2)
        if has_lid_sensor():
            if sensor_lid.value():
                debug_print("Lid is open", level=DEBUG)
                lid_open = True
                led_yellow.high()
                time.sleep(0.1)
            elif not sensor_lid.value():
                debug_print("Lid is closed", level=DEBUG)
                lid_open = False
                led_yellow.low()
        if has_bottom_sensor():
            if not sensor_bottom.value():
                debug_print("sensor_bottom is active", level=DEBUG)
                bottom_sensor_active = True
                led_red.high()
                time.sleep(0.1)
            elif sensor_bottom.value():
                debug_print("sensor_bottom is inactive", level=DEBUG)
                bottom_sensor_active = False
                led_red.low()
        if has_tilt_sensor():
            if sensor_tilt.value():
                debug_print("sensor_tilt is active", level=DEBUG)
                tilt_sensor_active = True
                led_green.high()
                time.sleep(0.1)
            elif not sensor_tilt.value():
                debug_print("sensor_tilt is inactive", level=DEBUG)
                tilt_sensor_active = False
                led_green.low()
        if has_reset_sensor():
            if not sensor_reset.value():
                debug_print("sensor_reset is active", level=DEBUG)
                reset_sensor_active = True
                led_green.high()
                led_yellow.high()
                led_red.high()
                if has_mail_been_delivered:
                    debug_print("#" * 50, level=DEBUG)
                    debug_print("Resetting mail delivery status", level=DEBUG)
                    debug_print("#" * 50, level=DEBUG)
                    has_mail_been_delivered = False
                    past_samples = []
            elif sensor_reset.value():
                led_green.low()
                led_yellow.low()
                led_red.low()
                debug_print("sensor_reset is inactive", level=DEBUG)
                reset_sensor_active = False
        past_samples.append({'lid_open': lid_open,
                             'bottom_sensor_active': bottom_sensor_active,
                             'tilt_sensor_active': tilt_sensor_active,
                             'reset_sensor_active': reset_sensor_active})
        if len(past_samples) > sliding_window_size:
            past_samples.pop(0)
        if not has_mail_been_delivered:
            has_mail_been_delivered = check_if_mail_has_been_delivered(past_samples)
            if has_mail_been_delivered:
                debug_print("New mail has been delivered")
                buzz_buzzer(5)
        if has_mail_been_delivered:
            debug_print("Mail is in the mailbox")
            flash_led(led_on_board, 5)
        if has_mail_been_delivered != previous_has_mail_been_delivered:
            # we have a state change and should update Home Assistant, and then we can go to sleep until interrupted OR for a set duration
            set_all_output_pins(to_low=True)
            send_telemetry_to_ntfy(has_mail_been_delivered)
            send_telemetry_to_ha(has_mail_been_delivered)
            # goto_sleep(duration=20 * 60 * 60)  # leaving this here for future use
            while True:
                debug_print("Going to sleep for 10 seconds")
                time.sleep(10)
                flash_led(led_on_board, 1)
                debug_print("Waking up from sleep")
                debug_print("Checking if the reset sensor is active")
                if has_reset_sensor():
                    if not sensor_reset.value():
                        flash_led(led_green, 2)
                        flash_led(led_yellow, 2)
                        flash_led(led_red, 2)
                        signal_success(RESETTING)
                        debug_print("sensor_reset is active")
                        has_mail_been_delivered = False
                        past_samples = []
                        send_telemetry_to_ntfy(optional_message="Mailbox has been reset")
                        send_telemetry_to_ha(False)
                        break
                    else:
                        debug_print("Reset sensor is not active, will go to sleep again")

        previous_has_mail_been_delivered = has_mail_been_delivered
        if len(past_samples) > 1:
            print_status = False
            if past_samples[-1].get('lid_open', False) != past_samples[-2].get('lid_open', False):
                print_status = True
            elif past_samples[-1].get('bottom_sensor_active', False) != past_samples[-2].get('bottom_sensor_active', False):
                print_status = True
            elif past_samples[-1].get('tilt_sensor_active', False) != past_samples[-2].get('tilt_sensor_active', False):
                print_status = True
            elif past_samples[-1].get('reset_sensor_active', False) != past_samples[-2].get('reset_sensor_active', False):
                print_status = True
            if print_status:
                debug_print(f"sensor_lid.value(): {sensor_lid.value()}", level=ALWAYS_PRINT)
                debug_print(f"sensor_bottom.value(): {sensor_bottom.value()}", level=ALWAYS_PRINT)
                debug_print(f"sensor_tilt.value(): {sensor_tilt.value()}", level=ALWAYS_PRINT)
                debug_print(f"sensor_reset.value(): {sensor_reset.value()}", level=ALWAYS_PRINT)


main()
