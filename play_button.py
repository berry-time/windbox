#!/usr/bin/env python3

import glob
import gpiozero
import logging
import os
from pygame import mixer
import time
from typing import List

min_debouncing_time_sec = 0.5  # button may have a "bouncing" effect of multiple presses


class PlaybackState():
    ''' Helper class/object to check, get, set and unset an active playlist by an ID. '''
    def __init__(self):
        self.active_id: int = -1
        self.lock_id: int = -1
    # methods for handling active playback state
    def is_active(self) -> bool:
        return self.active_id >= 0
    def get_active_id(self) -> int:
        return self.active_id
    def set_active_id(self, index: int) -> None:
        self.active_id = index
    def unset_active_id(self) -> None:
        self.active_id = -1
    # methods for handling the lock
    def is_lock_set(self) -> bool:
        return self.lock_id >= 0
    def set_lock(self, id=0) -> None:
        self.lock_id = id
    def release_lock(self) -> None:
        self.lock_id = -1


class PlayButton():
    ''' The PlayButton class manages the playback of the playlist associated to one GPIO button.
        The playback list is obtained from all suitable files in a folder.
        param id:             ID to associate this button to an active playlist. Shall be unique for each button.
        param pin:            Button GPIO connection. All pins are GPIO numbers, not physical numbers!
        param folder:         Folder containing audio files associated to this button/playlist.
        param autoplay:       When set to True, will continue playing all files of this playlist when button is pressed.
        param playback_state: Reference to playback state object to get, set or unset the active playlist.
        logger:               Logger object to write info/warnings/errors to.
        min_playtime_sec:     Minimum playtime (in seconds) before a track can be skipped.
    '''
    def __init__(
            self,
            id: int,
            pin: int,
            folder: str,
            autoplay: bool,
            playback_state: PlaybackState,
            logger: logging.Logger,
            min_playtime_sec: float) -> None:

        self.id = id
        self.autoplay = autoplay
        self.playback_state = playback_state
        self.logger = logger
        self.min_playtime_sec = max(min_playtime_sec, min_debouncing_time_sec)

        # find all matching tracks in folder and store in list
        self.tracks: List[str] = []
        for ext in ["mp3", "ogg"]:
            self.tracks += glob.glob(os.path.join(folder, "*." + ext))
        self.tracks = sorted(self.tracks)  # sort by name, regardless of extension
        self.num_tracks = len(self.tracks)
        self.next_track_idx: int = 0

        self.button = gpiozero.Button(pin=pin)
        self.button.when_pressed = lambda: self.pressed()
        self.logger.info("New PlayButton registered for pin " + str(pin))
        self.logger.info("- Founds tracks:\n  " + "\n  ".join([os.path.basename(t) for t in self.tracks]))


    def pressed(self):
        ''' Action to perform when a play button is pressed:
            1. Stop current playback.
            2. If the list of tracks is not empty, play next track in list.
            3. If autoplay is active and not playing last track of the list, set this list as active playback state.
        '''
        if self.playback_state.is_lock_set():
            return  # some other button is currently actively/recently pressed. Ignore this button press.

        self.playback_state.set_lock(self.id)

        mixer.music.stop()
        if self.num_tracks == 0:
            self.logger.info("Empty playlist selected, clearing active button id.")
            self.playback_state.unset_active_id()
            time.sleep(min_debouncing_time_sec)
        else:

            next_song_path = self.tracks[self.next_track_idx]
            self.logger.info(
                "Next song " +
                "("+ str(self.next_track_idx+1) + "/" + str(self.num_tracks) + "): " +
                os.path.basename(next_song_path))
            mixer.music.load(next_song_path)
            mixer.music.play()
            self.next_track_idx = (self.next_track_idx + 1) % self.num_tracks

            if self.autoplay and self.next_track_idx == 0:
                self.logger.info("Autoplay active for this playlist, but last track reached.")
                self.playback_state.unset_active_id()
            elif self.autoplay:
                self.logger.info("Autoplay active for this playlist: Setting active button id to " + str(self.id))
                self.playback_state.set_active_id(self.id)
            else:
                self.logger.info("Autoplay NOT active for this playlist.")
                self.playback_state.unset_active_id()

            time.sleep(self.min_playtime_sec)

        self.playback_state.release_lock()


class PlayButtons():
    ''' A set of play buttons. 
        Use "add" function to create a new play button, and "get_by_id" to return one by ID.
    '''
    def __init__(self, logger: logging.Logger) -> None:
        self.play_buttons: List[PlayButton] = []
        self.logger = logger
        self.playback_state = PlaybackState()

    def add(self, pin: int, folder: str, autoplay: bool=False, min_playtime_sec: float=10.0):
        self.play_buttons.append(
            PlayButton(
                id=len(self.play_buttons),  # The ID is the position in the play button list
                pin=pin,
                folder=folder,
                autoplay=autoplay,
                playback_state=self.playback_state,
                logger=self.logger,
                min_playtime_sec=min_playtime_sec))

    def get_by_id(self, id: int) -> PlayButton:
        for play_button in self.play_buttons:
            if play_button.id == id:
                return play_button
        error_msg = "Trying to get PlayButton with id " + str(id) + " which is not found."
        self.logger.error(error_msg)
        raise ValueError(error_msg)
