

import nflreadpy as nfl
import pandas as pd
import requests
import io
import time
import re

def get_cleaned_data():

    # Use load_player_stats instead of import_weekly_data
    # Note: nflreadpy returns Polars DataFrames by default
    player_stats = nfl.load_player_stats([2021])

    # If you prefer working with pandas, convert it easily:
    df_stats = player_stats.to_pandas()

    #below we are specifying what specific columns are required
    columns = ['week', 'player_display_name', 'position', 'season', 'team', 'fantasy_points']
    df_stats = df_stats[columns]

    df_stats = df_stats.rename(columns={'player_display_name':'Name', 'season':'Year', 'week':'Week'})
    #changes the two column names to match with our future df_fantasy names


    def get_all_weeks_data(num_weeks=18, game_type='fd'):
        all_weeks_list = []
        
        for week in range(1, num_weeks + 1):
            print(f"Fetching data for week {week}...")
            url = f"http://rotoguru1.com/cgi-bin/fyday.pl?week={week}&game={game_type}&scsv=1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            try:
                response = requests.get(url, headers=headers)
                raw_text = response.text
                
                # Isolate the data block
                csv_start = raw_text.find("Week;Year")
                if csv_start != -1:
                    data = raw_text[csv_start:]
                    df = pd.read_csv(io.StringIO(data), sep=';', on_bad_lines='skip')
                    
                    # Apply the filtering logic to ensure valid stats
                    df = df[pd.to_numeric(df['Week'], errors='coerce').notnull()]
                    df['Week'] = df['Week'].astype(int)
                    
                    all_weeks_list.append(df)
                
                # Polite delay to respect the server
                time.sleep(1) 
                
            except Exception as e:
                print(f"Error fetching week {week}: {e}")
                
        # Combine all individual week DataFrames into one
        if all_weeks_list:
            final_df = pd.concat(all_weeks_list, ignore_index=True)
            return final_df
        else:
            return None

    # Usage
    df_fantasy = get_all_weeks_data(18)
    if df_fantasy is not None:
        #display(df_fantasy.head())
        #display(df_fantasy.tail())
        print(f"Total rows collected: {len(df_fantasy)}")


    req_cols = ['Year', 'Week', 'Name', 'FD points', 'FD salary']
    df_fantasy = df_fantasy[req_cols]
    #this reads in our text file into a dataframe and only keeps the necessary columns

    df_fantasy = df_fantasy.rename(columns={'FD points':'proj_points'})
    #this reorders the names from last, first to first last and changes 
    #the column name of the proj points

    df_fantasy = df_fantasy.astype({
        'Week': 'int32',
        'Year': 'int32'
    })

    #function to remove common suffixes and reformat from "LAST, FIRST" to "FIRST LAST"
    def clean_and_format_name(name):
        #Removes common suffixes (II, III, IV, Jr., Sr.)
        #this regex looks for these suffixes and removes them
        cleaned_name = re.sub(r'\s+(Jr|Sr|II|III|IV)\.?', '', name)
        
        #Split and reorder from "LAST, FIRST" to "FIRST LAST"
        if ',' in cleaned_name:
            parts = cleaned_name.split(', ')
            if len(parts) == 2:
                return f"{parts[1]} {parts[0]}"
        return cleaned_name

    df_fantasy = df_fantasy[df_fantasy['Name'] != 'Cottrell, Nathan']
    #drops Nathan Cottrell, the only RB with a null salary - he only appears in week 16

    #apply the cleaning function to the 'Name' column in df_fantasy
    df_fantasy['Name'] = df_fantasy['Name'].apply(clean_and_format_name)


    df_merged = pd.merge(df_fantasy, df_stats, on=['Name', 'Year', 'Week'], how='inner')
    #merges the two dataframes by Name, Week, and Year

    col_order = ['Year', 'Week', 'Name', 'position', 'team', 'proj_points', 'FD salary', 'fantasy_points']
    df_merged = df_merged[col_order]
    df_merged[['proj_points', 'FD salary', 'fantasy_points']] = df_merged[['proj_points', 'FD salary', 'fantasy_points']].round(2)
    #this reorders the data and rounds all relevant number values to two decimal places per standard

    df_merged['position'] = df_merged['position'].replace({'FB':'RB'})

    valid_positions = ['QB','RB','WR','TE']
    df_merged = df_merged[df_merged['position'].isin(valid_positions)]

    # ... [Your team's existing data loading and cleaning code is up here] ...
    # Assuming your cleaned data is currently sitting in the 'df_merged' variable

    print("Fetching official NFL headshots...")

    # 1. Load the roster data for the years in your dataset
    # (Make sure to include all the years your dashboard supports)
    rosters_polars = nfl.load_rosters([2021]) 
    rosters_df = rosters_polars.to_pandas()

    # 2. Extract only the names and image URLs
    # The nflverse roster file labels the player name as 'full_name'
    headshots_df = rosters_df[['full_name', 'headshot_url']].copy()

    # 3. Drop duplicates to create a clean master lookup table
    # (Players appear in the roster every single year, we only need their URL once)
    headshots_df = headshots_df.drop_duplicates(subset=['full_name'])

    # 4. Rename 'full_name' to match your exact column header
    headshots_df = headshots_df.rename(columns={'full_name': 'Name'})

    # 5. Merge the URLs onto your master dataframe
    print("Merging headshots into master dataset...")
    df_merged = pd.merge(df_merged, headshots_df, on='Name', how='left')

    # 6. Safety Net: Fill missing URLs with a placeholder image 
    # This prevents Streamlit from throwing a broken image error if a rookie is missing a photo
    df_merged['headshot_url'] = df_merged['headshot_url'].fillna('https://via.placeholder.com/150?text=No+Photo')

    # return df_merged

    return df_merged

if __name__ == "__main__":
    # This block allows you to still run the script directly for testing
    result = get_cleaned_data()
    #print(result.head())


'''
from collect_clean import get_cleaned_data

# Call the function and capture the return value
my_df = get_cleaned_data()

# Now 'my_df' holds your 'df_merged'
print(my_df.head())

'''
