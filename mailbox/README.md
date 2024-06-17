# Mailbox
A simple setup for knowing if someone (maybe a even a mailman) has been fiddling with your mailbox today.

## Overview
My current residence get intermittent mail delivery (supposedly every other day for mail, but packages can come any day). Some days you don't get anything even if it is a mail delivery day. The mail also gets deliverd at different times depending on reasons (I suppose), so what does one do? Well you go check your mailbox at least 5+ times per day just to be sure. If only there was a better way.

picture of mailbox
video of operation

## Objective
The idea here is to hook up a couple of sensors to a regular physical snailmailbox, do so discretely enough to not alarm the mailman and to have a somewhat smart way of determining if mail has indeed been delivered today or not, thus taking the guessing game out of having a mailbox and cutting down on mailbox round trips.

## Bill of materials
- [ ] 1x Raspberry Pi Pico W
- [ ] 3x push buttons with low force actuation
- [ ] 1x tilt sensor
- [ ] x assorted wires of varying lengths and colors (your call, you can make then all white if you want)
- [ ] tape is always good to have around

<details>
<summary>Other useful things</summary>
- <kbd> Breadboard<br>
- <kbd> 3x LEDs<br>
- <kbd> approximately 500 jumper wires<br>
</details>

## Assembly instructions
I used a Pico WH on a breadboard to prototype this. I also added LEDs and a buzzer to help me see the state without hooking up a debugger. You can do that too if you want to, or just skip all of that and wire up the barebones setup in that section :point_down:

### Bare bones setup
_I am sure you won't have any issues, you don't need any of those flashy LEDs ;-)_

wiring diagram

### Full fat breadboard setup
picture of breadboard
wiring diagram

### Sticking it in an actual mailbox
picture

## Safe operation instructions
1. Assemble your setup
2. Flash the Pico with the software
3. Connect power to the Pico
4. Wait for mail to be delivered
5. If and when you go to check the mailbox, remember to press the reset button a little press so the system can go into mail detection state again =)

## Unsafe operation instructions
Basically just do what the safe instruction suggest whilst playing with matches or juggling knives (dealers choice).

## Setup

## Platform
Raspberry Pi Pico W?

## Code
The code can be found in this repo, you want the main.py file. Stick that on a Pico W (or WH) and watch it go.

## Data visualization
Mailbox is equipped with logic to send data to a Home Assistant server, which can then be used to visualize the data in a pretty straight forward way.

## In the end