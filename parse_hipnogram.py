# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 12:47:44 2016

@author: user
"""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import datetime as dt

stage_to_num = {'W':5, 'R':1, 'N1':2 , 'N2':3, 'N3':4 }
num_to_stage = {5: 'wake', 1 : 'rem', 2 :'N1', 3 : 'N2', 4: 'N3'}


try:
    neuroon_raw
    print('loaded')
except:
    print('loading')
    
def parse_neuroon_stages(permute = False, time_shift = 0, night = 1):

    if night == 1 :
        neuroon_raw = pd.read_csv('neuroon_signals/night_01/neuroon_stages.csv', index_col = 0)
    elif night ==2 :
        neuroon_raw = pd.read_csv('neuroon_signals/night_02/neuroon_stages.csv', index_col = 0)




    neuroon_stages = neuroon_raw.copy()
    
    # permute the stage number before binning into stages to simulate random assignment into stages - it proably is not random originally because we can see different average durations for different phases, i.e. rem is longer and continous or something  of a sort
    if(permute):
        neuroon_stages.loc[:, 'stage'] = np.random.permutation(neuroon_stages['stage'].as_matrix())
        
    # add two hours because time was saved in a different timezone
    neuroon_stages['timestamp'] = pd.to_datetime(neuroon_stages['timestamp'].astype(int), unit='ms', utc=True) \
    + pd.Timedelta(hours = 2) + pd.Timedelta(seconds = time_shift) 

    # Change from negative to positive stages coding
    neuroon_stages.loc[:, 'stage_num'] = np.abs(neuroon_stages['stage'])
    
    # Change the code of wake from 0 to 5, we'll need zero value later
    neuroon_stages.loc[neuroon_stages['stage_num'] == 0, 'stage_num'] = 5

    #Mark the row where a new stage startes
    neuroon_stages['stage_start'] = neuroon_stages['stage_num'] - neuroon_stages['stage_num'].shift(1)
    neuroon_stages['stage_end'] = neuroon_stages['stage_num'] - neuroon_stages['stage_num'].shift(-1)
    
    # mark the rows where stage started and where it ended
    neuroon_stages.loc[neuroon_stages['stage_start'] != 0, 'stage_shift'] = 'start'
    neuroon_stages.loc[neuroon_stages['stage_end'] != 0, 'stage_shift'] = 'end'

    # Find stages that lasted for one sampling interval, 30 sec
    neuroon_stages.loc[(neuroon_stages.loc[:,'stage_start'] != 0) & (neuroon_stages.loc[:,'stage_end'] != 0), 'stage_shift'] = 'short'
#    
    # Subtract 29.999 seconds from start, because it's onset is after a 30 sec interval where stage is calculated.
    # This subtraction will work in favor of neuroon because it was not availible in real time
    neuroon_stages.loc[neuroon_stages['stage_shift'] == 'start', 'timestamp'] = neuroon_stages.loc[neuroon_stages['stage_shift'] == 'start', 'timestamp'] - dt.timedelta(milliseconds = (1000 * 30) -1)
    # Leave only the rows where the stage shifted    
    neuroon_stages = neuroon_stages[pd.notnull(neuroon_stages['stage_shift'])]
            
    # Add the column with string names for stages
    neuroon_stages['stage_name'] = neuroon_stages['stage_num'].replace(num_to_stage)

    # Convert the short stages that had only one row, two two rows format with start and end time (assuming start was actually 30 sec before)
    extra_starts = neuroon_stages.loc[neuroon_stages['stage_shift'] == 'short', :]
    extra_starts.loc[:,'timestamp'] = extra_starts.loc[:,'timestamp'] - dt.timedelta(milliseconds = (1000 * 30) -1)
    extra_starts.loc[:,'stage_shift'] = 'start'
    # Add the extra start rows for short events to the main data frame
    neuroon_stages = neuroon_stages.append(extra_starts, ignore_index = True)
    # Sort by timestamp to have correct event order
    neuroon_stages = neuroon_stages.sort(columns = 'timestamp')
    # Rename the shorts to ends
    neuroon_stages.loc[neuroon_stages['stage_shift'] == 'short', 'stage_shift'] = 'end' 

   
    
    neuroon_stages.set_index(neuroon_stages['timestamp'], inplace = True)

    #Add unique event number for each phase occurence
    neuroon_stages['event_number'] = np.array([[i]*2 for i in range(int(len(neuroon_stages) /2))]).flatten()
    
     # Drop the columns used for stage_shift calculation
    neuroon_stages.drop(['stage_start', 'stage_end', 'stage'], axis = 1, inplace = True)
    
    if permute == False:
        neuroon_stages.to_csv('parsed_data/neuroon_hipnogram.csv', index = False)

    return neuroon_stages


def parse_psg_stages(night = 1):
    if(night == 1):
        path = 'neuroon_signals/night_01/psg_stages.csv'
    elif(night == 2):
        path = 'neuroon_signals/night_02/psg_stages.csv'
    psg_stages = pd.read_csv(path, header = None, names = ['timestamp', 'stage'])

    # Select only the rows describing the sleep stage
    psg_stages = psg_stages.loc[psg_stages['stage'].str.contains('Stage'), :]
    # Subtract unused parts of the string
    psg_stages.loc[:, 'stage' ]  = psg_stages['stage'].str.replace('Stage - ', '')
    psg_stages = psg_stages.loc[psg_stages['stage'] != 'No Stage', :]

    # Parse the time info from the string timestamp to the datetime object
    # We need to add the month and day info. Note that it changes after midnight 00:00:00
    #Get rid of empty spaces
    psg_stages.loc[:, 'timestamp']  = psg_stages['timestamp'].str.replace(' ', '')

    # Get only the hours to find a change of date index
    psg_stages['hour'] = pd.to_numeric(psg_stages['timestamp'].str[0:2], errors = 'coerce')
    # Find the index where the day changes, i.e. the first time the hour is greater than 00:00:00
    new_date = np.where(psg_stages['hour'] == 0)[0][0]
    # Add the day info to the datetime, accounting for the change after midnight
    if night == 1:
        psg_stages.iloc[0 : new_date, 0] = '2016-06-20 ' + psg_stages.iloc[0 : new_date, 0]
        psg_stages.iloc[new_date::, 0] = '2016-06-21 ' + psg_stages.iloc[new_date ::, 0]
    elif night ==2:
        psg_stages.iloc[0 : new_date, 0] = '2016-06-21 ' + psg_stages.iloc[0 : new_date, 0]
        psg_stages.iloc[new_date::, 0] = '2016-06-22 ' + psg_stages.iloc[new_date ::, 0]


    # Convert the string timestamp to datetime object
    psg_stages['timestamp'] =  pd.to_datetime(psg_stages['timestamp'],format = '%Y-%m-%d %H:%M:%S.%f')

    # Create numeric column with stage info
    psg_stages['stage_num'] = psg_stages['stage'].replace(stage_to_num)
    # Change the naming convention so it is the same between neuroon and psg hipnograms
    psg_stages['stage_name'] = psg_stages['stage_num'].replace(num_to_stage)
    
    # Mark the starting and ending time of each stage
    psg_stages['stage_shift']  ='start'
    
    # Stage start will always be followed by an end event.
    # Stage starts will have even indices, ends will have odd indices
    psg_stages['order'] = range(0, len(psg_stages) *2, 2)
    
    # Create the copy of start events and assign to them timestamp of the nex row, then they become end events.
    psg_copy = psg_stages.copy()
    psg_copy['stage_shift'] = 'end'
    psg_copy['order']= range(1, len(psg_stages) * 2, 2)
    # Here we assign the next row timestamp, and subtract one millisecond from it - pandas does not comply with duplicate indices, 
    # and subtracting one millisecond from an end event wil make it have a different timestamp from the next start event.
    psg_copy['timestamp'] = psg_copy['timestamp'].shift(-1) - pd.Timedelta(milliseconds = 1)

    # Combine starts and ends and sort them by order column, to have start,end,start,end,start,end, etc... order.
    psg_stages = psg_stages.append(psg_copy).sort('order')
    
    # Deal with the last timestamp which is Nan because of .shift() function
    psg_stages.iloc[-1, psg_stages.columns.get_loc('timestamp')] = psg_stages.iloc[-2, psg_stages.columns.get_loc('timestamp')] + pd.Timedelta(milliseconds = 1)

    
    psg_stages.set_index(psg_stages['timestamp'], inplace = True)

    
    #Add unique event number for each phase occurence
    psg_stages['event_number'] = np.array([[i]*2 for i in range(int(len(psg_stages) / 2))]).flatten()

    psg_stages.drop(['hour', 'order', 'stage'], axis = 1, inplace = True)

    psg_stages.to_csv('parsed_data/' +'psg_hipnogram.csv', index = False)
    return psg_stages
    
def prep_for_spectral(hipnogram):
    hipnogram = hipnogram.reset_index(drop = True)
    
    grouped = hipnogram.groupby('stage_shift', as_index=False)
    starts = grouped.get_group('start')
    ends = grouped.get_group('end')
    
    starts.loc[:,'ends'] = np.array(ends['timestamp'])
    starts.rename(columns = {'timestamp':'starts'}, inplace = True)
    
    return starts
