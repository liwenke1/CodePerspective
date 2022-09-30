import os
import json


from .FileParser import FileParser


class PersonParser():

    def __init__(self):
        pass


    def extractAllJavaFilePath(self, inputPath):
        javaFilePath = []
        fileNameList = os.listdir(inputPath)
        for fileName in fileNameList:
            filePath = os.path.join(inputPath, fileName)
            if os.path.isdir(filePath):
                javaFilePath.extend(self.extractAllJavaFilePath(filePath))
            elif filePath.endswith('.java'):
                javaFilePath.append(filePath)

        return javaFilePath

    
    def parseSingleFile(self, filePath):
        fileParser = FileParser()
        return fileParser.parseFile(filePath)


    def parseFileOfPerson(self, personPath):
        filePathList = self.extractAllJavaFilePath(personPath)

        personFeature = {
            'PersonName': personPath.split('/')[-1],
            'PersonPath': personPath,
            'FileFeatures': list()
        }
        for filePath in filePathList:
            personFeature['FileFeatures'].append(self.parseSingleFile(filePath))
        
        return personFeature


    def outputPersonFeatureToJson(self, personPath, outDir):
        personFeature = self.parseFileOfPerson(personPath)
        outFileName = personFeature['PersonName']
        outFilePath = os.path.join(outDir, outFileName)

        if os.path.exists(outFilePath):
            return

        with open(outFilePath, 'w') as wp:
            json.dump(personFeature, wp, indent=4)
