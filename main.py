import os
import logging

from feature import PersonParser

logging.basicConfig(filename='parse.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def extractAllPersonPath(projectPath):
    personPathList= []
    personNameList = os.listdir(projectPath)
    for personName in personNameList:
        personPathList.append(os.path.join(projectPath, personName))

    return personPathList


def extractAllPersonFeature():
    logging.info('----------Start')
    projectPath = 'dataset/Java/java40/'
    outDir = 'report/'
    personParser = PersonParser()

    personPathList = extractAllPersonPath(projectPath)
    for personPath in personPathList:
        personParser.outputPersonFeatureToJson(personPath, outDir)
        logging.info('{personPath} is Finished'.format(personPath=personPath))

    logging.info('----------End')


def main():
    extractAllPersonFeature()


if __name__ == '__main__':
    main()