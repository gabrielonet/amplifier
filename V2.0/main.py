#!/usr/bin/python
import time
import os
from time import sleep
import multiprocessing
from multiprocessing import Process, Value
import RPi.GPIO as GPIO
import Adafruit_ADS1x15
import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from kivy.uix.button import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.dropdown import DropDown
from kivy.base import runTouchApp
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty,StringProperty,ReferenceListProperty,ObjectProperty
from kivy.lang import Builder
from w1thermsensor import W1ThermSensor

GPIO.setmode(GPIO.BCM)
GPIO.setup(5,  GPIO.OUT, initial=GPIO.HIGH) # 80 m relay
GPIO.setup(6,  GPIO.OUT, initial=GPIO.HIGH) # 40 m relay
GPIO.setup(13, GPIO.OUT, initial=GPIO.HIGH) # 20 m relay
GPIO.setup(19, GPIO.OUT, initial=GPIO.HIGH) # 15 m relay
GPIO.setup(26, GPIO.OUT, initial=GPIO.HIGH) # 10 m relay
GPIO.setup(16, GPIO.OUT, initial=GPIO.HIGH) # ptt enable
GPIO.setup(20, GPIO.OUT, initial=GPIO.HIGH) # power relay
GPIO.setup(21, GPIO.OUT, initial=GPIO.HIGH) # reset protection
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP) # ptt transmit indicator
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP) # input power overdrive
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Drain current alarm
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP) # swr alarm
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP) # filter alarm

GPIO.output(21,  0) # reset on
sleep(0.1)
GPIO.output(21,  1) # reset off





def dallas(dummy,temp_1,speed):
    sensor = W1ThermSensor()
    GPIO.setup(17, GPIO.OUT, initial=GPIO.LOW) # PWM FAN_PIN
    fan = GPIO.PWM(17, 25)
    fan.start(0)
    print 'Set fan'
    fan.ChangeDutyCycle(100)
    while True:
        temp_1.value = sensor.get_temperature()
        speed.value = int(100-temp_1.value)
        if 30 >= temp_1.value >= 0:  speed.value = 45
        if 35 >= temp_1.value > 30:  speed.value = 50
        if 40 >= temp_1.value > 35:  speed.value = 60
        if 45 >= temp_1.value > 40:  speed.value = 70
        if 50 >= temp_1.value > 45:  speed.value = 80
        if 55 >= temp_1.value > 50:  speed.value = 90
        if 60 >= temp_1.value > 55:  speed.value = 100
        fan.ChangeDutyCycle(speed.value)
        
def analog(dummy, fwd):
    adc = Adafruit_ADS1x15.ADS1115()
    while True:
        fwd.value   = (adc.read_adc(3, gain=1, data_rate=860) * 0.1262)/1000
        ref.value   = (adc.read_adc(2, gain=1, data_rate=860) * 0.1262)/1000
        drain.value = (adc.read_adc(1, gain=1, data_rate=860) * 0.1262)/1000

class Main_Screen(FloatLayout):
        fwd_proc   = NumericProperty(0)
        ref_proc   = NumericProperty(0)
        drain_proc = NumericProperty(0)
        ptt = StringProperty('Stand By')
        temp = NumericProperty(0)
        speed_1 = NumericProperty(0)
        input_led = StringProperty('img/green-led.png')
        swr_led   = StringProperty('img/green-led.png')
        power_led = StringProperty("img/off.png")
        drain_led = StringProperty('img/green-led.png')
        filters_led = StringProperty('img/green-led.png')
        fault_status = False
        ht_bol = False
        ref = 1.97 # pentru 100 W
        #ref = 2.22 # pentru 1 kW
        power_text =StringProperty('[color=#008000]QRO Off[/color]')
        def home(self):
            if self.fault_status == False :
                self.ids._screen_manager.current = 'home' 
        def power (self):
            self.ht_bol = not self.ht_bol
            if self.ht_bol == True:
                self.power_text = '[color=#FF0000]QRO On[/color]'
                self.power_led = "img/on.png"
                GPIO.output(21,  0) # reset on
                sleep(0.1)
                GPIO.output(21,  1) # reset off
                GPIO.output(20,  0) #power relay on
                GPIO.output(16,  0) # ptt  ena relay on
                self.ids._screen_manager.current = 'home'

            if self.ht_bol == False :
                self.power_led = "img/off.png"
                GPIO.output(20,  1)    
                GPIO.output(16,  1)
                self.power_text = '[color=#008000]QRO Off[/color]'
                self.ptt = '[size=20][b][color=#FFC800]Stand By[/color][/size][/b]'

        def swr(self):
            if  GPIO.input(23) == 0:
                self.swr_led = 'img/red-led.png'
                self.fault()

            else:
                self.swr_led = 'img/green-led.png'
        def input(self):
            if (GPIO.input(22) == 0) :
                self.input_led = 'img/red-led.png'
                self.fault()
            else:                
                self.input_led = 'img/green-led.png'
        def drain(self):
            if  GPIO.input(27) == 0:
                self.drain_led = 'img/red-led.png'
                self.fault()
            else:
                self.drain_led = 'img/green-led.png'
        def filters(self):
            if  GPIO.input(24) == 0:
                self.filters_led = 'img/red-led.png'
                self.fault()
            else:
                self.filters_led = 'img/green-led.png'

        def fault(self):
            self.ht_bol = True ; self.power()
            self.ids._screen_manager.current = 'System'
 
        def sys_shut_down(arg):
            os.system("shutdown now -h")
        def sys_reboot(arg):
            os.system("reboot")            


        def band_relay(dummy, band):
            GPIO.output(5,  1); GPIO.output(6,  1); GPIO.output(13, 1); GPIO.output(19, 1); GPIO.output(26, 1) # set all relays to off
            if band == 80:
                GPIO.output(5,  0)
            if band == 40:
                GPIO.output(6,  0)                
            if band == 20:
                GPIO.output(13, 0)                
            if band == 15:
                GPIO.output(19, 0)
            if band == 10:
                GPIO.output(26, 0)
        def ptt_read(self,dummy):
            if (GPIO.input(12) == 0 and self.ht_bol == True ) :
                self.ptt =  '[size=20][b][color=#FF0600]Transmit[/color][/size][/b]'
            if (GPIO.input(12) == 1 and self.ht_bol == True ) :
                self.ptt = '[size=20][b][color=#00D53C]Receive[/color][/size][/b]'
            if (self.ht_bol == False ) :
                self.ptt = '[size=20][b][color=#FFC800]Stand By[/color][/size][/b]'

            

        def update(self,*args):
            s1 = 10 ** (   (self.ref - fwd.value)/0.025/10     )
            self.fwd_proc = (1/s1)*100
            
            s2 = 10 ** (   (self.ref - ref.value)/0.025/10     )
            self.ref_proc = (1/s2)*100
            
            self.drain_proc  = (drain.value*100)/3.3
            self.temp = temp_1.value
            self.speed_1 = speed.value
            self.ptt_read('dummy')
            self.swr()
            self.drain()
            self.filters()
            self.input()
        

            
class MyApp(App):
      
    def build(self):
        # Set up the layout:
        layout = FloatLayout()
        #Instantiate  UI objects ):
        main_screen = Main_Screen()
        GPIO.add_event_detect(22, GPIO.BOTH, callback=main_screen.ptt_read)

        # Add the UI elements to the layout:
        layout.add_widget(main_screen)
        Clock.schedule_once(main_screen.ptt_read)
        Clock.schedule_interval(main_screen.update, 0)

        return layout
if __name__ == '__main__':
    temp_1 = Value('d',33)
    speed = Value('d',0)
    fwd    = Value('d',0)
    ref    = Value('d',0)
    drain  = Value('d',0)
    proc_1 = multiprocessing.Process(target = dallas  , args=(1, temp_1, speed)) # dallas temperature sensor
    proc_2 = multiprocessing.Process(target = analog  , args=(1,fwd))    # analog to digital converter
    proc_1.start()    
    proc_2.start()
    MyApp().run()
    
    
    

