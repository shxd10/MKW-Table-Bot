'''
Created on Oct 21, 2021

@author: willg

This module helps track and store data from Wiimmfi.

'''
import common
from collections import defaultdict
from datetime import datetime, timedelta
import Placement
import Race
import Player
from typing import List, Dict, Tuple, Set
import UtilityFunctions
from copy import deepcopy, copy
import traceback
from itertools import chain
from numpy import place
#import itertools
#from contextlib import closing

"""SELECT
    Race.track_name,
    COUNT(Race.race_id) as times_played
FROM
    Race LEFT JOIN Track ON Race.track_name = Track.track_name
WHERE
    Track.is_ct == 1
GROUP BY
    Race.track_name
ORDER BY
    2 DESC, 1 ASC;"""
import os
from data_tracking import Data_Tracker_SQL_Query_Builder as QB

DEBUGGING_DATA_TRACKER = False
DEBUGGING_SQL = True

import sqlite3
database_connection:sqlite3.Connection = None

class SQLDataBad(Exception):
    pass
class SQLTypeWrong(SQLDataBad):
    pass
class SQLFormatWrong(SQLDataBad):
    pass

#dict of channel IDs to tier numbers

RT_NAME = "rt"
CT_NAME = "ct"
RXX_LOCKER_NAME = "rxx_locker"
RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS = {
    843981870751678484:8,
    836652527432499260:7,
    747290199242965062:6,
    747290182096650332:5,
    873721400056238160:5,
    747290167391551509:4,
    801620685826818078:4,
    747290151016857622:3,
    801620818965954580:3,
    805860420224942080:3,
    747290132675166330:2,
    754104414335139940:2,
    801630085823725568:2,
    747289647003992078:1,
    747544598968270868:1,
    781249043623182406:1
    }

CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS = {
    875532532383363072:7,
    850520560424714240:6,
    801625226064166922:5,
    747290436275535913:4,
    879429019546812466:4,
    747290415404810250:3,
    747290383297282156:2,
    823014979279519774:2,
    747290363433320539:1,
    871442059599429632:1
    }

RT_REVERSE_TIER_MAPPINGS = defaultdict(set)
CT_REVERSE_TIER_MAPPINGS = defaultdict(set)

for k,v in RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS.items():
    RT_REVERSE_TIER_MAPPINGS[v].add(k)
for k,v in CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS.items():
    CT_REVERSE_TIER_MAPPINGS[v].add(k)
    
TABLE_BOT_CHANNEL_TIER_MAPPINGS = {RT_NAME:RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS, CT_NAME:CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS}

room_data = {RT_NAME:{},
             CT_NAME:{},
             RXX_LOCKER_NAME:{}
             }
ALREADY_ADDED_ERROR = 11
FATAL_ERROR = 12
RACE_ADD_SUCCESS = 10
DATA_DUMP_SUCCESS = 9
#Need rxx -> [channel_id:channel_data:default_dict, room_data]


def get_start_time(channel_data):
    return channel_data[1]
def get_last_updated(channel_data):
    return channel_data[2]
def get_room_update_count(channel_data):
    return channel_data[3]
def get_tier(channel_data):
    return channel_data[4]

def tier_matches(tier, channel_data):
    if tier is None:
        return True
    return tier == get_tier(channel_data)
"""
class DataRetriever(object):
    #TODO: Finish method
    @staticmethod
    def choose_best_event_data(channel_id_events:Dict[int, List], prefer_tier=False, require_private_room=True) -> Tuple[List, Event]:
        '''Takes a dictionary with channel ids mapping to event data and returns the channel data and event that is most likely to be legitimate and accurate'''
        LEIGITMATE_ROOM_UPDATE_COUNT = 3
        cur_best = None
        #Filter by private rooms only if required
        filtered_events = filter(channel_id_events.values(), lambda event_data: (not require_private_room or all(race.roomType == Race.PRIVATE_ROOM_REGION for race in event_data[1].races)))
        for channel_data, event in filtered_events:
            if prefer_tier and get_tier(channel_data) is None:
                continue
            if get_room_update_count(channel_data) < LEIGITMATE_ROOM_UPDATE_COUNT:
                continue
            if cur_best is None:
                cur_best = (channel_data, event)
                continue
        
        #choose best out of the ones that didn't have a tier
            
            
        return cur_best
            
    
    @staticmethod
    def get_filtered_events(rxx_dict, tier=None, in_last_days=None):
        time_cutoff = (datetime.now() - timedelta(days=in_last_days)) if in_last_days else datetime.min
        results = []
        for rxx in rxx_dict:
            best_data = DataRetriever.choose_best_event_data(rxx_dict[rxx], prefer_tier=(tier is None))
            if best_data is None:
                continue
            channel_data, event = best_data
            if tier_matches(tier, channel_data) and time_cutoff < get_start_time(channel_data):
                results.append(event)
        return results
    @staticmethod
    def get_popular_characters(is_ct=False, tier=None, in_last_days=None, starting_position=None):
        pass
    
    @staticmethod
    def get_popular_tracks(is_ct=False, tier=None, in_last_days=None):
        track_count = defaultdict(int)
        rxx_dict = room_data[CT_NAME] if is_ct else room_data[RT_NAME]
        filtered_rxxs = DataRetriever.get_filtered_rxxs(rxx_dict, tier, in_last_days)
"""
class ChannelBotSQLDataValidator(object):
    def wrong_type_message(self, data, expected_type, multi=False):
        if multi:
            return f"{data} of type {type(data)} is not any of the expected types: ({', '.join([(t.__name__ if t is not None else 'None') for t in expected_type])})"
        else:
            return f"{data} of type {type(data)} is not expected type: {expected_type.__name__}"
    
    def validate_type(self, data, expected_type, can_be_none):
        if can_be_none:
            if not isinstance(data, (expected_type, type(None))):
                raise SQLTypeWrong(self.wrong_type_message(data, (expected_type, None), multi=True))
        else:
            if not isinstance(data, expected_type):
                raise SQLTypeWrong(self.wrong_type_message(data, expected_type))
    
    def validate_int(self, data, can_be_none=False):
        self.validate_type(data, int, can_be_none)
        
    def validate_str(self, data, can_be_none=False):
        self.validate_type(data, str, can_be_none)
    
    def validate_float(self, data, can_be_none=False):
        self.validate_type(data, float, can_be_none)
    
    def validate_bool(self, data, can_be_none=False):
        self.validate_type(data, bool, can_be_none)
        
    def is_from_wiimmfi_validation(self, is_from_wiimmfi):
        self.validate_bool(is_from_wiimmfi)
        
    def event_id_validation(self, event_id):
        self.validate_int(event_id)
        if event_id < 1:
            raise SQLFormatWrong(f"{event_id} is not a formatted like an event id, which should be a number")
    
    def channel_id_validation(self, channel_id):
        self.validate_int(channel_id)
        if channel_id < 1:
            raise SQLFormatWrong(f"{channel_id} is not a formatted like an channel id, which should be a number")
    
    def discord_id_validation(self, discord_id):
        self.validate_int(discord_id)
        if discord_id < 1:
            raise SQLFormatWrong(f"{discord_id} is not a formatted like a discord id, which should be a number")
        
    def placement_time_validation(self, time_str):
        self.validate_str(time_str)
        if not Placement.is_valid_time_str(time_str):
            raise SQLFormatWrong(f"{time_str} is not formatted like a valid finishing time")
        
    def placement_delta_validation(self, delta):
        self.validate_float(delta, can_be_none=True)
        
    def player_ol_status_validation(self, ol_status):
        self.validate_str(ol_status, can_be_none=True)
        
    def player_position_validation(self, player_pos):
        self.validate_int(player_pos)
        if player_pos < 1 and player_pos != -1:
            raise SQLFormatWrong(f"{player_pos} is not a valid player position")
        
    def player_finish_place_validation(self, place):
        self.validate_int(place)
        if place < 1:
            raise SQLFormatWrong(f"{place} is not a valid finishing place")
    
    def fc_validation(self, fc):
        self.validate_str(fc)
        if not UtilityFunctions.is_fc(fc):
            raise SQLFormatWrong(f"{fc} is not a formatted like an FC")
    
    def race_id_validation(self, race_id):
        self.validate_str(race_id)
        if not UtilityFunctions.is_race_ID(race_id):
            raise SQLFormatWrong(f"{race_id} is not a formatted like a race ID")
        
    def mii_hex_validation(self, mii_hex):
        self.validate_str(mii_hex, can_be_none=True)
        if isinstance(mii_hex, str):
            if not UtilityFunctions.is_hex(mii_hex):
                raise SQLFormatWrong(f"{mii_hex} is not a valid mii hex")
            
    def player_id_validation(self, player_id):
        self.validate_int(player_id)
        
    def player_mkwx_url_validation(self, mkwx_url):
        self.validate_str(mkwx_url)
    
    def validate_player_data(self, players:List[Player.Player]):
        '''Validates that all the data in players is the correct type and format before going into the database'''
        for player in players:
            self.fc_validation(player.get_FC())
            self.player_id_validation(player.get_player_id())
            self.player_mkwx_url_validation(player.get_mkwx_url())
            
    def track_name_validation(self, track_name, rxx=None):
        self.validate_str(track_name)
        if track_name == "None":
            raise SQLDataBad(f"track_name cannot be an 'None', room rxx: {rxx}")
    
    def track_url_validation(self, track_url):
        self.validate_str(track_url, can_be_none=True)
        
    def track_name_no_author_validation(self, track_name_author_stripped, rxx=None):
        self.validate_str(track_name_author_stripped)
        if track_name_author_stripped == "None":
            raise SQLDataBad(f"track_name without author cannot be an 'None', room rxx: {rxx}")
        
    def track_lookup_name_validation(self, track_lookup_name, rxx=None):
        self.validate_str(track_lookup_name)
        if track_lookup_name == "None" or ' ' in track_lookup_name:
            raise SQLDataBad(f"{track_lookup_name} is not a valid track lookup name, room rxx: {rxx}")
        
    def track_is_ct_validation(self, is_ct):
        self.validate_bool(is_ct)
        
    def validate_tracks_data(self, races:List[Race.Race]):
        '''Validates that all the relevant data (regarding track information) in races is the correct type and format before going into the database'''
        for race in races:
            race:Race.Race
            self.track_name_validation(race.get_track_name(), rxx=race.rxx)
            self.track_url_validation(race.get_track_url())
            no_author_name = race.getTrackNameWithoutAuthor()
            self.track_name_no_author_validation(no_author_name, rxx=race.rxx)
            self.track_is_ct_validation(race.is_custom_track())
            self.track_lookup_name_validation(Race.get_track_name_lookup(no_author_name), rxx=race.rxx)   
    
    def rxx_validation(self, rxx):
        self.validate_str(rxx)
        if not UtilityFunctions.is_rLID(rxx):
            raise SQLFormatWrong(f"{rxx} is not a formatted like an rxx")
        
    def wiimmfi_utc_time_validation(self, wiimmfi_time):
        self.validate_str(wiimmfi_time)
        if not UtilityFunctions.is_wiimmfi_utc_time(wiimmfi_time):
            raise SQLFormatWrong(f"{wiimmfi_time} is not a formatted like the expected Wiimmfi time")
        
    def race_number_validation(self, race_number):
        self.validate_int(race_number)
        if race_number < 1:
            raise SQLDataBad(f"{race_number} race number must be greater than 0")
        
    def race_room_name_validation(self, room_name):
        self.validate_str(room_name)
    
    def race_room_type_validation(self, room_type):
        self.validate_str(room_type)
    
    def race_cc_validation(self, cc):
        self.validate_str(cc)
        
    def region_validation(self, region):
        self.validate_str(region)
        if not Race.is_valid_region(region):
            raise SQLFormatWrong(f"{region} region is not a valid region (see Race.is_valid_region)")
    
    def connection_fails_validation(self, conn_fails):
        self.validate_float(conn_fails, can_be_none=True)
        
    def player_role_validation(self, player_role):
        self.validate_str(player_role)
        
    def player_vr_validation(self, vr):
        self.validate_int(vr, can_be_none=True)
        if isinstance(vr, int):
            if vr < 0:
                raise SQLFormatWrong(f"{vr} VR cannot be less than 0")
    
    def player_character_validation(self, character):
        self.validate_str(character, can_be_none=True)
        if isinstance(character, str):
            if character.strip() == "":
                raise SQLFormatWrong(f"{character} character for player cannot be an empty string")
    
    def player_vehicle_validation(self, vehicle):
        self.validate_str(vehicle, can_be_none=True)
        if isinstance(vehicle, str):
            if vehicle.strip() == "":
                raise SQLFormatWrong(f"{vehicle} vehicle for player cannot be an empty string")
            
    def name_validation(self, name):
        self.validate_str(name, can_be_none=True)
        if isinstance(name, str):
            if name.strip() == "":
                raise SQLFormatWrong(f"{name} name player cannot be an empty string")
        
    def validate_races_data(self, races:List[Race.Race]):
        '''Validates that all the data in races is the correct type and format before going into the database'''
        for race in races:
            race:Race.Race
            self.race_id_validation(race.get_race_id())
            self.rxx_validation(race.get_rxx())
            self.wiimmfi_utc_time_validation(race.get_match_start_time())
            self.race_number_validation(race.get_race_number())
            self.race_room_name_validation(race.get_room_name())
            self.race_room_type_validation(race.get_room_type())
            self.race_cc_validation(race.get_cc())
            self.region_validation(race.get_region())            
            self.is_from_wiimmfi_validation(race.is_from_wiimmfi())
            
        self.validate_tracks_data(races)
            
    def validate_placement_data(self, placements:Dict[Tuple,Placement.Placement]):
        for (race_id, fc), placement in placements.items():
            self.race_id_validation(race_id)
            self.fc_validation(fc)
            player = placement.getPlayer()
            self.fc_validation(player.get_FC())
            self.player_finish_place_validation(placement.get_place())
            self.placement_time_validation(placement.get_time_string())
            self.placement_delta_validation(placement.get_delta())
            self.player_ol_status_validation(player.get_ol_status())
            self.player_position_validation(player.get_position())
            self.region_validation(player.get_region())
            self.connection_fails_validation(player.get_connection_fails())
            self.player_role_validation(player.get_role())
            self.player_vr_validation(player.get_VR())
            self.player_character_validation(player.get_character())
            self.player_vehicle_validation(player.get_vehicle())
            self.name_validation(player.get_discord_name())
            self.name_validation(player.get_lounge_name())
            self.mii_hex_validation(player.get_mii_hex())
            self.is_from_wiimmfi_validation(placement.is_from_wiimmfi())
                
            
        
    
    def validate_event_id_race_ids(self, event_id_race_ids:Set[Tuple]):
        for event_id, race_id in event_id_race_ids:
            self.event_id_validation(event_id)
            self.race_id_validation(race_id)
            
    def validate_mii_hex_update(self, race_id_fc_placements:Dict[Tuple, Placement.Placement]):
        for (race_id, fc), placement in race_id_fc_placements.items():
            self.race_id_validation(race_id)
            self.fc_validation(fc)
            self.mii_hex_validation(placement.getPlayer().get_mii_hex())
            
    def validate_event_data(self, channel_bot):
        self.event_id_validation(channel_bot.get_event_id())
        self.channel_id_validation(channel_bot.get_channel_id())
        self.discord_id_validation(channel_bot.getRoom().get_set_up_user_discord_id())
        if not isinstance(channel_bot.getRoom().get_known_region(), str):
            raise SQLTypeWrong(self.wrong_type_message(channel_bot.getRoom().get_known_region(), str))
        if not isinstance(channel_bot.getRoom().get_set_up_display_name(), str):
            raise SQLTypeWrong(self.wrong_type_message(channel_bot.getRoom().get_set_up_display_name(), str))
            
            

            

class RoomTrackerSQL(object):
    def __init__(self, channel_bot):
        self.channel_bot = channel_bot
        self.data_validator = ChannelBotSQLDataValidator()
            
    
    def get_race_as_sql_tuple(self, race:Race.Race):
        '''Converts a given table bot race into a tuple that is ready to be inserted into the Race SQL table'''
        return (race.get_race_id(),
                race.get_rxx(),
                common.get_utc_time(),
                UtilityFunctions.get_wiimmfi_utc_time(race.get_match_start_time()),
                race.get_race_number(),
                race.get_room_name(),
                race.get_track_name(),
                race.get_room_type(),
                race.get_cc(),
                race.get_region(),
                race.is_from_wiimmfi())
    
    def get_race_as_sql_track_tuple(self, race):
        '''Converts a given table bot race into a tuple that is ready to be inserted into the Track SQL table'''
        no_author_name = race.getTrackNameWithoutAuthor()
        return (race.get_track_name(),
                race.get_track_url(),
                no_author_name,
                race.is_custom_track(),
                Race.get_track_name_lookup(no_author_name)
                )
    
    def get_player_as_sql_player_tuple(self, player):
        '''Converts a given table bot player into a tuple that is ready to be inserted into the Player SQL table'''
        return (player.get_FC(),
                int(player.get_player_id()),
                player.get_mkwx_url())
        
    def get_placement_as_sql_place_tuple(self, race_id, placement:Placement.Placement):
        '''Converts a given table bot Placement into a tuple that is ready to be inserted into the Place SQL table'''
        player:Placement.Player.Player = placement.getPlayer()
        return (race_id,
                player.get_FC(),
                player.get_name(),
                placement.get_place(),
                placement.get_time_string(),
                placement.get_delta(),
                player.get_ol_status(),
                player.get_position(),
                player.get_region(),
                player.get_connection_fails(),
                player.get_role(),
                player.get_VR(),
                player.get_character(),
                player.get_vehicle(),
                player.get_discord_name(),
                player.get_lounge_name(),
                player.get_mii_hex(),
                placement.is_from_wiimmfi())
    
    
        
    def insert_missing_placements_into_database(self):
        '''Inserts placements in self.channel_bot's races are not yet in the database's Place table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns a list of the inserted placements (as 2-tuples: race_id, fc) upon success. (An empty list is returned if no placements were inserted.)'''
        
        race_id_fc_placements = {(race.get_race_id(), placement.getPlayer().get_FC()):placement for race in self.channel_bot.getRoom().races for placement in race.getPlacements()}
        if len(race_id_fc_placements) == 0:
            return []
        
        self.data_validator.validate_placement_data(race_id_fc_placements)
        all_data = [self.get_placement_as_sql_place_tuple(race_id, p) for (race_id, _), p in race_id_fc_placements.items()]
        insert_ignore_script = QB.build_insert_missing_placement_script(all_data)
        values_args = list(chain.from_iterable(all_data))
        
        with database_connection:
            return list(database_connection.execute(insert_ignore_script, values_args))
        return []
    
    
    def insert_missing_players_into_database(self):
        '''Inserts players in all of the races in self.channel_bot.races that are not yet in the database's Player table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns a list of the inserted player's fcs (as 1-tuples) upon success. (An empty list is returned if no players were inserted.)'''
        unique_room_players = [placement.getPlayer() for placement in self.channel_bot.getRoom().getFCPlacements().values()]
        if len(unique_room_players) == 0:
            return []
        
        self.data_validator.validate_player_data(unique_room_players)
            
        all_data = [self.get_player_as_sql_player_tuple(p) for p in unique_room_players]
        insert_ignore_script = QB.build_insert_missing_players_script(all_data)
        values_args = list(chain.from_iterable(all_data))
        with database_connection:
            return list(database_connection.execute(insert_ignore_script, values_args))
        return []
    
    
    def insert_missing_races_into_database(self):
        '''Inserts races in self.channel_bot.races are not yet in the database's Race table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns a list of the inserted race's race_id's (as 1-tuples) upon success. (An empty list is returned if no races were inserted.)'''
        unique_races = {race.get_race_id():race for race in self.channel_bot.getRoom().races}.values()
        if len(unique_races) == 0:
            return []
        
        self.data_validator.validate_races_data(unique_races)
        all_data = [self.get_race_as_sql_tuple(r) for r in unique_races]
        insert_ignore_script = QB.build_insert_missing_races_script(all_data)
        values_args = list(chain.from_iterable(all_data))
        with database_connection:
            return list(database_connection.execute(insert_ignore_script, values_args))
        return []

    
    
    def insert_missing_tracks_into_database(self):
        '''Inserts tracks in self.channel_bot's races are not yet in the database's Track table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns the a list of the inserted track names (as 1-tuples) upon success. (An empty list is returned if no tracks were inserted.)'''
        races_unique_track_names = {race.get_track_name():race for race in self.channel_bot.getRoom().races}.values()
        if len(races_unique_track_names) == 0:
            return []
        
        self.data_validator.validate_tracks_data(races_unique_track_names)
        all_data = [self.get_race_as_sql_track_tuple(r) for r in races_unique_track_names]
        insert_ignore_script = QB.build_insert_missing_tracks_script(all_data)
        values_args = list(chain.from_iterable(all_data))
        
        with database_connection:
            return list(database_connection.execute(insert_ignore_script, values_args))
        return []
        
        
    
    def get_matching_placements_with_missing_hex(self, update_mii_args):
        '''Given a list of 3-tuples (where the tuple is (race_id, fc, _)), returns existing a list of (race_id, fcs) tuples in Place table whose mii_hex is null.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong'''
        missing_mii_data = [(data[0], data[1], None) for data in update_mii_args]
        if len(missing_mii_data) == 0:
            return []
        missing_mii_hexes_statement = QB.get_existing_race_fcs_in_Place_table_with_null_mii_hex(missing_mii_data)
        values_args = list(chain.from_iterable(missing_mii_data))
        with database_connection:
            return list(database_connection.execute(missing_mii_hexes_statement, values_args))
        return []
        
    def update_database_place_miis(self):
        '''Updates the mii_hex for placements in Place table for placements in self.channel_bot.race's placements who have a mii_hex if that mii_hex in the Place table is null.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns the a list of the race_id, fc (as 2-tuples) of the placements whose mii_hex's were updated. (An empty list is returned if nothing was updated.)'''
        have_miis_for_placements = {(race.get_race_id(), placement.getPlayer().get_FC()):placement for race in self.channel_bot.getRoom().races for placement in race.getPlacements() if placement.getPlayer().get_mii_hex() is not None}
        if len(have_miis_for_placements) == 0:
            return []
        
        self.data_validator.validate_mii_hex_update(have_miis_for_placements)
        
        update_mii_script = QB.update_mii_hex_script()
        update_mii_args = [(race_id, fc, placement.getPlayer().get_mii_hex()) for (race_id, fc), placement in have_miis_for_placements.items()]
        
        found_race_id_fcs_with_null_miis = self.get_matching_placements_with_missing_hex(update_mii_args)
        with database_connection:
            database_connection.executemany(update_mii_script, update_mii_args)
        return found_race_id_fcs_with_null_miis
    
    
    def insert_missing_event_ids_race_ids(self):
        '''Inserts (event_id, race_id) in for each race in self.channel_bot's races that are not yet in the database's Event_Races table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns the a list of the inserted event_ids, race_ids (as 2-tuples) upon success. (An empty list is returned if nothing was inserted.)'''
        event_id_race_ids = {(self.channel_bot.get_event_id(), race.get_race_id()) for race in self.channel_bot.getRoom().races} #Note this is a set of tuples, not a dict
        if len(event_id_race_ids) < 1:
            return []
        self.data_validator.validate_event_id_race_ids(event_id_race_ids)
        
        insert_ignore_script = QB.build_missing_event_ids_race_ids_script(event_id_race_ids)
        values_args = list(chain.from_iterable((event_id, race_id) for event_id, race_id in event_id_race_ids))
        with database_connection:
            return list(database_connection.execute(insert_ignore_script, values_args))
        return []
    
    def get_event_as_upsert_sql_place_tuple(self, channel_bot):
        '''Converts a given table bot a tuple that is ready to be inserted into the Event SQL table'''
        return (channel_bot.get_event_id(),
                channel_bot.get_channel_id(),
                common.get_utc_time(),
                common.get_utc_time(),
                0,
                channel_bot.getRoom().get_known_region(),
                channel_bot.getRoom().get_set_up_user_discord_id(),
                channel_bot.getRoom().get_set_up_display_name())
        
    def insert_missing_event(self, was_real_update=False):
        self.data_validator.validate_event_data(self.channel_bot)
        event_sql_args = [*self.get_event_as_upsert_sql_place_tuple(self.channel_bot)]
        if len(event_sql_args) < 1:
            return []
        
        upsert_script = QB.build_event_upsert_script(was_real_update)
        with database_connection:
            added_updated_event_ids = list(database_connection.execute(upsert_script, event_sql_args))
            if was_real_update:
                return added_updated_event_ids
        return []
    
    
    def add_event_id(self):
        '''Inserts event_id for self.channel_bot int Event_ID table.
        May raise SQLDataBad, SQLTypeWrong, SQLFormatWrong
        Returns a list of the inserted event_id (as a 1-tuple) upon success. (An empty list is returned if nothing was inserted.)'''
        self.data_validator.event_id_validation(self.channel_bot.get_event_id())
        event_sql_args = [(self.channel_bot.get_event_id(),)]
        if len(event_sql_args) < 1:
            return []
        
        upsert_script = QB.build_missing_event_id_table_script(event_sql_args)
        #print(upsert_script)
        with database_connection:
            return list(database_connection.execute(upsert_script, event_sql_args[0]))
        return []
    
    
class RoomTracker(object):
    
    @staticmethod
    def new_channel_data(channel_id):
        lounge_tier = None
        if channel_id in RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS:
            lounge_tier = RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS[channel_id]
        if channel_id in CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS:
            lounge_tier = CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS[channel_id]
        #channelid, first command time, last command time, total room updates sent, tier
        return [channel_id, datetime.now(), datetime.now(), 0, lounge_tier]
    
    @staticmethod
    def check_create_channel_data(rxx, rxx_dict, channel_bot):
        if rxx not in rxx_dict:
            rxx_dict[rxx] = {}
        if channel_bot.channel_id not in rxx_dict[rxx]:
            rxx_dict[rxx][channel_bot.channel_id] = [RoomTracker.new_channel_data(channel_bot.channel_id), RoomTracker.create_event(channel_bot)]
            return False
        return True
    """
    @staticmethod
    def create_placement(placement:Race.Placement):
        player = placement.getPlayer()
        return Place(fc=player.get_FC(),
                     name=player.get_name(),
                     place=placement.get_place(),
                     time=placement.get_time(),
                     lagStart=placement.get_delta(),
                     playerURL=player.get_mkwx_url(),
                     pid=player.get_player_id(),
                     ol_status=player.get_ol_status(),
                     roomPosition=player.get_position(),
                     roomType=player.get_region(),
                     connectionFails=player.get_connection_fails(),
                     role=player.get_role(),
                     vr=player.get_VR(),
                     character=player.get_character(),
                     vehicle=player.get_vehicle(),
                     discord_name=player.get_discord_name(),
                     lounge_name=player.get_lounge_name(),
                     mii_hex=player.get_mii_hex())
    
    @staticmethod
    def create_race(channel_data_info, race:Race.Race) -> Race:
        channel_id = channel_data_info[0][0]
        tier = get_tier(channel_data_info[0])
        all_placements = [RoomTracker.create_placement(p) for p in race.getPlacements()]
        return Race(timeAdded=datetime.now(),
                    channel_id=channel_id,
                    tier=tier,
                    matchTime=race.get_match_start_time(),
                    id=race.get_race_id(),
                    raceNumber=race.get_race_number(),
                    roomID=race.get_room_name(),
                    rxx=race.get_rxx(),
                    trackURL=race.get_track_url(),
                    roomType=race.get_room_type(),
                    trackName=race.get_track_name(),
                    trackNameFixed=Race.remove_author_and_version_from_name(race.get_track_name()),
                    cc=race.get_cc(),
                    region=race.get_region(),
                    is_ct=race.is_custom_track(),
                    placements=all_placements)
    """
    @staticmethod
    def get_miis(channel_bot) -> Dict[str, str]:
        #[print(mii) for mii in channel_bot.get_miis()]
        return {FC : mii.mii_data_hex_str for (FC,mii) in channel_bot.get_miis().items()}
    """    
    @staticmethod
    def create_event(channel_bot) -> Event:
        return Event(timeAdded=datetime.now(),
                     allFCs=set(channel_bot.getRoom().getFCs()),
                     races=[],
                     room_type=channel_bot.getRoom().get_room_type(),
                     name_changes=copy(channel_bot.getRoom().name_changes),
                     removed_races=copy(channel_bot.getRoom().removed_races),
                     placement_history=copy(channel_bot.getRoom().placement_history),
                     forcedRoomSize=copy(channel_bot.getRoom().forcedRoomSize),
                     playerPenalties=copy(channel_bot.getRoom().playerPenalties),
                     dc_on_or_before=copy(channel_bot.getRoom().dc_on_or_before),
                     sub_ins=deepcopy(channel_bot.getRoom().sub_ins),
                     set_up_user_discord_id=channel_bot.getRoom().set_up_user,
                     set_up_user_display_name=channel_bot.getRoom().set_up_user_display_name,
                     playersPerTeam=channel_bot.getWar().playersPerTeam,
                     numberOfTeams=channel_bot.getWar().numberOfTeams,
                     defaultRoomSize=channel_bot.getWar().get_num_players(),
                     numberOfGPs=channel_bot.getWar().numberOfGPs,
                     eventName=channel_bot.getWar().warName,
                     missingRacePts=channel_bot.getWar().missingRacePts,
                     manualEdits=copy(channel_bot.getWar().manualEdits),
                     ignoreLargeTimes=channel_bot.getWar().ignoreLargeTimes,
                     teamPenalties=copy(channel_bot.getWar().teamPenalties),
                     teams=copy(channel_bot.getWar().teams),
                     miis=RoomTracker.get_miis(channel_bot))
    @staticmethod
    def update_event_data(channel_bot, channel_data_info):
        channel_data_info[1].allFCs.update(channel_bot.getRoom().getFCs())
        channel_data_info[1].miis.update(RoomTracker.get_miis(channel_bot))
        channel_data_info[1] = Event(timeAdded=channel_data_info[1].timeAdded,
                                     allFCs=channel_data_info[1].allFCs,
                                     races=channel_data_info[1].races,
                                     room_type=channel_bot.getRoom().get_room_type(),
                                     name_changes=copy(channel_bot.getRoom().name_changes),
                                     removed_races=copy(channel_bot.getRoom().removed_races),
                                     placement_history=copy(channel_bot.getRoom().placement_history),
                                     forcedRoomSize=copy(channel_bot.getRoom().forcedRoomSize),
                                     playerPenalties=copy(channel_bot.getRoom().playerPenalties),
                                     dc_on_or_before=copy(channel_bot.getRoom().dc_on_or_before),
                                     sub_ins=deepcopy(channel_bot.getRoom().sub_ins),
                                     set_up_user_discord_id=channel_bot.getRoom().set_up_user,
                                     set_up_user_display_name=channel_bot.getRoom().set_up_user_display_name,
                                     playersPerTeam=channel_bot.getWar().playersPerTeam,
                                     numberOfTeams=channel_bot.getWar().numberOfTeams,
                                     defaultRoomSize=channel_bot.getWar().get_num_players(),
                                     numberOfGPs=channel_bot.getWar().numberOfGPs,
                                     eventName=channel_bot.getWar().warName,
                                     missingRacePts=channel_bot.getWar().missingRacePts,
                                     manualEdits=copy(channel_bot.getWar().manualEdits),
                                     ignoreLargeTimes=channel_bot.getWar().ignoreLargeTimes,
                                     teamPenalties=copy(channel_bot.getWar().teamPenalties),
                                     teams=copy(channel_bot.getWar().teams),
                                     miis=channel_data_info[1].miis)
    """
    @staticmethod
    def add_race(channel_data_info, race:Race.Race):
        _, event = channel_data_info
        for r in event.races:
            if r.rxx != race.get_rxx():
                common.log_error(f"rxx's didn't match in add_race:\n{race}\n{r}")
                return FATAL_ERROR
            if r.id == race.raceID:
                return ALREADY_ADDED_ERROR
        #lock_status = obtain_rxx_lock(race.get_rxx())
        #if lock_status != LOCK_OBTAINED: #in use
        #    return
        
        event.races.append(RoomTracker.create_race(channel_data_info, race))
        return RACE_ADD_SUCCESS
        
    
    @staticmethod
    def update_channel_meta_data(channel_bot, channel_data_info):
        channel_meta_data, event = channel_data_info
        roomRaceIDs = set(r.get_race_id() for r in channel_bot.getRoom().getRaces())
        eventRaceIDs = set(r.id for r in event.races)
        if not (len(roomRaceIDs.difference(eventRaceIDs)) == 0 or roomRaceIDs.issubset(eventRaceIDs)): #The room added a race
            channel_meta_data[2] = datetime.now()
            channel_meta_data[3] += 1
        
    @staticmethod
    def add_everything_to_database(channel_bot):
        races:List[Race.Race] = channel_bot.getRoom().getRaces()
        sql_helper = RoomTrackerSQL(channel_bot)
        added_players = sql_helper.insert_missing_players_into_database()
        added_tracks = sql_helper.insert_missing_tracks_into_database()
        added_races = sql_helper.insert_missing_races_into_database()
        added_placements = sql_helper.insert_missing_placements_into_database()
        added_miis = sql_helper.update_database_place_miis()
        added_event_id = sql_helper.add_event_id()
        added_event_ids_race_ids = sql_helper.insert_missing_event_ids_race_ids()
        added_event_ids = sql_helper.insert_missing_event(was_real_update=(len(added_event_ids_race_ids) > 0))

        if DEBUGGING_SQL:
            print(f"Added players: {added_players}")
            print(f"Added tracks: {added_tracks}")
            print(f"Added races: {added_races}")
            print(f"Added placements: {added_placements}")
            print(f"Added miis: {added_miis}")
            print(f"Added event id: {added_event_id}")
            print(f"Added event_id, race_id's: {added_event_ids_race_ids}")
            print(f"Added event ids: {added_event_ids}")
        return
        #sql_helper.
        update_channel_data = True
        update_event_data = True
        for race in races:
            if race.get_rxx() is None or not UtilityFunctions.is_rLID(race.get_rxx()):
                common.log_error(f"No rxx for this race: {race}")
                continue
            rxx_dict = room_data[CT_NAME] if race.is_custom_track() else room_data[RT_NAME]
            update_event_data = RoomTracker.check_create_channel_data(race.get_rxx(), rxx_dict, channel_bot)
            if update_channel_data:
                update_channel_data = False
                RoomTracker.update_channel_meta_data(channel_bot, rxx_dict[race.get_rxx()][channel_bot.channel_id])
            if update_event_data:
                update_event_data = False
                RoomTracker.update_event_data(channel_bot, rxx_dict[race.get_rxx()][channel_bot.channel_id])
            
            success_code = RoomTracker.add_race(rxx_dict[race.get_rxx()][channel_bot.channel_id], race)
            if success_code == FATAL_ERROR:
                return FATAL_ERROR
        return DATA_DUMP_SUCCESS
    
    
    @staticmethod
    def add_data(channel_bot):
        if channel_bot.getRoom().is_initialized():
            #Make a deep copy to avoid asyncio switching current task to a tabler command and modifying our data in the middle of us validating it or adding it
            deepcopied_channel_bot = deepcopy(channel_bot)
            if deepcopied_channel_bot.getRoom().is_initialized(): #This check might seem unnecessary, but we'll leave it in case we convert things to asyncio that aren't currently asynchronous (making it necessary)
                try:
                    success_code = RoomTracker.add_everything_to_database(deepcopied_channel_bot)
                except:
                    common.log_traceback(traceback)
                    raise
                        

def load_room_data():
    if not os.path.exists(common.ROOM_DATA_TRACKING_DATABASE_FILE):
        print("Warning: No database for room tracking found, so creating a new one. If you should have had a database, stop the program immediately using Ctrl+Z, locate the room tracking database or restore a backup.")
        from data_tracking import sql_database_setup
        try:
            sql_database_setup.create_room_tracking_database()
        except:
            os.remove(common.ROOM_DATA_TRACKING_DATABASE_FILE)
            print("Warning: Failed to create database")
            raise


def start_database():
    global database_connection
    database_connection = sqlite3.connect(common.ROOM_DATA_TRACKING_DATABASE_FILE)

def populate_tier_table():
    cur = database_connection.cursor()
    populate_tier_table_script = common.read_sql_file(common.ROOM_DATA_POPULATE_TIER_TABLE_SQL)
    cur.executescript(populate_tier_table_script)

def ensure_foreign_keys_on():
    cur = database_connection.cursor()
    cur.executescript("""PRAGMA foreign_keys = ON;""")
    
def initialize():
    load_room_data()
    start_database()
    ensure_foreign_keys_on()
    populate_tier_table()

def save_data():
    pass
    
def on_exit():
    save_data()
    database_connection.close()


if __name__ == '__main__':
    initialize()
    