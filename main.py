#!/usr/bin/env python3

######################################################################################
# REQUIRED SETUP OF THE RASPBERRY PI
######################################################################################
# INSTALL THE "GPIOZERO" PACKAGE AND THE "PYGAME" PACKAGE
# sudo apt update && sudo apt install python3-gpiozero python3-pygame

# RUN THE INSTALLER SCRIPT FOR "I2S DAC" AUDIO BOARD
# curl -sS https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/i2samp.sh | bash
#
# SET THE FOLLOWING CRONTAB ENTRIES (RUN crontab -e)
# # windbox start script
# @reboot /usr/bin/python3 /home/pi/zero-fun-net/windbox/windbox.py & > /home/pi/zero-fun-net/windbox/console.log 2>&1
# # turn off LED to reduce power consumption, see https://picockpit.com/raspberry-pi/raspberry-pi-zero-2-battery
# @reboot echo none | sudo tee /sys/class/leds/led0/trigger &
# # disable HDMI to reduce power consumption, see https://picockpit.com/raspberry-pi/raspberry-pi-zero-2-battery
# @reboot /usr/bin/tvservice -o &
#
######################################################################################

import logging
import os
from pygame import mixer
import time

from play_button import PlayButtons

def setup_logger(log_file_path: str, verbose: bool=False) -> logging.Logger:
    ''' Just some customization and beautification of logs to a file.
    '''
    logger = logging.getLogger("Windbox")
    logger.setLevel(logging.DEBUG)
    logging_ch = logging.StreamHandler()
    if not verbose:
        logging_ch.setLevel(logging.WARNING)
    logger.addHandler(logging_ch)
    logging_fh = logging.FileHandler(log_file_path)
    if logging_fh:
        logging_fh.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(logging_fh)
    else:
        logger.error("Could not open logging output file!")
    return logger


def main():
    ''' The main application of the "windbox" music player box.
        It will
        * assign certain PINs to "play button" objects which are fed by folders containing songs (MP3, OGG)
        * create an infinite loop to handle inputs of the created play buttons
        
        For details on the play buttons, see play_button.py, but basically
        * each play button will generate a playlist from the files in the folder provided
        * for each play button, you can decide whether the playlist shall use autoplay
          functionality, i.e. to proceed with the next song after one is finished, or not.
        * if a button is pressed, the current song is skipped (if any is playing) and the next song
          from the playlist associated to the pressed button is played
    '''
    app_base_path = "/home/pi/zero-fun-net/windbox"
    song_path = os.path.join(app_base_path, "songs")
    logger_path = os.path.join(app_base_path, "logger.log")

    logger = setup_logger(logger_path, verbose=False)
    mixer.init()

    # pins 18, 19, 21 are used by adafruit audio board. DO NOT USE!
    play_buttons = PlayButtons(logger)
    play_buttons.add(pin=2,  folder=os.path.join(song_path, "green"))
    play_buttons.add(pin=3,  folder=os.path.join(song_path, "red"))
    play_buttons.add(pin=4,  folder=os.path.join(song_path, "yellow"))
    play_buttons.add(pin=17, folder=os.path.join(song_path, "blue"))
    play_buttons.add(pin=22, folder=os.path.join(song_path, "black"), autoplay=True)
    play_buttons.add(pin=27, folder=os.path.join(song_path, "white"), autoplay=True)
    play_buttons.add(pin=10, folder="/dev/null")  # transparent button, just to stop playing

    while True:
        time.sleep(0.2)  # no need to hurry
        if mixer.music.get_busy():
            # Still playing, nothing to do.
            continue
        if play_buttons.playback_state.is_active():
            # Finished playing, but we have an active playback of a playlist. Play next song.
            logger.info("Autoplay active for this button, playing next track.")
            play_buttons.get_by_id(play_buttons.playback_state.get_active_id()).pressed()


if __name__ == '__main__':
    main()
