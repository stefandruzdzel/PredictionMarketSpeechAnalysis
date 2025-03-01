"""
Future improvements:
    Get a data source that is posted sooner so I can have the most recent transcripts
    Verify spelling
    Backtest accuracy for weighting methodology

"""


import os
import datetime as dt
import pandas as pd
import numpy as np
import re

contestFilepath = 'Contest 20241102-2.csv'
event_type = 'Rally'


def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_data = f.read()
    
    # Remove commas: Drill, Baby Drill
    # also remove "smart quote" or typographically curly apostrophe, ’, instead of the standard straight apostrophe, '
    return raw_data.replace(',','').replace('’',"'").upper()

def get_percents(events, s_filter):
    unweighted = events.loc[s_filter,'Yes'].mean()
    weighted   = (events.loc[s_filter,'Yes']*events.loc[s_filter,'Weight'] / events.loc[s_filter,'Weight'].sum()).sum()
    return unweighted, weighted


def check_for_timestamp(text):
    if '(' in text and ')' in text:
        # if text.index(')') - text.index('(') == 8:
        return True
    return False


def split_text_by_speaker(contents):
    """
    contents = read_file(filepath)
    
    """
    temp = pd.DataFrame(contents.split('\n\n'),columns=['Text'])
    temp.loc[:,'Timestamp'] = temp.Text.apply(check_for_timestamp)
    temp.loc[temp.loc[:,'Timestamp'],'Speaker'] = temp.loc[temp.loc[:,'Timestamp'],'Text'].apply(lambda x:x.split('(')[0].strip())
    s_filter = temp.loc[:,'Speaker'] == ''
    temp.loc[s_filter,'Speaker'] = np.nan
    temp.loc[:,'Speaker'] = temp.loc[:,'Speaker'].fillna(method='ffill')
    temp.loc[:,'Speaker'] = temp.loc[:,'Speaker'].fillna('Unknown')
    temp.loc[:,'Speaker'] = temp.loc[:,'Speaker'].str.upper()
    # ('DONALD TRUMP','PRESIDENT DONALD J. TRUMP','DONALD J TRUMP','DONALD TRUMP JR.')
    temp.loc[:,'Trump?'] = temp.loc[:,'Speaker'].apply(lambda x:('DONALD' in x) and ('TRUMP' in x))
    # print(temp.loc[temp.loc[:,'Trump?']==False,'Speaker'].unique())
    trumpText = ''
    otherText = ''
    
    for i,row in temp.iterrows():
        if row['Trump?'] == True:
            trumpText += ' | ' + row['Text']
        else:
            otherText += ' | ' + row['Text']
    return trumpText, otherText


def percents_for_keyword(keywords, minCount, events_local, state):
    """
    
    keywords, minCount, events_local = keywords, row['Count'], events.copy()
    
    # For back testing
    keywords, minCount, events_local = keywords, row['Count'], events.query('Filename == %r'%(eventFilename)).copy()
    """
    
    events_local.loc[:,'Yes'] = 0
    events_local.loc[:,'Matches'] = 0
    events_local.loc[:,'PartOfAnotherWord'] = 0
    
    stringMatches = []
    for i,row in events_local.iterrows():
        contents = processedText[row['Filename']]
        # for i,contents in enumerate([trumpText, otherText]):
        
        runningCount = 0
        for keyword in keywords:
            
            pattern = rf"\b{keyword}(s|'s|es)?\b"
            # re.search(pattern, text, re.IGNORECASE)
            # re.findall(pattern, text, re.IGNORECASE)
            matches = [(match.start(), match.end()) for match in re.finditer(pattern, contents, re.IGNORECASE)]
            stringMatches.extend([[row['Filename'],contents[x[0]-15:x[1]+15]] for x in matches])
            runningCount += len(matches)
            

        if (runningCount >= minCount):
            events_local.loc[i,'Yes'] = 1
        
        
        events_local.loc[i,'Matches'] = runningCount
        events_local.loc[i,'PartOfAnotherWord'] = 0.#partOfAnotherWord
        
    s_filter = events_local.loc[:,'Type'] == 'OtherEvent'
    uw_perc_other, w_perc_other = get_percents(events_local, s_filter)

    s_filter = events_local.loc[:,'Type'] == 'Rally'
    uw_perc_rally, w_perc_rally = get_percents(events_local, s_filter)

    s_filter = events_local.loc[:,'Type'] != -1 # All
    uw_perc_all, w_perc_all = get_percents(events_local, s_filter)
    
    s_filter = (events_local.loc[:,'State'] == state) & (events_local.loc[:,'Type'] == event_type)
    uw_perc_state, w_perc_state = get_percents(events_local, s_filter)
    
    return uw_perc_other, w_perc_other, uw_perc_rally, w_perc_rally, uw_perc_all, w_perc_all, uw_perc_state, w_perc_state, stringMatches, events_local.copy()



today = dt.datetime.now()

events = pd.read_csv(r'Speeches\EventDetails.csv').fillna('')
events.loc[:,'Date'] = events.Filename.apply(lambda x:dt.datetime.strptime(x.split('-')[0],'%Y%m%d'))
events.loc[:,'DaysOut'] = events.loc[:,'Date'].apply(lambda x:(today-x).days)
events.loc[:,'Rank'] = events.loc[:,'DaysOut'].rank()
events.loc[:,'Weight'] = 1./(events.loc[:,'Rank'] + events.loc[:,'Rank'].mean())

df = pd.read_csv(contestFilepath).fillna('')




events.loc[:,'State'] = events.loc[:,'Location'].apply(lambda x:x.split(',')[1].strip())

s_filter = contestFilepath == events.loc[:,'ContestFile']
if np.sum(s_filter) == 1:
    state = events.loc[s_filter,'State'].values[0]
else:
    print('Contest file is not inked in EventDetails.csv, can\'t find State')
    state = ''
    
# Trim down events file to just ones where we already have the speech data
s_filter = events.loc[:,'Filename'].apply(lambda x:os.path.isfile(os.path.join('Speeches',x+'.txt')))
events = events.loc[s_filter,:].reset_index(drop=True)

if state != '':
    print('State matches count:',np.sum((events.loc[:,'State']==state)&(events.loc[:,'Type']==event_type)))
processedText = {}

for i,row in events.iterrows():
    file = row['Filename']+'.txt'
    filepath = os.path.join('Speeches',file)
    contents = read_file(filepath)
    trumpText, otherText = split_text_by_speaker(contents)
    processedText[row['Filename']] = trumpText



df.loc[:,['uw_perc_other', 'w_perc_other', 'uw_perc_rally', 'w_perc_rally', 'uw_perc_all', 'w_perc_all','uw_perc_state', 'w_perc_state']] = 0.0
error_checking = []
events_dfs_list = []


for i,row in df.iterrows():
    keywords = [row['Main']]
    if row['AdditionalTerms'] != '':
        keywords.extend(row['AdditionalTerms'].split(','))
    keywords = [x.upper() for x in keywords]

    temp = percents_for_keyword(keywords, row['Count'], events.copy(), state)
    df.loc[i,['uw_perc_other', 'w_perc_other', 'uw_perc_rally', 'w_perc_rally', 'uw_perc_all', 'w_perc_all','uw_perc_state', 'w_perc_state']] = temp[:8]
    error_checking.append(temp[-2])
    events_dfs_list.append(temp[-1])

files = events.query('Type == "%s"'%(event_type)).loc[:,'Filename']
byEvent = pd.DataFrame(columns=files)

for i,row in df.iterrows():
    byEvent.loc[i,:] = events_dfs_list[i].query('Type == "%s"'%(event_type)).loc[:,'Yes'].values
    
byEvent.index = df.Main    

"""
i = 8
row = df.iloc[i]
print(row['Main'])
z = events_dfs_list[i]
text = pd.DataFrame(error_checking[i],columns=['File','text'])
print(z.query('Type == "Rally"').Yes)
"""

# .25 =  25% expected return
# Yes is inherently more risky, since if he doesn't speak then No wins
# Although he's been speaking longer and longer
# min_e_value_yes = .10
# min_e_value_no  = .10

# df.loc[:,'Yes Price'] = df.loc[:,'w_perc_rally'] - min_e_value_yes
# df.loc[:,'No Price'] = 1-df.loc[:,'w_perc_rally'] - min_e_value_no





# print('Rally %:',rallyYes/rallyTotal)
# print('Event %:',eventYes/eventTotal)
# print('All %:',allYes/allTotal)



# file = '20241012-2.txt'
# index = contents.index(keyword)
# contents[index-15:index+16]


