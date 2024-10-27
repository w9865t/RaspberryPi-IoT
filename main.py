import RPi.GPIO as GPIO
import smbus
import lirc
import time
import multiprocessing

# 7seg setup
GPIO.setmode(GPIO.BCM)
DECODER_7SEG = {'D0':4, 'D1':26, 'D2':6, 'D3':20}
DIGIT_7SEG = {1:22, 2:27, 3:5, 4:21}

# turn off all 7seg
GPIO.setup(list(DIGIT_7SEG.values()), GPIO.OUT, initial=1)

# SW setup
SW_master = 16
SW_AC = 25
SW_LT = 24
SW_TV = 23

GPIO.setup(SW_master, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(SW_AC, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(SW_LT, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(SW_TV, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# set SW events
stat_SW_master = 0
def check_SW_master(pin):
    global stat_SW_master
    if (stat_SW_master == 0):
        print('master OFF Pressed. wait for 8 sec...')
        stat_SW_master = 1
        main_process.ctrl_IR('AC', 'OFF')
        main_process.ctrl_IR('LT', 'OFF')
        main_process.ctrl_IR('TV', 'OFF')
    else:
        print('master ON Pressed. wait for 8 sec...')
        stat_SW_master = 0
        main_process.ctrl_IR('AC', 'ON')
        main_process.ctrl_IR('LT', 'ON')
        main_process.ctrl_IR('TV', 'ON')

stat_SW_AC = 0
def check_SW_AC(pin):
    global stat_SW_AC
    if (stat_SW_AC == 0):
        print('AC OFF Pressed')
        main_process.ctrl_IR('AC', 'OFF')
        stat_SW_AC = 1
    else:
        print('AC ON Pressed')
        main_process.ctrl_IR('AC', 'ON')
        stat_SW_AC = 0        

stat_SW_LT = 0
def check_SW_LT(pin):
    global stat_SW_LT
    if (stat_SW_LT == 0):
        print('LT OFF Pressed')
        main_process.ctrl_IR('LT', 'OFF')
        stat_SW_LT = 1
    else:
        print('LT ON Pressed')
        main_process.ctrl_IR('LT', 'ON')
        stat_SW_LT = 0

stat_SW_TV = 0
def check_SW_TV(pin):
    global stat_SW_TV
    if (stat_SW_TV == 0):
        print('TV OFF Pressed. wait for 8 sec...')
        stat_SW_TV = 1
        main_process.ctrl_IR('TV', 'OFF')
        
    else:
        print('TV ON Pressed. wait for 8 sec...')
        stat_SW_TV = 0
        main_process.ctrl_IR('TV', 'ON')

GPIO.add_event_detect(SW_master, GPIO.FALLING, callback=check_SW_master, bouncetime=8000)
GPIO.add_event_detect(SW_AC, GPIO.FALLING, callback=check_SW_AC, bouncetime=500)
GPIO.add_event_detect(SW_LT, GPIO.FALLING, callback=check_SW_LT, bouncetime=500)
GPIO.add_event_detect(SW_TV, GPIO.FALLING, callback=check_SW_TV, bouncetime=8000)

# IR controler setup
ircon = lirc.CommandConnection(socket_path='/var/run/lirc/lircd')

# temp sensor setup
i2c = smbus.SMBus(1)

i2c_address = 0x48
i2c_config = 0x03

# 16bit mode
i2c.write_byte_data(i2c_address, i2c_config, 0x80)

def read_temperature():
    byte_data = i2c.read_byte_data(i2c_address, 0x00)
    data = byte_data<<8
    byte_data = i2c.read_byte_data(i2c_address, 0x01)
    data = data|byte_data
    return data/128.

# setup end
################################################

# class for system control
class sys_ctrl:
    def __init__(self):
        self.stat_AC = 0
        self.stat_LT = 0
        self.stat_TV = 0

        self.cur_stat_list = multiprocessing.Manager().list()
        self.cur_stat_list.append(1)
        self.cur_stat_list.append(0)
        self.cur_stat_list.append(0)
        self.cur_stat_list.append(0)

        self.seg_process = multiprocessing.Process(target=self.ctrl_7seg)


    # ctrl IR devices
    # device name for target, next status for mod
    def ctrl_IR(self, target, mod):
        if (target == 'AC'):
            if (mod == 'ON'):
                self.stat_AC = 1
                lirc.SendCommand(ircon, remote='COOLER', keys=['KEY_ON']).run()
            if (mod == 'OFF'):
                self.stat_AC = 0
                lirc.SendCommand(ircon, remote='COOLER', keys=['KEY_OFF']).run()

        if (target == 'LT'):
            if (mod == 'ON'):
                self.stat_LT = 1
                lirc.SendCommand(ircon, remote='ROOMLIGHT', keys=['KEY_POWER']).run()
            if (mod == 'OFF'):
                self.stat_LT = 0
                lirc.SendCommand(ircon, remote='ROOMLIGHT', keys=['KEY_POWER']).run()

        if (target == 'TV'):
            if (mod == 'ON'):
                self.stat_TV = 1
                # turn on and change channel
                lirc.SendCommand(ircon, remote='TV', keys=['KEY_POWER']).run()
                time.sleep(3)
                lirc.SendCommand(ircon, remote='TV', keys=['KEY_DIGITL_BROADCAST']).run()
                time.sleep(3)
                lirc.SendCommand(ircon, remote='TV', keys=['KEY_1']).run()

            if (mod == 'OFF'):
                self.stat_TV = 0
                lirc.SendCommand(ircon, remote='TV', keys=['KEY_POWER']).run()

        # after control, refresh status
        self.refresh_stats()


    # refresh current status
    # master, ac, lt, tv
    def refresh_stats(self):
        self.cur_stat_list[1] = self.stat_AC
        self.cur_stat_list[2] = self.stat_LT
        self.cur_stat_list[3] = self.stat_TV

    # control single segment
    def ctrl_single_seg(self, loc, content):
        GPIO.setup(list(DIGIT_7SEG.values()), GPIO.OUT, initial=1)
        GPIO.setup(DIGIT_7SEG[loc], GPIO.OUT, initial=0)

        cur = format(content, 'b').zfill(4) ####
        GPIO.setup(DECODER_7SEG['D3'], GPIO.OUT, initial=int(cur[0]))
        GPIO.setup(DECODER_7SEG['D2'], GPIO.OUT, initial=int(cur[1]))
        GPIO.setup(DECODER_7SEG['D1'], GPIO.OUT, initial=int(cur[2]))
        GPIO.setup(DECODER_7SEG['D0'], GPIO.OUT, initial=int(cur[3]))


    # ctrl 7seg LED
    # if called, call stats to obtain status
    # refresh 7seg LED
    def ctrl_7seg(self):
        while(1):
            self.ctrl_single_seg(1, self.cur_stat_list[0])
            time.sleep(0.005)
            self.ctrl_single_seg(2, self.cur_stat_list[1])
            time.sleep(0.005)
            self.ctrl_single_seg(3, self.cur_stat_list[2])
            time.sleep(0.005)
            self.ctrl_single_seg(4, self.cur_stat_list[3])
            time.sleep(0.005)




    # main
    def ctrl_main(self):
        # multiprocessing 7seg
        self.seg_process.start()
        while(1):
            h = time.localtime().tm_hour
            m = time.localtime().tm_min
            # if time is 8:00 AM, turn on LT and TV
            if (h == 8 and m == 0 and self.stat_LT == 0 and self.stat_TV == 0):
                print('8:00 AM, Turning on LT and TV...')
                self.ctrl_IR('LT', 'ON')
                self.ctrl_IR('TV', 'ON')
            
            # if time is 9:00 AM, turn off LT and TV
            if (h == 9 and m == 0 and self.stat_LT == 1 and self.stat_TV == 1):
                print('9:00 AM, Turning off LT and TV...')
                self.ctrl_IR('LT', 'OFF')
                self.ctrl_IR('TV', 'OFF')
                

            # if temp is over 30 degree celcius, turn on AC
            if (read_temperature() > 30 and self.stat_AC == 0):
                print('Room is hot, Turning on AC...')
                self.ctrl_IR('AC', 'ON')
            
            # if temp is under 26 degree celcius, turn off AC
            if (read_temperature() < 26 and self.stat_AC == 1):
                print('Room is cool enough, Turning off AC...')
                self.ctrl_IR('AC', 'OFF')

            time.sleep(1)

# main
try:
    main_process = sys_ctrl()
    main_process.ctrl_main()

except KeyboardInterrupt:
    pass

# quit
GPIO.remove_event_detect(SW_master)
GPIO.remove_event_detect(SW_AC)
GPIO.remove_event_detect(SW_LT)
GPIO.remove_event_detect(SW_TV)
main_process.seg_process.kill()
time.sleep(1)
GPIO.cleanup()