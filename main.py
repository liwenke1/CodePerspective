import os
import json
import logging
import csv

from feature import FileParser

logging.basicConfig(filename='parse.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def parseSingleJavaFile(path):
    parser = FileParser()
    return parser.parse(path)


def extractAllJavaFilePath(personPath):
    JavaFilePath = []
    fileNameList = os.listdir(personPath)
    for fileName in fileNameList:
        filePath = os.path.join(personPath, fileName)
        if os.path.isdir(filePath):
            JavaFilePath.extend(extractAllJavaFilePath(filePath))
        else:
            JavaFilePath.append(filePath)

    return JavaFilePath


def parseFeatureOfPersion(personPath):
    personFeature = {
        'personName': personPath.split('/')[-1],
        'items': []
    }
    
    logging.info('Person {name} Start'.format(name=personFeature['personName']))

    filePathList = extractAllJavaFilePath(personPath)
    for filePath in filePathList:

        logging.info('{Path} Start'.format(Path=filePath))
        
        codeFeatureList, openness, conscientiousness, extroversion, agreeableness, neuroticism = parseSingleJavaFile(filePath)
        personFeature['items'].append({
            'fileName': filePath.split('/')[-1],
            'codeFeature': {
                'newUsageRate': codeFeatureList[0],
                'safetyUsageRate': codeFeatureList[1],
                'commentRate': codeFeatureList[2],
                'longFunctionRate': codeFeatureList[3],
                'localVariableVarience': codeFeatureList[4],
                'englishLevel': codeFeatureList[5],
                'normalNamingRate': codeFeatureList[6],
                'lambdaFunctionCallMethodRate': codeFeatureList[7],
                'roughExceptionRate': codeFeatureList[8]
            },
            'psychologicalFeature': {
                'openness': openness,
                'conscientiousness': conscientiousness,
                'extroversion': extroversion,
                'agreeableness': agreeableness,
                'neuroticism': neuroticism
            }  
        })

        logging.info('{Path} Finish'.format(Path=filePath))
        
    logging.info('Person {name} Finish'.format(name=personFeature['personName']))
    return personFeature


def parseJavaProjectPersonFeatureJson(parser):
    projectPath = 'dataset/Java/java40/'
    projectFeature = {
        'projectPath': projectPath,
        'language': 'java',
        'items': []
    }

    personList = os.listdir(projectPath)
    for person in personList:
        personPath = os.path.join(projectPath, person)
        projectFeature['items'].append(parseFeatureOfPersion(parser, personPath))
        
    with open('report/PersonFeatureOfJava.json', 'w') as wp:
        json.dump(projectFeature, wp, indent=4)


def parseJavaProjectFeatureCsv():
    projectPath = 'dataset/Java/java40/'
    header = ['personName', 'fileName', 'newUsageRate', 'safetyUsageRate', 'commentRate',
              'longFunctionRate', 'localVariableVarience', 'englishLevel', 'normalNamingRate',
              'functionCallMethodRate', 'roughExceptionRate', 'openness', 'conscientiousness',
              'extroversion', 'agreeableness', 'neuroticism']
    with open('report/FeatureOfJavaProject.csv', 'w') as csvFile:
        csvWriter = csv.DictWriter(csvFile, fieldnames=header)
        csvWriter.writeheader()

        personList = os.listdir(projectPath)
        for person in personList:
            personPath = os.path.join(projectPath, person)
            personFeature = parseFeatureOfPersion(personPath)
            for item in personFeature['items']:
                csvWriter.writerow({
                    'personName': personFeature['personName'],
                    'fileName': item['fileName'],
                    'newUsageRate': item['codeFeature']['newUsageRate'],
                    'safetyUsageRate': item['codeFeature']['safetyUsageRate'],
                    'commentRate': item['codeFeature']['commentRate'],
                    'longFunctionRate': item['codeFeature']['longFunctionRate'],
                    'localVariableVarience': item['codeFeature']['localVariableVarience'],
                    'englishLevel': item['codeFeature']['englishLevel'],
                    'normalNamingRate': item['codeFeature']['normalNamingRate'],
                    'lambdaFunctionCallMethodRate': item['codeFeature']['lambdaFunctionCallMethodRate'],
                    'roughExceptionRate': item['codeFeature']['roughExceptionRate'],
                    'openness': item['psychologicalFeature']['openness'],
                    'conscientiousness': item['psychologicalFeature']['conscientiousness'],
                    'extroversion': item['psychologicalFeature']['extroversion'],
                    'agreeableness': item['psychologicalFeature']['agreeableness'],
                    'neuroticism': item['psychologicalFeature']['neuroticism']
                })

if __name__ == '__main__':
    parseJavaProjectFeatureCsv()
    # parser = FileParser()
    # parser.parse('dataset/Java/java40/andengineexamples/andengineexamples/RectangleExample.java')