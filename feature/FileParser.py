from collections import Counter
import json
import math
import re
import numpy as np
import chardet
from antlr4 import *

from .grammer import JavaParser
from .grammer import JavaLexer
from .grammer import JavaExtract


class FileParser():

    def __init__(self):
        self.listener = JavaExtract()
        self.walker = ParseTreeWalker()


    def calaulateUsage(self, fileData):
        code = ''
        for line in fileData:
            code += line

        # usage after jdk8
        rules_new = [
            r"\-\>", r"\.stream", r"Instant\.", r"LocalDate\.", r"LocalTime\.",
            r"LocalDateTime\.", r"ZonedDateTime\.", r"Period\.",
            r"ZoneOffset\.", r"Clock\.", r"Optional\.", r"var", r"copyOf\(",
            r"ByteArrayOutputStream\(", r"\.transferTo", r"\.isBlank",
            r"\.strip", r"\.stripTrailing", r"\.stripLeading", r"\.repeat",
            r"Pack200\.", r"\"\"\"", r"\@\S+\n\@\S+\n"
        ]
        # abandon usage
        rules_old = [
            r"com\.sun\.awt\.AWTUtilities", r"sun\.misc\.Unsafe\.defineClass",
            r"Thread\.destroy", r"Thread\.stop", r"jdk\.snmp"
        ]
        # safety usage
        rules_safety = [
            r"public final", r"private final", r"SecurityManager",
            r"synchronized", r"volatile", r"ReentrantLock"
        ]

        newUsageNumber = sum([len(re.findall(rule, code)) for rule in rules_new])
        oldUsageNumber = sum([len(re.findall(rule, code)) for rule in rules_old])
        safetyUsageNumber = sum([len(re.findall(rule, code)) for rule in rules_safety])
        
        return newUsageNumber / (newUsageNumber + oldUsageNumber) if newUsageNumber + oldUsageNumber != 0 else None, None


    def extractStringOutput(self, code):
        rules = [
            r'info[(]"(.*?)"[)]',
            r'err[(]"(.*?)"[)]',
            r'error[(]"(.*?)"[)]',
            r'[sS]ystem.err.println[(]"(.*?)"[)];',
            r'[sS]ystem.out.println[(]"(.*?)"[)]',
            r'[sS]ystem.out.printf[(]"(.*?)"[)]',
            r'[sS]ystem.out.print[(]"(.*?)"[)]'
        ]

        stringOutput = []
        for rule in rules:
            stringOutput.extend(re.findall(rule, code))
        
        return stringOutput


    def extractComment(self, tokenStream):
        comment = []

        for token in tokenStream.tokens:
            if token.channel == 4:
                comment.append(token.text)

        return comment


    def calculateCommentRate(self, comment, fileData):
        codeLength = len(fileData)
        return math.log(len(comment) / (codeLength - len(comment)))


    def calculateLongFunctionRate(self):
        if self.listener.functionNumber == 0:
            return None
        
        functionLength = []
        for function in self.listener.functionList:
            functionLength.append(function['functionEndLine'] - function['functionStartLine'] + 1)
        longFunctionNumber = sum(length > 50 for length in functionLength)

        return longFunctionNumber / self.listener.functionNumber


    def calculateVariableLocationVariance(self):
        if self.listener.functionNumber == 0:
            return None

        variableRelativeLocationAfterNorm = []
        for function in self.listener.functionList:
            functionLength = function['functionEndLine'] - function['functionStartLine'] + 1
            for variable in function['localVariableList']:
                variableRelativeLocationAfterNorm.append((variable['Line'] - function['functionStartLine'] + 1) / functionLength)
        
        if len(variableRelativeLocationAfterNorm) == 0:
            return None

        variableVariance = np.std(variableRelativeLocationAfterNorm)
        return variableVariance


    def analyseEnglishLevel(self, wordList):
        if len(wordList) == 0:
            return None

        with open('resources/WordLevel.json') as fp:
            englishDict = json.load(fp)
        
        englishScore = 0
        englishUsageTime = 0
        for word in wordList:
            if word.isalpha() and word in englishDict:
                englishScore += englishDict[word]
                englishUsageTime += 1

        return englishScore / englishUsageTime if englishUsageTime != 0 else 0


    def extractWordAndNamingConvention(self, identifier):
        ''' 
        Support Cammel and UnderScore Naming Convention
        
        Tip: When identifier is only a word, we assume its naming convention is UnderScore
        '''
        
        cammelPattern = re.compile('([a-z0-9]+|[A-Z][a-z0-9]+)((?:[A-Z0-9][a-z0-9]*)*)')
        result = cammelPattern.match(identifier)
        if result:
            wordList = []
            wordList.append(result.group(1))
            for word in re.findall('[A-Z0-9][a-z0-9]*', result.group(2)):
                wordList.append(word)
            return wordList, True
            
        underScorePattern = re.compile('[a-z0-9]+(_[a-z0-9]+)')
        if underScorePattern.match(identifier):
            wordList = identifier.split('_')
            return wordList, True

        return None, False


    def extractAllIdentifier(self):
        identifierList = []

        identifierList.extend(self.listener.classNameList)
        identifierList.extend(self.listener.classVariableNameList)
        for function in self.listener.functionList:
            identifierList.append(function['functionName'])
            for variable in function['localVariableList']:
                identifierList.append(variable['variableName'])
        
        return identifierList


    def calculateEnglishLevelAndNormalNamingRate(self):
        identifierList = self.extractAllIdentifier()

        if len(identifierList) == 0:
            return None, None

        normalIdentifierNumber = 0
        wordList = []
        for identifier in identifierList:
            wordFromIdentifier, isNormal = self.extractWordAndNamingConvention(identifier)
            if isNormal:
                wordList.extend(wordFromIdentifier)
                normalIdentifierNumber += 1
        englishLevel = self.analyseEnglishLevel(wordList)

        return englishLevel, normalIdentifierNumber / len(identifierList)


    def calculateLambdaFunctionCallMethod(self):
        if self.listener.lambdaFunctionNumber + self.listener.functionNumber == 0:
            return None

        return self.listener.lambdaFunctionNumber / (self.listener.lambdaFunctionNumber + self.listener.functionNumber)


    def calculateRoughExceptionRate(self):
        if self.listener.exceptionNumber == 0 :
            return None

        roughExceptNumber = 0
        for exceptName in self.listener.exceptionNameList:
            if exceptName == 'Exception':
                roughExceptNumber += 1

        return roughExceptNumber / self.listener.exceptionNumber


    def calWordFrequency(self, text):
        word = re.split('\s+', text)
        wordFrequency = Counter(word)
        wordTF = {}
        for word, frequency in wordFrequency.items():
            wordTF[word] = frequency/len(word)
        return wordTF


    def calTernaryOperatorRate(self, text):
        return math.log(self.listener.ternaryOperatorNumber / len(text))


    def calTokenRate(self, text):
        token = re.split('[*;\\{\\}\\[\\]()+=\\-&/|%!?:,<>~`\\s\"]', text)
        return math.log(len(token) / len(text))


    def calControlStructureRate(self, text):
        return math.log(self.listener.controlStructureNumber / len(text))
        

    def calLiteralRate(self, text):
        return math.log(self.listener.literalNumber / len(text))


    def calKeywordRate(self, tokenStream, text):
        tokenNumber = 0
        for token in tokenStream.tokens:
            if token.type >= 1 and token.type <= 66:
                tokenNumber += 1
        return math.log(tokenNumber / len(text))


    def calFunctionRate(self, text):
        return math.log(self.listener.functionNumber / len(text))


    def calParamsAvgAndStandardDev(self):
        paramNumeber = []
        for function in self.listener.functionList:
            paramNumeber.append(len(function['functionParams']))
        
        return sum(paramNumeber) / len(paramNumeber), np.std(paramNumeber)


    def calLineLengthAvgAndStandardDev(self, fileData):
        lineLength = [len(line) for line in fileData]
        return sum(lineLength) / len(lineLength), np.std(lineLength)


    def calculateOpenness(self, newUsageRate):
        return newUsageRate


    def calculateConscientiousness(self, safetyUsageRate, normalNamingRate, 
                                   longFunctionRate, commentRate, roughExceptionRate):
        conscientiousness = []

        if safetyUsageRate != None:
            conscientiousness.append(safetyUsageRate)
        
        if normalNamingRate != None:
            conscientiousness.append(normalNamingRate)
        
        if longFunctionRate != None:
            conscientiousness.append(max((1 - 1.3 *longFunctionRate), 0))
        
        if commentRate != None:
            if commentRate < 1/3:
                conscientiousness.append(5/3 * commentRate)
            elif commentRate < 2:
                conscientiousness.append(0.5 + 0.25 * commentRate)
            else:
                conscientiousness.append(max(0.5 - 0.1 * commentRate, 0))
        
        if roughExceptionRate != None:
            conscientiousness.append(1 - roughExceptionRate)
        
        if len(conscientiousness) == 0:
            return None

        return np.mean(conscientiousness)


    def calculateExtroversion(self, commentRate):
        extroversion = []

        if commentRate != None:
            if commentRate < 1/3:
                extroversion.append(5/3 * commentRate)
            elif commentRate < 2:
                extroversion.append(0.5 + 0.25 * commentRate)
            else:
                extroversion.append(max(0.5 - 0.1 * commentRate, 0))

        if len(extroversion) == 0:
            return None

        return np.mean(extroversion)


    def calculateAgreeableness(self, newUsageRate, longFunctionRate, functionCallMethodRate,
                               roughExceptionRate):
        agreeableness = []

        if newUsageRate != None:
            if newUsageRate < 0.5:
                agreeableness.append(0.5 - 0.5 * newUsageRate)
            else:
                agreeableness.append(0.5 + 0.5 * newUsageRate)

        if longFunctionRate != None:
            agreeableness.append(max((1 - 1.3 *longFunctionRate), 0))

        if functionCallMethodRate != None:
            agreeableness.append(1 - 0.5 * functionCallMethodRate)

        if roughExceptionRate != None:
            agreeableness.append(1 - roughExceptionRate)

        if len(agreeableness) == 0:
            return None

        return np.mean(agreeableness)

    def calculateNeuroticism(self, normalNamingRate, localVariableVarience):
        neuroticism = []

        if normalNamingRate != None:
            neuroticism.append(normalNamingRate)

        if localVariableVarience != None:
            neuroticism.append(max(1 - localVariableVarience, 0))

        if len(neuroticism) == 0:
            return None

        return np.mean(neuroticism)


    def parse(self, filePath):
        with open(filePath, 'rb') as fp:
            file = fp.read()
        fileMode = chardet.detect(file)["encoding"]

        with open(filePath, 'r', encoding=fileMode) as fp:
            file = fp.read()

        # parse ast
        tokenStream = CommonTokenStream(JavaLexer(InputStream(file)))
        parser = JavaParser(tokenStream)
        self.walker.walk(self.listener, parser.compilationUnit())

        with open(filePath, 'r', encoding=fileMode) as fp:
            fileData = fp.readlines()

        # extract code features
        newUsageRate, safetyUsageRate = self.calaulateUsage(fileData)
        commentRate = self.calculateCommentRate(self.extractComment(tokenStream), fileData)
        longFunctionRate = self.calculateLongFunctionRate()
        localVariableVarience = self.calculateVariableLocationVariance()
        englishLevel, normalNamingRate = self.calculateEnglishLevelAndNormalNamingRate()
        lambdaFunctionCallMethodRate = self.calculateLambdaFunctionCallMethod()
        roughExceptionRate = self.calculateRoughExceptionRate()

        # calculate psychological features
        openness = self.calculateOpenness(newUsageRate)
        conscientiousness = self.calculateConscientiousness(safetyUsageRate, normalNamingRate, longFunctionRate, 
                                                            commentRate, roughExceptionRate)
        extroversion = self.calculateExtroversion(commentRate)
        agreeableness = self.calculateAgreeableness(newUsageRate, longFunctionRate, lambdaFunctionCallMethodRate,
                                                    roughExceptionRate)
        neuroticism = self.calculateNeuroticism(normalNamingRate, localVariableVarience)

        return [newUsageRate, safetyUsageRate, commentRate, longFunctionRate, localVariableVarience,
                englishLevel, normalNamingRate, lambdaFunctionCallMethodRate, roughExceptionRate], \
                openness, conscientiousness, extroversion, agreeableness, neuroticism
