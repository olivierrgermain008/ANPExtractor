'''
This code extracts the data made public by the ANP.
Original files can be found at: https://reate.cprm.gov.br/anp/TERRESTREen
As this is not a proper web site made for robotic exploration but essentially an exposed file management system, similar to SharePoint, 
the files have to be downloaded in bulk.
This is best done at night, when the download directory can be changed to a Sharepoint one previously mounted to the local machine.
Then the zip can be expanded to the same directory, and deleted. Keep the files as offline only. 
The files are then ready to be processed.
The code will first ask where are the files, so the synched directory can be selected. It will only download the needed files (txt ones, small) as it needs them.
After that, the code create a map with the data, as well as a csv file.
Those two files will be saved in the same directory where the text files are located.
'''

import re
import os
import glob
import pandas as pd
import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter import filedialog
from tkinter import messagebox
import folium
from dateutil.parser import parse
import bisect
from datetime import datetime
from branca.element import Template, MacroElement
import webbrowser
import shutil
import easygui

# Pop up window to select the directory where the text files are located
root = tk.Tk()
root.withdraw()
myfiles_path = filedialog.askdirectory()

# Pop up another window to let the user enter the name of the field
def get_oilfield_name():
    tk.Tk().withdraw()  # to hide the main window
    oilfield_name = askstring("Input", "Enter the name of the oilfield:")
    return oilfield_name
oilfield_name = get_oilfield_name()

# Pop up another window with radio buttons to let the user choose the type of folder he is using (0, 1, 2 or 3 levels deep)
def get_folder_depth():
    options = ["1 level", "2 levels", "3 levels", '4 levels']
    message = "Please select an option about how deep are the data files buried into the folder structure from the directory you just selected.\r\n1 level down (e.g. Technical folder / Data files\r\n2 levels down (e.g.: Wells / Technical folders / Data files)\r\n3 levels down (e.g.: Categories / Wells / Technical folders / Data files)\r\n4 levels down (e.g.: Field / Categories / Wells / Technical folders / Data files)"
    title = "Option Selection"

    choice = easygui.buttonbox(message, title, options)

    if choice == "1 level":
        return 0
    elif choice == "2 levels":
        return 1
    elif choice == "3 levels":
        return 2
    elif choice == "4 levels":
        return 3
folder_depth = get_folder_depth()

# This function extracts the key data of abandonned wells from a formatted "agp" file
def keydata_agp(lines):
        for line in lines:
            # Extracts the POCO name
            if line.startswith(' POCO'):
                # Find the position where 'POCO' starts
                start = line.find(' POCO')
                # Extract the rest of the line
                rest_of_line = line[start + len(' POCO'):].strip()
                # Remove "           :   " from the text
                rest_of_line = rest_of_line.lstrip("           :   ")
                poco = rest_of_line

            # In some rare cases, POCO is written as POÇO
            if line.startswith(' PO\u00C7O'):
                # Find the position where 'POCO' starts
                start = line.find(' PO\u00C7O')
                # Extract the rest of the line
                rest_of_line = line[start + len(' PO\u00C7O'):].strip()
                # Remove "           :   " from the text
                rest_of_line = rest_of_line.lstrip("           :   ")
                poco = rest_of_line
    
            # Extracts the well ID    
            if line.startswith(' IDENTIFICADOR'):
                # Find the position where 'POCO' starts
                start = line.find(' IDENTIFICADOR')
                # Extract the rest of the line
                rest_of_line = line[start + len(' IDENTIFICADOR'):].strip()
                # Remove "  :   " from the text
                rest_of_line = rest_of_line.lstrip("  :   ")
                well_id, rest_of_line = rest_of_line.split(' ', 1)
    
            # Extracts the well end date
            if line.startswith(' TERMINO'):
                # Find the position where 'POCO' starts
                start = line.find(' TERMINO')
                # Extract the rest of the line
                rest_of_line = line[start + len(' TERMINO'):].strip()
                # Remove "        :   " from the text
                rest_of_line = rest_of_line.lstrip("        :   ")
                end_date, rest_of_line = rest_of_line.split(' ', 1)
                        
            # Extracts the Latitude, Longitude and other format of Latitude and Longitude (other formats not used later in the code)
            if line.startswith(' LATITUDE'):
                # Find the position where 'POCO' starts
                start = line.find(' LATITUDE')
                # Extract the rest of the line
                rest_of_line = line[start + len(' LATITUDE'):].strip()
                # Remove "       :   " from the text
                rest_of_line = rest_of_line.lstrip("       :   ")
                # Split the rest of the line at the first space
                latitude, rest_of_line = rest_of_line.split(' ', 1)
                lat_otherformat = re.search('\((.*?)\)', rest_of_line).group(1)
                lat_otherformat = lat_otherformat.lstrip()
                other_text, useful_text = rest_of_line.split('LONGITUDE      :   ', 1)
                longitude, rest_of_line = useful_text.split(' ', 1)
                long_otherformat = re.search('\((.*?)\)', rest_of_line).group(1)
                long_otherformat = long_otherformat.lstrip()
        return (poco, well_id, end_date, latitude, longitude, lat_otherformat, long_otherformat)

# This function extracts the key data of abandonned wells from a formatted "dados" file
def keydata_dados(lines):
    latitude_processed = False # this is because there are multiple lines with latitude and longitude in the dados file
    for line in lines:
        # Extracts the well name
        if line.startswith('PREFIXO ANP       : '):
            start = line.find('PREFIXO ANP       : ')
            rest_of_line = line[start + len('PREFIXO ANP       : '):].strip()
            poco = rest_of_line

        # Extracts the well ID
        if line.startswith('CADASTRO ANP      : '):
            start = line.find('CADASTRO ANP      : ')
            rest_of_line = line[start + len('CADASTRO ANP      : '):].strip()
            well_id = rest_of_line

        # Extracts the Latitude and Longitude
        if line.startswith('    Latitude     :  ') and not latitude_processed:
            start = line.find('    Latitude     :  ')
            # Extract the rest of the line
            rest_of_line = line[start + len('    Latitude     :  '):].strip()
            # Split the rest of the line at the first space
            latitude, rest_of_line = rest_of_line.split(' ', 1)
            # Extract the longitude
            rest_of_line = rest_of_line[len('   Longitude    : '):].strip()
            longitude, rest_of_line = rest_of_line.split(' ', 1)
            latitude_processed = True
            
         # Extracts the End date
        if line.startswith('DATA DE TERMINO DO POCO       : '):
            start = line.find('DATA DE TERMINO DO POCO       : ')
            rest_of_line = line[start + len('DATA DE TERMINO DO POCO       : '):].strip()
            end_date = rest_of_line
    return (poco, well_id, end_date, latitude, longitude)

# This will transform a data string into a datetime object
def custom_date_parser(date):
    try:
        # Split the date string into day, month, and year
        day, month, year = date.split('/')
        # If the year only has two digits, add "19" to the start
        if len(year) == 2:
            year = '19' + year
        # Reassemble the date string
        date = '/'.join([day, month, year])
        # Parse the date string with dayfirst=True
        return parse(date, dayfirst=True)
    except ValueError:
        return pd.Timestamp('1990-01-01')

# Copy a file from its original location to a chosen folder
def copy_file(file, folder_name):
    destination_dir = os.path.join(myfiles_path, folder_name, '')
    destination_dir = destination_dir.replace('\\', '/')
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    new_file_name = os.path.join(destination_dir, oilfield_name + '_' + os.path.basename(file))
    shutil.copy2(file, new_file_name)

# Creates a dataframe to store the extracted AGP well data
def create_agpdf():
    allmywells_df = pd.DataFrame(columns=['Path', 'POCO', 'Well ID', 'End Date', 'Latitude', 'Longitude'])
    # Get all the txt files in your directory and subdirectories with a name called AGP
    files = [f for f in glob.glob(os.path.join(myfiles_path, '**/*AGP.txt'), recursive=True)]
    for file in files:
            if os.path.isfile(file):
                print('Now processing file:', file)
                txtgoto = oilfield_name + '_CopiedTXT'
                copy_file(file, txtgoto)
                with open(file, 'r') as my_file:
                    lines = my_file.readlines()
                    poco, well_id, end_date, latitude, longitude, lat_otherformat, long_otherformat = keydata_agp(lines)
                    new_row = pd.DataFrame({'Path': [file], 'POCO': [poco], 'Well ID': [well_id], 'End Date': [end_date], 'Latitude': [latitude], 'Longitude': [longitude]})
                    allmywells_df = pd.concat([allmywells_df, new_row], ignore_index=True)
    return allmywells_df
allmywells_df = create_agpdf()

# Creates a dataframe to store the extracted DADOS well data
def create_dadosdf():
    allmywells_df = pd.DataFrame(columns=['Path', 'POCO', 'Well ID', 'Latitude', 'Longitude'])
    # Get all the txt files in your directory and subdirectories with a name called DADOS
    files = [f for f in glob.glob(os.path.join(myfiles_path, '**/*DADOS.txt'), recursive=True)]
    for file in files:
            if os.path.isfile(file):
                print('Now processing file:', file)
                txtgoto = oilfield_name + '_CopiedTXT'
                copy_file(file, txtgoto)
                with open(file, 'r') as my_file:
                    lines = my_file.readlines()
                    poco, well_id, end_date, latitude, longitude = keydata_dados(lines)
                    new_row = pd.DataFrame({'Path': [file], 'POCO': [poco], 'Well ID': [well_id], 'End Date': [end_date], 'Latitude': [latitude], 'Longitude': [longitude]})
                    allmywells_df = pd.concat([allmywells_df, new_row], ignore_index=True)
    return allmywells_df
allmywells_df = pd.concat([allmywells_df, create_dadosdf()])

allmywells_df['End Date'] = allmywells_df['End Date'].apply(custom_date_parser)
allmywells_df['End Date'] = pd.to_datetime(allmywells_df['End Date'])
allmywells_df['Path'] = allmywells_df['Path'].str.replace('\\',' / / ', regex = False)
allmywells_df['Path'] = allmywells_df['Path'].str.replace(myfiles_path, oilfield_name+' ', regex=False)
file_path = os.path.join(myfiles_path, 'allwells_data.csv')
allmywells_df.to_csv(file_path, index=False)

# This function finds the AGP folders that do not contain the right types of files
def find_agpfolders_without_files(directory):
    folders = []
    print('Now finding AGP folders without the right types of files')
    for dirpath, dirnames, filenames in os.walk(directory):
        if os.path.basename(dirpath) == 'AGP':
            files = os.listdir(dirpath)
            if not any(fn.endswith('agp.txt') or fn.endswith('dados.txt') for fn in files):
                folders.append(dirpath)
    with open(os.path.join(myfiles_path, 'AGP_missingfiles.txt'), 'w') as f:
            if not folders:
                f.write('All AGP folders contain the right types of files\n')
            else:
                for folder in folders:
                    f.write(folder + '\n')
find_agpfolders_without_files(myfiles_path)

# This function checks if each well file structure contains an AGP folder and gives the name of the wells that do not
def find_subfolders_without_AGP(directory):
    subfolders = []
    print('Now finding wells without AGP folders')
    for dirpath, dirnames, filenames in os.walk(directory):
         # Split the path into components
        path_parts = dirpath.split(os.sep)
        ''' Replace the number below with 2 if you download the whole field data, 1 if you download the data from one category only'''
        if len(path_parts) - len(myfiles_path.split(os.sep)) == 2:
            # Check if 'AGP' is not in the directory names
            if 'AGP' not in dirnames:
                subfolders.append(dirpath)
        with open(os.path.join(myfiles_path, 'Missing_AGP_folders.txt'), 'w') as f:
            if not subfolders:
                f.write('All AGP folders contain the right types of files\n')
            else:
                for folder in subfolders:
                    f.write(folder + '\n')
find_subfolders_without_AGP(myfiles_path)

# Creates the map of well, with markers colored by the date of abandonment split into 8 equal periods
def create_map():
    # Create a map centered at an initial location
    print('Now creating the map')
    
    allmywells_df['Latitude'] = allmywells_df['Latitude'].str.strip().astype(float)
    allmywells_df['Longitude'] = allmywells_df['Longitude'].str.strip().astype(float)
    initial_latitude = allmywells_df['Latitude'].mean()
    initial_longitude = allmywells_df['Longitude'].mean()

    m = folium.Map(location=[initial_latitude, initial_longitude])
    # Calculate the bounds of the data and fit the map to them
    sw = allmywells_df[['Latitude', 'Longitude']].min().values.tolist()
    ne = allmywells_df[['Latitude', 'Longitude']].max().values.tolist()
    m.fit_bounds([sw, ne]) 
    
    # Calculate the spread of the abandonment dates so as to fit the marker colors to this spread
    first_abandoned = allmywells_df['End Date'].min()
    last_abandoned = allmywells_df['End Date'].max()
    spread = last_abandoned - first_abandoned
    spread_in_days = spread.days
    dates = pd.date_range(start=first_abandoned, periods=8, freq=str(spread_in_days//7) + 'D')
    dates_list = dates.to_list()
    mycolors = ['black', 'gray', 'red', 'orange', 'green', 'blue', 'pink', 'purple']

    # Add a colored marker for each abandoned well
    for index, row in allmywells_df.iterrows():
        if row['End Date'] < dates_list[0]:
            index = 0
        elif row['End Date'] > dates_list[-1]:
            index = len(dates_list) - 1
        else:
            index = bisect.bisect_right(dates_list, row['End Date']) % len(mycolors)
        pincolor = mycolors[index]
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=f"POCO: {row['POCO']}, Well ID: {row['Well ID']}, End Date: {row['End Date'].strftime('%Y-%m-%d')}",
            icon=folium.Icon(color=pincolor)
        ).add_to(m)
        
    # Create a color map
    color_map = {dates_list[i]: mycolors[i] for i in range(len(dates_list))}

    # Create a legend
    legend_html = '''
    <div style="position: absolute; bottom: 50px; right: 50px; width: 150px; height: 300px; 
    border:2px solid grey; z-index:9999; font-size:14px; background-color:white; opacity: 0.8;">
    '''
    legend_html += "<h4 style='text-align: center;'>Legend</h4>"

    for date, color in color_map.items():
        legend_html += f"<p style='margin-left: 10px;'><mark style='background-color: {color}; opacity: 0.7;'></mark>&emsp;{date.strftime('%Y-%m-%d')}</p>"
    legend_html += '</div>'

    # Add the legend to the map
    legend = folium.Marker(
        [initial_latitude, initial_longitude],
        icon=folium.DivIcon(html=legend_html)
    )
    m.add_child(legend)

    # Save the map to an HTML file
    file_path = os.path.join(myfiles_path, 'map.html')
    m.save(file_path)
    webbrowser.open(file_path)
create_map()
