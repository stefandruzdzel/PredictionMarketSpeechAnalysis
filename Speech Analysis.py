"""
Future improvements:
    Get a data source that is posted sooner so I can have the most recent transcripts
    Verify spelling
    Get apostrophe's to work, as in "McDonald's"
    Verify that my word counts match past results on PolyMarket

"""


import os
import datetime as dt
import pandas as pd

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_data = f.read()
    
    return raw_data.upper()


today = dt.datetime.now()

events = pd.read_csv(r'Speeches\EventDetails.csv')
events.loc[:,'Date'] = events.Filename.apply(lambda x:dt.datetime.strptime(x.split('-')[0],'%Y%m%d'))
events.loc[:,'DaysOut'] = events.loc[:,'Date'].apply(lambda x:(today-x).days)
events.loc[:,'Rank'] = events.loc[:,'DaysOut'].rank()
events.loc[:,'Weight'] = 1./events.loc[:,'Rank']

df = pd.read_csv('Contest 20241018.csv').fillna('')

df.loc[:,'AllowPartial'] = df.loc[:,'AllowPartial']==1

def get_percents(events, s_filter):
    unweighted = events.loc[s_filter,'Yes'].mean()
    weighted   = (events.loc[s_filter,'Yes']*events.loc[s_filter,'Weight'] / events.loc[s_filter,'Weight'].sum()).sum()
    return unweighted, weighted

def percents_for_keyword(keywords, minCount, bAllowPartial):
    # keywords = ['dark maga']
    # minCount = 1
    events.loc[:,'Yes'] = 0
    events.loc[:,'Matches'] = 0
    events.loc[:,'PartOfAnotherWord'] = 0
    
    stringMatches = []
    for i,row in events.iterrows():
        file = row['Filename']+'.txt'
        filepath = os.path.join('Speeches',file)
        contents = read_file(filepath)
        
        runningCount = 0
        for keyword in keywords:
            
            count = contents.count(keyword.upper())
            # print(keyword,file,count)
            runningCount += count
            
            bMatch = keyword in contents
            partOfAnotherWord = 0
            while bMatch == True:
                index = contents.index(keyword)
                

                # Check to see if it's part of another word
                leadingChar  = contents[index-1]
                trailingChar = contents[index+len(keyword)]
                if leadingChar.isalpha() or (trailingChar.isalpha() and not trailingChar in ('S')): #,'’',"'"
                    bPartial = True
                    partOfAnotherWord += 1
                    # if  keyword == 'ELON':
                    #     print(stringMatches[-1])
                else:
                    bPartial = False
                
                stringMatches.append([file,contents[index-15:index+len(keyword)+15],'partial?:',bPartial])
                
                contents = contents[index+len(keyword):]
                bMatch = keyword in contents
        
        if bAllowPartial == False:
            
            # if partOfAnotherWord > 0:    
            #     print(bAllowPartial,runningCount,partOfAnotherWord, minCount)
            runningCount -= partOfAnotherWord
            
        if (runningCount >= minCount):
            events.loc[i,'Yes'] = 1
        
        
        events.loc[i,'Matches'] = runningCount
        events.loc[i,'PartOfAnotherWord'] = partOfAnotherWord
        
    s_filter = events.loc[:,'Type'] == 'OtherEvent'
    uw_perc_other, w_perc_other = get_percents(events, s_filter)

    s_filter = events.loc[:,'Type'] == 'Rally'
    uw_perc_rally, w_perc_rally = get_percents(events, s_filter)

    s_filter = events.loc[:,'Type'] != -1 # All
    uw_perc_all, w_perc_all = get_percents(events, s_filter)

    if events.loc[:,'Matches'].sum() > 0:
        percPartOfAnotherWord = events.loc[:,'PartOfAnotherWord'].sum() / events.loc[:,'Matches'].sum()
    else:
        percPartOfAnotherWord = 0.0
    
    return uw_perc_other, w_perc_other, uw_perc_rally, w_perc_rally, uw_perc_all, w_perc_all, percPartOfAnotherWord, stringMatches

df.loc[:,['uw_perc_other', 'w_perc_other', 'uw_perc_rally', 'w_perc_rally', 'uw_perc_all', 'w_perc_all', 'percPartOfAnotherWord']] = 0.0
error_checking = []
for i,row in df.iterrows():
    keywords = [row['Main']]
    if row['AdditionalTerms'] != '':
        keywords.extend(row['AdditionalTerms'].split(','))
    keywords = [x.upper() for x in keywords]

    temp = percents_for_keyword(keywords, row['Count'], row['AllowPartial'])
    df.loc[i,['uw_perc_other', 'w_perc_other', 'uw_perc_rally', 'w_perc_rally', 'uw_perc_all', 'w_perc_all', 'percPartOfAnotherWord']] = temp[:7]
    error_checking.append(temp[-1])



# .25 =  25% expected return
# Yes is inherently more risky, since if he doesn't speak then No wins
min_e_value_yes = .30
min_e_value_no  = .25

df.loc[:,'Yes Price'] = df.loc[:,'w_perc_rally'] - min_e_value_yes
df.loc[:,'No Price'] = 1-df.loc[:,'w_perc_rally'] - min_e_value_no



# print('Rally %:',rallyYes/rallyTotal)
# print('Event %:',eventYes/eventTotal)
# print('All %:',allYes/allTotal)



# file = '20241012-2.txt'
# index = contents.index(keyword)
# contents[index-15:index+16]


"""
tax 100%
million .66
Inflation .833
elon

"""