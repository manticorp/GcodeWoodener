#!/usr/bin/env python

""" Adds woodgrain to a gcode file using woodfill filament by varying the temperature over layers"""

from os import path
import sys
from math import floor
import argparse
import random
import re
import base64
from io import BytesIO

# importing the module tkinter
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

__author__ = "Harry Mustoe-Playfair"
__copyright__ = "Copyright 2022"
__credits__ = ["Harry Mustoe-Playfair"]
__license__ = "CC0"
__version__ = "0.1.0"
__maintainer__ = "Harry Mustoe-Playfair"
__email__ = "harry.mustoeplayfair@gmail.com"
__status__ = "Beta"

woodgrainedMarker = ";HAS_BEEN_WOODGRAINED"
eol = "\n"
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")
    return path.join(base_path, relative_path)

class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class GcodeError(Exception):
    pass

class GcodeEmptyError(GcodeError):
    pass

class GcodeNoLayersError(GcodeError):
    pass

class GcodeAlreadyWoodifiedError(GcodeError):
    pass

class Application(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        window_width = 600
        window_height = 400
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.log = []
        self.thumbnailImage = None
        self.master.title('GCode Woodgrainer')
        self.master.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        try:
            ico = 'logo-icon-150x150.ico'
            self.master.iconbitmap(resource_path(ico))
        except Exception:
            pass
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.grid(sticky=tk.N+tk.E+tk.S+tk.W)
        self.createWidgets()

    def createWidgets(self):
        # Set up the frames
        self.topframe = ttk.Frame(self.master, padding="6 12 6 12")
        self.topframe.grid(column=0, row=0, sticky=tk.N+tk.E+tk.S+tk.W)

        self.buttonframe = ttk.Frame(self.topframe, padding="5 0 5 0")
        self.buttonframe.grid(column=0, row=0, sticky=tk.W+tk.E)

        self.inputframe = ttk.Frame(self.topframe, padding="5 0 5 0")
        self.inputframe.grid(column=0, row=1, sticky=tk.W+tk.E)


        self.outputframe = ttk.Frame(self.master, padding="6 12 6 12")
        self.outputframe.grid(column=0, row=1, sticky=tk.N+tk.E+tk.S+tk.W)
        self.outputframe.grid_rowconfigure(99, weight=1)
        self.outputframe.grid_columnconfigure(1, weight=1)

        # Buttons
        self.fileChooserButton = ttk.Button(self.buttonframe, text='Open',
            command=self.chooseFileAndPreview)
        self.fileChooserButton.grid(column=1, row=0)

        self.saveButton = ttk.Button(self.buttonframe, text='Save',
            command=self.runProcess, state=tk.DISABLED)
        self.saveButton.grid(column=2, row=0, padx="5")

        self.quitButton = ttk.Button(self.buttonframe, text='Quit',
            command=self.quit)
        self.quitButton.grid(column=99, row=0)


        # Inputs
        self.minTempLabel = ttk.Label(self.inputframe, padding="0 5 0 0", text="Min Temp *C", justify=tk.LEFT)
        self.minTempLabel.grid(column=0, row=0, sticky=tk.W)
        self.minTemp = tk.DoubleVar(value=200);
        self.minTempBox = ttk.Entry(self.inputframe, width=15, justify=tk.RIGHT, textvariable = self.minTemp)
        self.minTempBox.grid(column=0, row=1, sticky=tk.W)
        helptext = "The maximum allowable temperature value"
        CreateToolTip(self.minTempLabel, helptext)
        CreateToolTip(self.minTempBox, helptext)

        self.maxTempLabel = ttk.Label(self.inputframe, padding="0 5 0 0", text="Max Temp *C", justify=tk.LEFT)
        self.maxTempLabel.grid(column=1, row=0, sticky=tk.W)
        self.maxTemp = tk.DoubleVar(value=240)
        self.maxTempBox = ttk.Entry(self.inputframe, width=15, justify=tk.RIGHT, textvariable = self.maxTemp)
        self.maxTempBox.grid(column=1, row=1, sticky=tk.W)
        helptext = "The maximum allowable temperature value"
        CreateToolTip(self.maxTempLabel, helptext)
        CreateToolTip(self.maxTempBox, helptext)

        self.stepTempLabel = ttk.Label(self.inputframe, padding="0 5 0 0", text="Temp Step *C", justify=tk.LEFT)
        self.stepTempLabel.grid(column=2, row=0, sticky=tk.W)
        self.stepTemp = tk.DoubleVar(value=5)
        self.stepTempBox = ttk.Entry(self.inputframe, width=15, justify=tk.RIGHT, textvariable = self.stepTemp)
        self.stepTempBox.grid(column=2, row=1, sticky=tk.W)
        helptext  = "The step between each temperature range."+eol
        helptext += "For example, if min = 200, max = 220, step = 5 then the possible "
        helptext += "values for layer temps are 200, 205, 210, 215 and 220"
        CreateToolTip(self.stepTempLabel, helptext)
        CreateToolTip(self.stepTempBox, helptext)

        self.numLayersPerTempLabel = ttk.Label(self.inputframe, padding="0 5 0 0", text="Num Layers Per Temp", justify=tk.LEFT)
        self.numLayersPerTempLabel.grid(column=3, row=0, sticky=tk.W)
        self.numLayersPerTemp = tk.IntVar(value=2)
        self.numLayersPerTempBox = ttk.Entry(self.inputframe, width=20, justify=tk.RIGHT, textvariable = self.numLayersPerTemp)
        self.numLayersPerTempBox.grid(column=3, row=1, sticky=tk.W)
        helptext = "This controls the number of layers that each temperature change sticks around for"
        CreateToolTip(self.numLayersPerTempLabel, helptext)
        CreateToolTip(self.numLayersPerTempBox, helptext)

        # Output
        curRow = 0
        self.thumbnailLabel = ttk.Label(self.outputframe, text="Thumbnail")
        self.thumbnailLabel.grid(column=0, row=curRow, pady=4, padx=(0,4), sticky=tk.W)
        self.thumbnailValue = tk.Frame(self.outputframe)
        self.thumbnailValue.grid(column=1, row=curRow, pady=4, padx=(0,4), sticky=tk.W)
        curRow +=1

        self.filenameLabel = ttk.Label(self.outputframe, text="File")
        self.filenameLabel.grid(column=0, row=curRow, pady=4, padx=(0,4), sticky=tk.W)
        self.filename = tk.StringVar()
        self.filenameValue = ttk.Entry(self.outputframe,
            state='readonly',
            width=64,
            textvariable=self.filename)
        self.filenameValue.grid(column=1, row=curRow, sticky=tk.W+tk.E)
        curRow +=1

        self.numLinesLabel = ttk.Label(self.outputframe, text="Lines")
        self.numLinesLabel.grid(column=0, row=curRow, pady=4, padx=(0,4), sticky=tk.W)
        self.numLines = tk.IntVar()
        self.numLinesValue = ttk.Entry(self.outputframe,
            state='readonly',
            width=64,
            textvariable=self.numLines)
        self.numLinesValue.grid(column=1, row=curRow, sticky=tk.W+tk.E)
        curRow +=1

        self.numLayersLabel = ttk.Label(self.outputframe, text="Layers")
        self.numLayersLabel.grid(column=0, row=curRow, pady=4, padx=(0,4), sticky=tk.W)
        self.numLayers = tk.IntVar()
        self.numLayersValue = ttk.Entry(self.outputframe,
            state='readonly',
            width=64,
            textvariable=self.numLayers)
        self.numLayersValue.grid(column=1, row=curRow, sticky=tk.W+tk.E)
        curRow +=1

        self.processingStatusLabel = ttk.Label(self.outputframe, text="Status")
        self.processingStatusLabel.grid(column=0, row=99, pady=4, padx=(0,4), sticky=tk.W+tk.N)
        self.processingStatus = tk.StringVar()
        self.processingStatusValue = ScrolledText(self.outputframe, width=64, height=12)
        self.processingStatusValue.grid(column=1, row=99, sticky=tk.W+tk.E+tk.S+tk.N)

    # Logs a line to the processing status box
    def logLine(self, line):
        if args.verbose:
            print(line)
        self.log.append(line)
        self.processingStatusValue.delete('1.0', tk.END)
        self.processingStatusValue.insert("1.0", eol.join(self.log))

    # Clears the processing status box
    def logClear(self):
        self.log.clear()
        self.processingStatusValue.delete('1.0', tk.END)

    # Show a file chooser and preview the file
    def chooseFileAndPreview(self):
        self.logClear()
        if self.thumbnailImage:
            self.thumbnailImage.grid_forget()
            self.thumbnailImage = None
        filetypes = (
            ('gcode files', ('*.g','*.gcode', '*.gc')),
            ('All files', '*.*')
        )
        if args.verbose:
            print("Choosing file")
        file = fd.askopenfilename(title="Choose a GCODE file to process", filetypes=filetypes)
        return self.setFileAndPreview(file)

    # Set a file name and preview the file
    def setFileAndPreview(self, file):
        self.file = file
        self.filename.set(path.basename(self.file))
        if self.file and path.isfile(self.file):
            self.activeFile = open(self.file, 'r')
            if self.activeFile is not None:
                self.previewFile()
                try:
                    self.checkFileValidity()
                    self.activateSaveButtons()
                    self.logLine('File read and analysed')
                except GcodeError as inst:
                    self.deactivateSaveButtons()
                    self.logLine('%s' % inst)
                except Exception as inst:
                    self.deactivateSaveButtons()
                    self.logLine('An unknown error occurred: ' + inst)

    # "Preview" the current file
    # @TODO upgrade preview functionality
    def previewFile(self):
        self.numLayersInFile = 0
        self.numLinesInFile = 0
        self.activeFileContents = self.activeFile.readlines()
        self.thumbnail = '';
        inThumb = False
        for line in self.activeFileContents:
            self.numLinesInFile += 1
            if '; thumbnail end' in line:
                inThumb = False
            if inThumb:
                self.thumbnail += (re.sub(r"^; ", "", line)).strip()
            if '; thumbnail begin' in line:
                inThumb = True
            if isLayerChangeLine(line):
                self.numLayersInFile += 1

        if args.verbose:
            print('Num layers: %d, num lines: %d' % (self.numLayersInFile, self.numLinesInFile))

        if self.thumbnail:
            thumb = Image.open(BytesIO(base64.b64decode(self.thumbnail)))
            im = ImageTk.PhotoImage(image=thumb);
            self.thumbnailImage = tk.Label(self.thumbnailValue, image=im)
            self.thumbnailImage.image = im
            self.thumbnailImage.grid()

        self.numLines.set(self.numLinesInFile)
        self.numLayers.set(self.numLayersInFile)
        return

    # Turns on the save button
    def activateSaveButtons(self):
        self.saveButton['state'] = tk.NORMAL
        return

    # Turns off the save button
    def deactivateSaveButtons(self):
        self.saveButton['state'] = tk.DISABLED
        return

    # Checks if file is valid for processing
    def checkFileValidity(self):
        if self.numLinesInFile <= 1:
            raise GcodeEmptyError("Num lines in file <=1 (had %d)" % (self.numLinesInFile))
        if self.numLayersInFile <= 1:
            raise GcodeNoLayersError("Num layers in file <=1 (had %d)" % (self.numLayersInFile))
        for line in self.activeFileContents:
            if isWoodgrainedAlreadyLine(line):
                raise GcodeAlreadyWoodifiedError("File has already been woodgrained by us!")
        return True

    def runProcess(self):
        parts = path.splitext(path.basename(self.file))
        nfn = "%s_WOODGRAINED.gcode" % (parts[0])
        f = fd.asksaveasfile(initialdir=path.dirname(self.file),
            initialfile=nfn,
            filetypes=(("GCode", "*.gcode"), ("all files", "*.*")),
            mode='w',
            defaultextension=".gcode")
        if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
            return

        result = processLines(
            self.activeFileContents,
            self.minTemp.get(),
            self.maxTemp.get(),
            self.stepTemp.get(),
            self.numLayersPerTemp.get())

        self.logLine("%d lines processed, %d layers, %d temperature changes" % (result['numlines'], result['numlayers'], result['numtempchanges']))

        f.writelines(result['lines'])
        self.logLine('File saved')
        f.close()

        return

def fileHasBeenWoodGrained(contents):
    for line in contents:
        if woodgrainedMarker in line:
            return True
    return False

def isWoodgrainedAlreadyLine(line):
    return woodgrainedMarker in line

def isLayerChangeLine(line):
    if re.search(r'; *(BEFORE_LAYER_CHANGE|LAYER:|WOODGRAIN_INSERT_LAYER)', line):
        return True
    else:
        return False

def getTemp(min, max, step):
    return floor(random.randint(min, max)/step)*step

def processLines(lines, mintemp, maxtemp, step, linespertemp):
    curLines = 0
    lineNum = 0
    numLayers = 0
    tempChanges = 0
    newlines = lines.copy()
    for line in newlines:
        if isWoodgrainedAlreadyLine(line):
            raise GcodeAlreadyWoodifiedError('File has already been woodgrained')
        lineNum = lineNum+1
        if isLayerChangeLine(line):
            if curLines >= linespertemp:
                curTemp = getTemp(mintemp, maxtemp, step)
                if args.verbose:
                    print("Processing line %d with temp %d" % (lineNum, curTemp))
                newlines.insert(lineNum, ("M104 S%d ;WOODGRAIN_TEMP"+eol) % (curTemp))
                tempChanges = tempChanges + 1;
                curLines = 0
            curLines = curLines + 1
            numLayers = numLayers + 1;
    newlines.insert(0, woodgrainedMarker+eol)
    if args.verbose:
        print("Processing finished - %d temperature changes over %d layers" % (tempChanges, numLayers))
    return {'lines':newlines, 'numlines': lineNum, 'numlayers':numLayers, 'numtempchanges':tempChanges}

def runGui(args):
    app = Application(tk.Tk())
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    finally:
        app.mainloop()
    return 1

def runCmd(args):
    if not args.filename:
        raise Exception('Filename is required if running on command line - no file given')
        exit(1)

    if args.verbose:
        print("Processing %s with min temp of %d and a max temp of %d" % (args.filename, args.mintemp, args.maxtemp))

    with open(args.filename, "r") as f:
        contents = f.readlines()
        if args.verbose:
            print("File has %d lines" % (len(contents)))

    result = processLines(contents, args.mintemp, args.maxtemp, args.step, args.numlayers)
    contents = result['lines']

    fn = args.outname

    if not fn:
        fn = args.filename

    with open(fn, "w") as f:
        contents = "".join(contents)
        f.write(contents)
    return 1

def main(args):
    if (args.commandline):
        return runCmd(args)
    else:
        return runGui(args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog = 'Gcode Woodgrainer',
                        description = 'Adds woodgrain to a gcode file using woodfill filament by varying the temperature randomly over layers')

    parser.add_argument('filename', nargs='?') # positional argument
    parser.add_argument('-o', '--outname', help='Output filename - defaults to input filename')
    parser.add_argument('-t', '--maxtemp', type=float, help='Maximum temperature', default=240)
    parser.add_argument('-b', '--mintemp', type=float, help='Minimum temperature', default=200)
    parser.add_argument('-s', '--step', type=float, help='Temperature step size, e.g if 5, possible temps are 200, 205, 210, 215 etc', default=2.5)
    parser.add_argument('-n', '--numlayers', type=int, help='How many layers per temp change', default=2)
    parser.add_argument('-c', '--commandline', action='store_true', help='Command line only version (headless, no gui)')
    parser.add_argument('-x', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    args = parser.parse_args()
    main(args)