# Install requirements

1. `python3 -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -r requirements.txt`

# Setup raspberry and LED

## Material

You will need : 

1. A breadboard
2. 2 resistance
3. 2 LEDs
4. 4 cables male/female
5. The raspberry, of course.

## Understanding breadboard

A breadboard is segmented into lines and column: 

- You have lines A,B,C,D,E,F,G,H,I,J
- You have columns [1,64]

Lines are divided into two parts : [A,B,C,D,E] and [F,G,H,I,J]. Theses 2 parts are NOT connected together.  

Different columns are NOT connected together.  

A valid connection would be for example : [A10,B10,C10,E10,F10]. For example, if you need to connecte the raspberry input to resistance input, it needs to be one the same column. But the resistance output can be on another column.  

For example, you could do the following montage:

1. GPIO (Raspberry input): A10
2. Resistance input: C10
3. Resistance output: C6
4. LED input: E6
5. LED output: E4
6. Ground (Raspberry output): C4

It looks like this:

[insert 3 photos]

## Raspberry input and output: which pins to use?

In order to plug your LEDs, you need to know the input and output PINs on your raspberry. Input needs to be a GPIO PIN and output needs to be a Ground PIN. A raspberry 3 have 40 PINs, some are ground, some are GPIO and some are of an other type. You need a reliable method to properly identify PINs to use.

You can use the following command on your raspberry to identify the PINs:

```bash
pinout
```

```
Wi-fi              : True
Bluetooth          : True
Camera ports (CSI) : 1
Display ports (DSI): 1

,--------------------------------.
| oooooooooooooooooooo J8     +====
| 1ooooooooooooooooooo        | USB
|                             +====
| o1 RUN  Pi Model 3B  V1.2      |
| |D      +---+               +====
| |S      |SoC|               | USB
| |I      +---+               +====
| |0               C|            |
|                  S|       +======
|                  I| |A|   |   Net
| pwr      |HDMI|  0| |u|   +======
`-| |------|    |-----|x|--------'

J8:
   3V3  (1) (2)  5V    
 GPIO2  (3) (4)  5V    
 GPIO3  (5) (6)  GND   
 GPIO4  (7) (8)  GPIO14
   GND  (9) (10) GPIO15
GPIO17 (11) (12) GPIO18
GPIO27 (13) (14) GND   
GPIO22 (15) (16) GPIO23
   3V3 (17) (18) GPIO24
GPIO10 (19) (20) GND   
 GPIO9 (21) (22) GPIO25
GPIO11 (23) (24) GPIO8 
   GND (25) (26) GPIO7 
 GPIO0 (27) (28) GPIO1 
 GPIO5 (29) (30) GND   
 GPIO6 (31) (32) GPIO12
GPIO13 (33) (34) GND   
GPIO19 (35) (36) GPIO16
GPIO26 (37) (38) GPIO20
   GND (39) (40) GPIO21

RUN:
RUN (1)
GND (2)

For further information, please refer to https://pinout.xyz/
```

In the schematic, PIN 1 is labeled, all other are 0. This help you identify the correct placements of PIN number.  

For example, If we take the previous example, you could set GPIO (Raspberry input) in PIN 40, and Ground (raspberry output) in PIN 39.

Then, in the code, change the values of LEDs input PINs:

```python
PIN_LED_1  = 40
```

# Run the code

`python3 ./code.py`
