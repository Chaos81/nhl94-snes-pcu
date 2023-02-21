# """ Program updates Player Card pointers for Classic ROM players in a custom ROM"""
# """ Version 0.1 """
# Version History
# 0.1 - Original Python version with GUI

from tkinter import Tk, Menu, PhotoImage, BOTH
from tkinter.ttk import Frame, Button, Label
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showinfo, showerror

import sys
from binascii import b2a_hex, unhexlify
import csv
import os
from shutil import copyfile
import struct
from typing import Text
import random

class PCU(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)

        self.parent = parent

        # Instance Variables
        self.bg_image = ""
        self.head_offset = 0  # Header Offset
        self.ROMfile = 'No ROM loaded.'
        self.tempROMFile = 'temp.smc'
        self.pointerFile = 'Player_Card_Pointers.csv'
        self.romLoaded = False
        self.rosterList = []
        self.pointerDict = dict()

        self.initUI()

    def initUI(self):

        self.parent.title("SNES NHL '94 PCU v0.1")
        self.pack(fill=BOTH, expand=1)

        # Menu
        menubar = Menu(self.parent)
        self.parent.config(menu=menubar)

        fileMenu = Menu(menubar, tearoff=0)
        fileMenu.add_command(label="Select ROM...", command=self.loadROM)
        fileMenu.add_command(label="Update Player Cards...", command=self.updateCards)
        fileMenu.add_command(label="Exit", command=sys.exit)
        menubar.add_cascade(label="File", menu=fileMenu)

        helpMenu = Menu(menubar, tearoff=0)
        helpMenu.add_command(label="Instructions...", command=self.inst)

        helpMenu.add_command(label="About...", command=self.about)
        menubar.add_cascade(label="Help", menu=helpMenu)

        # Background Image
        image = self.find_data_file('nhl94.gif')
        self.bg_image = PhotoImage(file=image)
        bg_label = Label(self, image=self.bg_image)
        bg_label.grid(row=0, column=0, padx=135, pady=20, columnspan=2)
        # Buttons
        self.loadROM_button = Button(self, text="Select ROM", command=self.loadROM)
        self.loadROM_button.grid(row=1, column=0)
        self.updateCards_button = Button(self, text="Update Player Cards", command=self.updateCards)
        self.updateCards_button['state'] = "disabled"
        self.updateCards_button.grid(row=1, column=1)
        # Text Display
        self.selectedROM = Label(self, text='No ROM loaded.')
        self.selectedROM.config(text = 'No ROM loaded.')
        self.selectedROM.grid(row=2, padx=30, pady=20, columnspan=2)

    def find_data_file(self, filename):
        if getattr(sys, "frozen", False):
            # The application is frozen.
            datadir = os.path.dirname(sys.executable)
        else:
            # The application is not frozen.
            datadir = os.path.dirname(__file__)

        return os.path.join(datadir, filename)

    def inst(self):

        showinfo("SNES NHL '94 Player Card Updater",
                "This tool will update the player cards in a custom roster ROM. In a custom roster ROM, the players are usually not "
                "on their original teams, and when the player cards are shown, they are incorrect as they correspond to the original Classic "
                "ROM player on that team and in that position. This tool will rearrange the Player Card pointers so that the correct Player "
                "Card is shown for each player. If there is a player in the ROM that was not originally in the Classic 94 ROM, they will "
                "be given a generic Player Card.\n\nTo use the tool, load the ROM that you would like to correct the Player Cards for. Then, "
                "hit the Update Player Cards button, and the tool will ask you where to save the modified ROM to. Choose a location, "
                "and it will change the Player Card pointer table to display the correct cards, and save a new copy of the ROM to the "
                "location specified. If there are any errors, the tool will pop up with an error message.")


    def about(self):

        showinfo("About SNES 94 PCU", "SNES 94 Player Carad Updater ver. 0.1\n\nCreated by chaos\n\nIf there are any bugs "
                                           "or questions, please email me at chaos@nhl94.com")

    def checkhead(self, f):

        # Checks for SMC header and creates offset if needed
        # Checks for ROM Name in ROM Header at 32704 (7FC0) - NHL '94 (4E 48 4C 20 27 39 34)
        # Header is size 512 bytes (200 hex)

        f.seek(32704)
        name = f.read(7).hex()      # New function as of Python 3.5, no need to use b2a_hex anymore
        # name = b2a_hex(f.read(7)).decode("utf-8")

        print(name)

        if name == "4e484c20273934":
            self.head_offset = 0
            print('Headerless')
        else:
            self.head_offset = 512
            print('Headered')

    def cleanup(self):
        # Clean up operations to allow another ROM to be modified
        
        self.selectedROM.config(text = 'No ROM loaded.')
        self.updateCards_button['state'] = "disabled"
        
    def lit_to_big(self, little):
        # Change byte string from little to big endian
        
        return little[2:4] + little[0:2]

    def check_csv(self, reader):
        # Check CSV to make sure there are no missing fields for each entry

        for row in reader:
            if any(val in ("") for val in row.values()):
                return False
        return 1

    def tm_ptrs(self, f):
        # Retrieve Team Offset Pointers

        # Check for Header
        self.checkhead(f)

        # Team Offset Start Position - 927207 - Headerless, 927719 Headered
        f.seek(927207 + self.head_offset)

        ptrarray = []

        for i in range(0, 28):  # Currently hard coded for 28 teams
            firsttm = b2a_hex(f.read(2))
            f.seek(2, 1)

            conv = self.lit_to_big(firsttm)

            # If needed, add header offset
            if self.head_offset == 512:
                data = int(conv, 16) + int('0x0D8200', 16)
            else:
                data = int(conv, 16) + int('0x0D8000', 16)

            print(data)
            ptrarray.append(data)

        return ptrarray

    def get_team_info(self, f, ptr):
        # Retrieve Team info, including data offsets, player data space, team name stuff 

        # Player Data Offset - Default is 55 00 (85 bytes), but in some custom ROMs, may be different
        f.seek(ptr)
        plpos = self.lit_to_big(b2a_hex(f.read(2)))
        ploff = int(plpos, 16)

        # Team Data Offset - Team Offset + 4 bytes
        f.seek(ptr + 4)
        tmpos = self.lit_to_big(b2a_hex(f.read(2)))
        dataoff = ptr + int(tmpos, 16)

        # Calculate Player Data Space
        # Team Data Offset - Player Data Offset - 2 (last 2 bytes of Player Data 02 00)
        plsize = int(tmpos, 16) - ploff - 2

        # Team Name Data starts at the end of Player Data (offset given at bytes 4 and 5 in Team Data)
        # First offset: Length of Team City (including this byte)
        # AA 00 TEAM CITY BB 00 TEAM ABV CC 00 TEAM NICKNAME DD 00 TEAM ARENA
        # AA - Length of Team City (includes AA and 00)
        # BB - Length of Team Abv (includes BB and 00)
        # CC - Length of Team Nickname (includes CC and 00)
        # DD - Length of Team Arena (includes DD and 00)
        # All Name Data is in ASCII format.

        # Read Team City
        f.seek(dataoff)
        tml = int(self.lit_to_big(b2a_hex(f.read(1))), 16)
        # Skip 00
        f.seek(1, 1)
        tmcity = f.read(tml - 2).decode("utf-8")

        # Read Team Abv
        tml = int(self.lit_to_big(b2a_hex(f.read(1))), 16)
        f.seek(1, 1)
        tmabv = f.read(tml - 2).decode("utf-8")

        # Read Team Nickname
        tml = int(self.lit_to_big(b2a_hex(f.read(1))), 16)
        f.seek(1, 1)
        tmnm = f.read(tml - 2).decode("utf-8")

        return dict(city=tmcity, abv=tmabv, name=tmnm, plspace=plsize, ploff=ploff)

    def get_player_info(self, f, ptr, tminfo, teampos):
        # Retreive Player Info

        # Player Data Starts 85 bytes (0x55) from Start offset (may be different in custom ROM)

        # XX 00 "PLAYER NAME" XX 123456789ABCDE

        # XX =	"Player name length" + 2 (the two bytes in front of the name) in hex.
        # 00 =	Null (Nothing)

        # "PLAYER NAME"

        # XX =	Jersey # (decimal)

        # 1 = Weight
        # 2 = Agility

        # 3 = Speed
        # 4 = Off. Aware.

        # 5 = Def. Aware.
        # 6 = Shot Power/Puck Control

        # 7 = Checking
        # 8 = Stick Hand (Uneven = Right. Even = Left. 0/1 will do.)

        # 9 = Stick Handling
        # A = Shot Accuracy

        # B = Endurance/StR
        # C = ? (Roughness on Genesis)/StL

        # D = Passing/GlR
        # E = Aggression/GlL

        # Calculate # of Players - Goalies First, then F and D

        f.seek(ptr + 19)
        gdata = b2a_hex(f.read(2)).decode("utf-8")
        numg = gdata.find("0")
        f.seek(ptr + 17)

        pdata = b2a_hex(f.read(1))
        numf = int(pdata[0:1], 16)
        numd = int(pdata[1:2], 16)

        nump = numg + numf + numd

        # Move to Player Data - we only need the name and position of each player, so everything else is skipped

        f.seek(ptr + tminfo['ploff'])

        # Create list of players on the roster
        pllist = []

        for i in range(1, nump + 1):
            # Name
            pnl = int(b2a_hex(f.read(1)), 16)
            
            # Skip 00
            f.seek(1, 1)

            name = f.read(pnl - 2).decode("utf-8")
            # print(name)

            # Skip over the rest of this player's data
            f.seek(8, 1)

            # G, F or D?

            if i <= numg:
                pos = 'G'
            elif i <= (numg + numf):
                pos = 'F'
            else:
                pos = 'D'

            # Store name and pos in list
            player = [name, pos]
            pllist.append(player)

        return pllist

    def loadROM(self):
        # Loads ROM and makes a temporary copy of it

        ftypes = [("'94 ROM Files", '*.smc')]
        home = os.path.expanduser('~')
        file = askopenfilename(title="Please choose a '94 ROM file...", filetypes=ftypes, initialdir=home)
        if file != '':
            try:
                # Make sure you can open file
                with open(file, 'rb') as f:

                    # Copy ROM to a temp file
                    copyfile(file, self.tempROMFile)

                    # Update text display, enable updateCards button
                    
                    self.selectedROM.config(text = file + ' loaded.')
                    self.updateCards_button['state'] = "normal"

            except IOError:
                    showerror("SNES NHL '94 PCU", "Could not open ROM.  Please check file "
                                                        "permissions.")    

    def readPointerFile(self):
        # Reads Player Card Pointer file and stores in dictionary

        file = self.pointerFile
        # print (file)
        with open(file, 'r', newline='') as csvfile:
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, fieldnames=['Name', 'Pointer'])

            # Check for empty spaces in the file, exit if there are
            check = self.check_csv(reader)
            if not check:
                csvfile.close()
                return 2

            # Read file, insert into dictionary
            csvfile.seek(0)
            for row in reader:
                self.pointerDict[row['Name']] = row['Pointer']
            
            print(self.pointerDict)

        return 1

    def updateCards(self):
        # Updates Player Cards
        # Uses Temp ROM file, and saves to a new location once complete

        # Load ROM file
        file = self.tempROMFile
        with open(file, 'rb+') as f:

            # First, we need to read the Player Card Pointer CSV file and store the data in a dictionary
            check = self.readPointerFile()
            
            if check == 2:
                showerror("SNES NHL '94 PCU", "There is a problem with the pointer CSV file. Please "
                          "check the file and make sure there are no blank entries.")
                return
            
            # Next, retrieve Team Pointers
            tmarray = self.tm_ptrs(f)

            # Next, we need to extract the rosters for each team, and store them in a list. We use a count variable to keep track of teams. Once we have the list
            # of players, we will update the Player Card pointers
            count = 0
            for ptr in tmarray:
                count += 1
                tminfo = self.get_team_info(f, ptr)
                plinfo = self.get_player_info(f, ptr, tminfo, count)
                # print(plinfo)
                self.rosterList.append(plinfo)

            # Update Player Card Pointers - First position is 970067 decimal, or 0xECD53 (Headerless values). Each team has 26 pointer slots, regardless of 
            # how many players there are on the team. We will update the actual players, and pad the rest of the slots with generic card values.
            # Each pointer is 4 bytes, so there are 104 bytes total (26 x 4) for each team. If the player is not found in the CSV file, he will be assigned a 
            # generic card based on his position.
                
            # Set initial pointer position
            ptroffset = 970067 + self.head_offset
            f.seek(ptroffset)

            # Default G and Player cards

            defaultG = '4ec69900'
            defaultP = ['e8e19900', '74fe8f00', '3db19a00']

            for team in self.rosterList:
                count = 0
                for player in team:
                    count += 1
                    if player[0] in self.pointerDict.keys():
                        # Player already has a card, remove spaces from pointer, and write to file
                        ptr = self.pointerDict[player[0]]
                        ptr = ptr.replace(" ","")
                        print (player[0] + " -> " + ptr)
                        f.write(unhexlify(ptr))
                    else:
                        # Player does not have a card, are they G or F/D?
                        pos = player[1]
                        if pos == 'G':
                            f.write(unhexlify(defaultG))
                        else:
                            dptr = random.choice(defaultP)
                            f.write(unhexlify(dptr))

                while count < 26:
                    # Less than 26 players on the team (always the case)
                    count += 1
                    dptr = random.choice(defaultP)
                    print (str(count) + " -> " + dptr)
                    f.write(unhexlify(dptr))
        
        # Save modified ROM to a new file

        home = os.path.expanduser('~')
        try:
            save = asksaveasfilename(title="Please choose a name and location for the new ROM file...",
                                         defaultextension='.smc', initialdir=home)
            copyfile(self.tempROMFile, save)
            showinfo("SNES NHL '94 PCU", "Player Cards have been updated. Updated ROM located at " + save + '.')
        except IOError as e:
            showerror("SNES NHL '94 PCU", "Could not save ROM to location.  Please check folder "
                                                      "permissions.")
        
        self.cleanup()

def main():
    root = Tk()
    ros = PCU(root)

    # Window Setting
    root.geometry("500x300+300+300")
    root.resizable(False, False)
    root.wm_iconbitmap('icon.ico')
    root.mainloop()


if __name__ == '__main__':
    main()