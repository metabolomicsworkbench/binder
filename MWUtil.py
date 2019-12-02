from __future__ import print_function

import os
import sys
import time
import re
from io import StringIO
import base64

import requests

import pandas as pd
import numpy as np

__all__ = ["CheckAndWarnEmptyStudiesData", "CheckAndWarnEmptyStudiesUIFData", "ListClassInformation", "ListStudiesAnalysisAndResultsData", "RetrieveStudiesAnalysisAndResultsData", "RetrieveUploadedData", "SetupUIFDataForStudiesAnalysisAndResults, SetupCSVDownloadLink"]


def ListStudiesAnalysisAndResultsData(StudiesResultsData, DisplayDataFrame = False, IPythonDisplayFuncRef = None, IPythonHTMLFuncRef = None):
    """List analysis and results data retrieved for studies using
    RetrieveStudiesAnalysisAndResultsData. 
    
    Arguments:
        StudiesResultsData (dict): A dictionary containing retrieved data for 
            analysis and results in specified study ID(s).
        DisplayDataFrame (bool): Flag for displaying data frame using iPython
        IPythonDisplayFuncRef (function): Reference to iPython display function
            for displaying data frame converted into HTML.
        IPythonHTMLFuncRef (function): Reference to iPython HTML function
            for converting dataframe into HTML.

    """
    
    print("\nListing analysis metadata for studies along with datatable for named metabolites...")
    
    if len(StudiesResultsData.keys()) == 0:
        print("No data available")
    
    for StudyID in StudiesResultsData:
        print("")
        for AnalysisID in StudiesResultsData[StudyID]:
            print("\nstudy_id:%s\nanalysis_id:%s" % (StudyID, AnalysisID))
            for DataType in StudiesResultsData[StudyID][AnalysisID]:
                DataValue = StudiesResultsData[StudyID][AnalysisID][DataType]
                if re.match("^(data_frame)$", DataType, re.I):
                    if DisplayDataFrame and IPythonDisplayFuncRef is not None and IPythonHTMLFuncRef is not None:
                        print("data_frame:\n")
                        IPythonDisplayFuncRef(IPythonHTMLFuncRef(DataValue.to_html(max_rows = 10, max_cols = 10)))
                    else:
                        print("data_frame: <Pandas DataFrame available; skipping display>")
                else:
                    print("%s: %s" % (DataType, DataValue))

def RetrieveStudiesAnalysisAndResultsData(StudyIDs, MWBaseURL = "https://www.metabolomicsworkbench.org/rest"):
    """Retrieve analysis and results data for a study ID or list of space
    delimited study IDs. In addition, study substrings are allowed to
    perform fuzzy match.
    
    Arguments:
        StudyIDs (str): Study ID or IDs.
        MWBaseURL (str): REST URL base for MW.

    Returns:
        dict : A dictionary containing retrieved data  for analysis and
            results in specified study ID(s).

    Examples:

        StudiesResultsData = MWUtil.RetrieveStudiesAnalysisAndResultsData(StudyIDs, MWBaseURL)
        if len(StudiesResultsData.keys()) == 0:
             print("No data available")
    
        for StudyID in StudiesResultsData:
            for AnalysisID in StudiesResultsData[StudyID]:
                print("\nstudy_id:%s\nanalysis_id:%s" % (StudyID, AnalysisID))
                for DataType in StudiesResultsData[StudyID][AnalysisID]:
                    DataValue = StudiesResultsData[StudyID][AnalysisID][DataType]
                    if re.match("^(data_frame)$", DataType, re.I):
                        print("data_frame: <Pandas DataFrame available; skipping display>")
                    else:
                        print("%s: %s" % (DataType, DataValue))

    """
    
    StudiesResultsData = {}
    
    StudyIDs = re.sub("[ ]+", " ", StudyIDs)
    
    for StudyID in StudyIDs.split(" "):
        MWDataURL = MWBaseURL + "/study/study_id/" + StudyID + "/analysis/"
        
        print("Initiating request: %s" % MWDataURL)
        Response = requests.get(MWDataURL)
        if Response.status_code != 200:
            print("Request failed: status_code: %d" % Response.status_code)
            continue
        
        AnalysisData = Response.json()
        
        print("Processing analysis data...")
        _ProcessAnalysisData(StudiesResultsData, AnalysisData)
    
    for StudyID in StudiesResultsData:
        for AnalysisID in StudiesResultsData[StudyID]:
            print("\nRetrieving datatable for analysis ID, %s, in study ID, %s..." % (AnalysisID, StudyID))
            
            MWDataURL = MWBaseURL + "/study/analysis_id/" + AnalysisID + "/datatable"
            
            print("Initiating request: %s" % MWDataURL)
            Response = requests.get(MWDataURL)
            if Response.status_code != 200:
                print("***Error: Request failed: status_code: %d" % Response.status_code)
                continue
            
            print("Processing datatable text...")
            Separator = "\t"
            ResultsDataTable, ClassNamesToNumsMap = _ProcessDataTableText(Response.text, Sep = Separator, AddClassNum = True)
            StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"] = ClassNamesToNumsMap
            
            print("Setting up Pandas dataframe...")
            RESULTSDATATABLE = StringIO(ResultsDataTable)
            StudiesResultsData[StudyID][AnalysisID]["data_frame"] = pd.read_csv(RESULTSDATATABLE, sep = Separator, index_col = "Samples")
    
    return StudiesResultsData

def RetrieveUploadedData(UploadedDataInfo):
    """Retrieve data from the uploaded data information available
    from the FileUpload ipywidget.
    
    Arguments:
        UploadedDataInfo: Value of FileUpload ipywidget.

    Returns:
        dict : A dictionary containing retrieved data for uploaded data
            file(s).

    Examples:

        StudiesResultsData = MWUtil.RetrieveUploadedData(UploadedDataInfo)
        if len(StudiesResultsData.keys()) == 0:
             print("No data available")
    
        for StudyID in StudiesResultsData:
            for AnalysisID in StudiesResultsData[StudyID]:
                print("\nstudy_id:%s\nanalysis_id:%s" % (StudyID, AnalysisID))
                for DataType in StudiesResultsData[StudyID][AnalysisID]:
                    DataValue = StudiesResultsData[StudyID][AnalysisID][DataType]
                    if re.match("^(data_frame)$", DataType, re.I):
                        print("data_frame: <Pandas DataFrame available; skipping display>")
                    else:
                        print("%s: %s" % (DataType, DataValue))

    """
    
    print("\nProcessing uploaded data file(s)...")
    
    StudiesResultsData = {}
    
    for FileName, FileDataInfo in UploadedDataInfo.items():
        Name = FileDataInfo["metadata"]["name"]
        Type = FileDataInfo["metadata"]["type"]
        Size = FileDataInfo["metadata"]["size"]
            
        Content = FileDataInfo["content"].decode()
            
        _, FileExt = os.path.splitext(Name)
        if re.match("^(\.txt)|(\.tsv)$", FileExt):
            Separator = "\t"
        else:
            Separator = ","

        print("\nProcessing uploaded data file %s..." % Name)

        StudyID = Name
        AnalysisID = "NA"

        # Intialize data...
        StudiesResultsData[StudyID] = {}
        StudiesResultsData[StudyID][AnalysisID] = {}
        StudiesResultsData[StudyID][AnalysisID]["analysis_summary"] = "NA"
        
        ResultsDataTable, ClassNamesToNumsMap = _ProcessDataTableText(Content, Sep = Separator, NewSampleColName = "Samples", NewClassColName = "Class", AddClassNum = True)
        StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"] = ClassNamesToNumsMap
        
        print("Setting up Pandas dataframe...")
        RESULTSDATATABLE = StringIO(ResultsDataTable)
        StudiesResultsData[StudyID][AnalysisID]["data_frame"] = pd.read_csv(RESULTSDATATABLE, sep = Separator, index_col = "Samples")

    return StudiesResultsData
    
def _ProcessAnalysisData(StudiesResultsData, AnalysisData):
    """Process analysis data retrieved in JSON format for a study or set of studies"""
    
    if "study_id" in AnalysisData:
        # Turn single study with single analysis data set into dictionary
        # with multiple studies/analysis data set...
        AnalysisData = {"1" : AnalysisData}
    
    for DataSetNum in AnalysisData:
        StudyID = AnalysisData[DataSetNum]["study_id"]
        AnalysisID = AnalysisData[DataSetNum]["analysis_id"]
        
        # Intialize data...
        if StudyID not in StudiesResultsData:
            StudiesResultsData[StudyID] = {}
        
        StudiesResultsData[StudyID][AnalysisID] = {}
        
        # Track data...
        for DataType in AnalysisData[DataSetNum]:    
            DataValue = AnalysisData[DataSetNum][DataType]    
            if re.match("^(study_id|analysis_id)$", DataType, re.I):
                continue
            
            StudiesResultsData[StudyID][AnalysisID][DataType] = DataValue

def _ProcessDataTableText(DataTableText, Sep = "\t", NewSampleColName = None, NewClassColName = None, AddClassNum = True):
    """Process datatable retrieved retrieves in text format for a specific analysis ID"""

    DataLines = []

    # Standardize new line char and split lines...
    DataTableText = re.sub("(\r\n)|(\r)", "\n", DataTableText)
    TextLines = DataTableText.split("\n")
    
    # Process data labels...
    LineWords = TextLines[0].split(Sep)
    
    DataLabels = []
    ColLabel = NewSampleColName if NewSampleColName is not None else LineWords[0]
    DataLabels.append(ColLabel)

    ColLabel = NewClassColName if NewClassColName is not None else LineWords[1]
    DataLabels.append(ColLabel)
    
    if AddClassNum:
        DataLabels.append("ClassNum")
    
    for Index in range(2, len(LineWords)):
        Name = LineWords[Index]
        DataLabels.append(Name)
    
    DataLines.append(Sep.join(DataLabels))
    
    # Process data...
    ClassNamesMap = {}
    ClassNum = 0
    for Index in range(1, len(TextLines)):
        LineWords = TextLines[Index].split(Sep)
        
        if len(LineWords) <= 2:
            continue
        
        # Handle sample ID and class name...
        DataLine = []
        DataLine.append(LineWords[0])
        DataLine.append(LineWords[1])
        
        if AddClassNum:
            ClassName = LineWords[1]
            if ClassName not in ClassNamesMap:
                ClassNum += 1
                ClassNamesMap[ClassName] = ClassNum
            DataLine.append("%s" % ClassNamesMap[ClassName])
            
        for Index in range(2, len(LineWords)):
            DataLine.append(LineWords[Index])
        
        DataLines.append(Sep.join(DataLine))
    
    return ("\n".join(DataLines), ClassNamesMap)

def SetupUIFDataForStudiesAnalysisAndResults(StudiesResultsData, MinClassCount = None):
    """Setup data for creating  UIF from analysis and results data for a single
    or multiple studies.
    
    Arguments:
        StudiesResultsData (dict):  A dictionary containing analysis and results
          data for a single or multiple studies.
        MinClassCount (int): Minimum number of classes required in each data set.

    Returns:
        dict : A dictionary containing studies and analysis data for creating UIF.

    """
    
    StudiesUIFData = {}
    StudiesUIFData["StudyIDs"] = []
    StudiesUIFData["AnalysisIDs"] = {}
    StudiesUIFData["MetaboliteIDs"] = {}
    StudiesUIFData["ClassIDs"] = {}
    
    for StudyID in StudiesResultsData:
        NewStudy = True
        
        for AnalysisID in StudiesResultsData[StudyID]:
            if "data_frame" not in StudiesResultsData[StudyID][AnalysisID]:
                print("***Warning: Excluding study ID, %s, analysis ID, %s, from further analysis: No named metabolities data available..." % (StudyID, AnalysisID))
                continue
            
            ResultsDataFrame = StudiesResultsData[StudyID][AnalysisID]["data_frame"]
            ColumnNames = list(ResultsDataFrame.columns.values)
            if len(ColumnNames) <= 3:
                print("***Warning: Excluding study ID, %s, analysis ID, %s, from further analysis: No named metabolities data available..." % (StudyID, AnalysisID))
                continue
            
            if MinClassCount is not None:
                ClassCount = len(StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"])
                if ClassCount < MinClassCount:
                    print("***Warning: Excluding study ID, %s, analysis ID, %s, from further analysis: Contains less than %s classes..." % (StudyID, AnalysisID, MinClassCount))
                    continue
            
            if NewStudy:
                NewStudy = False
                StudiesUIFData["StudyIDs"].append(StudyID)
                StudiesUIFData["AnalysisIDs"][StudyID] = []
                StudiesUIFData["MetaboliteIDs"][StudyID] = {}
                StudiesUIFData["ClassIDs"][StudyID] = {}
            
            StudiesUIFData["AnalysisIDs"][StudyID].append(AnalysisID)
            StudiesUIFData["MetaboliteIDs"][StudyID][AnalysisID] = []
            StudiesUIFData["ClassIDs"][StudyID][AnalysisID] = []
            
            StudiesUIFData["MetaboliteIDs"][StudyID][AnalysisID].extend(ColumnNames[3:])
            StudiesUIFData["ClassIDs"][StudyID][AnalysisID].extend(StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"])
    
    if len(StudiesUIFData["StudyIDs"]) == 0:
        print("***Warning: No studies available for further analysis...")

    return StudiesUIFData

#
# Reference:
# https://stackoverflow.com/questions/31893930/download-csv-from-an-ipython-notebook
#
def SetupCSVDownloadLink(DataFrame, Title = "Download CSV file", CSVFilename = "DataFrameDownload.csv"):  
    """Setup a HTML link for downloading a dataframe as a CSV file.

    Arguments:
        DataFrame (panda): Panda dataframe.
        Title (str): Title for URL.
        CSVFilename (str): Name of a CSV file to download.

    Returns:
        str : A HTML string for downloading dataframe as a CSV file.

    """
    
    CSVData = DataFrame.to_csv()
    Base64EncodedData = base64.b64encode(CSVData.encode()).decode()
    HTMLText = '<a download="%s" href="data:text/csv;base64,%s" target="_blank">%s</a>' % (CSVFilename, Base64EncodedData, Title)
    
    return HTMLText


def CheckAndWarnEmptyStudiesData(StudiesResultsData, RetrievedMWData = True, SpecifiedStudyIDs = None):
    """Check and warn about empty results data.

    Arguments:
        StudiesResultsData (dict): A dictionary containing retrieved data for 
            analysis and results in specified study ID(s).
        RetrievedMWData (bool): Data retrived from MW.
        SpecifiedStudyIDs (str): Specified study IDs.

    """

    if StudiesResultsData is None or len(StudiesResultsData.keys()) == 0:
        if RetrievedMWData:
            print("Failed to retrieve data. Specify valid study ID(s) and click button above without re-running the cell...")
        else:
            print("Failed to upload data. Select valid file(s) and click button above without re-running the cell...")
    else:
        if RetrievedMWData:
            if SpecifiedStudyIDs is None:
                print("Successfully retrieved data for specified study ID(s)...")
            else:
                print("Successfully retrieved data for specified study ID(s): %s" % SpecifiedStudyIDs)
        else:
            print("Successfully uploaded specified data file(s): %s" % (", ".join(StudiesResultsData.keys())))

def CheckAndWarnEmptyStudiesUIFData(StudiesUIFData, RetrievedMWData = True, SpecifiedStudyIDs = None):
    """Check and warn about empty UIF data.

    Arguments:
        StudiesUIFsData (dict): A dictionary containing studies and analysis
            data for creating UIF.
        RetrievedMWData (bool): Data retrived from MW.
        SpecifiedStudyIDs (str): Specified study IDs.

    """
    
    if StudiesUIFData is None or len(StudiesUIFData.keys()) == 0:
        if RetrievedMWData:
            print("Failed to retrieve data containing multiple classes. Specify valid study ID(s) and try again...")
        else:
            print("Failed to retrieve data containing multiple classes. Specify valid data file(s) and try again...")
    else:
        if RetrievedMWData:
            if SpecifiedStudyIDs is None:
                print("Successfully retrieved data for specified study ID(s)...")
            else:
                print("Successfully retrieved data for specified study ID(s): %s" % SpecifiedStudyIDs)
        else:
            print("Successfully uploaded specified data file(s): %s" % (", ".join(StudiesUIFData["StudyIDs"])))

# List class information...
def ListClassInformation(StudiesResultsData, StudyID, AnalysisID, RetrievedMWData = True, ClassNumsColorNamesMap = None):
    """List information for available class names and numbers.
  
    Arguments:
        StudiesResultsData (dict): A dictionary containing retrieved data for 
            analysis and results in specified study ID(s).
        StudyID (str): StudyID or uploaded file name.
        AnalysisID (str): AnalysisID or NA for uploaded file.
        RetrievedMWData (bool): Data retrived from MW.
        ClassNumsColorNamesMap (dict): Class num to color name map.

    """
    
    StudyIDLabel = "StudyID" if RetrievedMWData else "Uploaded File"
    print("%s: %s" % (StudyIDLabel, StudyID))
    
    print("AnalysisID: %s\nAnalysis Summary: %s" % (AnalysisID, StudiesResultsData[StudyID][AnalysisID]["analysis_summary"]))
    
    for ClassName in StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"]:
        ClassNum = StudiesResultsData[StudyID][AnalysisID]["class_names_to_nums"][ClassName]
        
        ClassNumColor = None
        if ClassNumsColorNamesMap is not None:
            if ClassNum in ClassNumsColorNamesMap:
                ClassNumColor = ClassNumsColorNamesMap[ClassNum]
        
        if ClassNumColor is not None:
            print("ClassNum: %s; ClassNumColor: %s\nClassName: %s" % (ClassNum, ClassNumColor, ClassName))
        else:
            print("ClassNum: %s; ClassName: %s" % (ClassNum, ClassName))
