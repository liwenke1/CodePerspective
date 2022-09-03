import json
import re
import numpy as np
from antlr4 import *

from grammer.JavaParser import JavaParser
from grammer.JavaLexer import JavaLexer
from grammer.JavaExtract import JavaExtract


class FileParser():

    def __init__(self):
        self.listener = JavaExtract()
        self.walker = ParseTreeWalker()


    def calaulateUsage(self, code):
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
        
        return newUsageNumber / (newUsageNumber + oldUsageNumber) if newUsageNumber + oldUsageNumber != 0 else 0


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

        identifierList.append(self.listener.classNameList)
        identifierList.extend(self.listener.classVariableNameList)
        for function in self.listener.functionList:
            identifierList.append(function['functionName'])
            for variable in function['localVariableList']:
                identifierList.append(variable['variableName'])
        
        return identifierList


    def calculateEnglishLevelAndNormalRate(self):
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


    def parse(self, file):
        # parse ast
        tokenStream = CommonTokenStream(JavaLexer(InputStream(file)))
        parser = JavaParser(tokenStream)
        self.walker.walk(self.listener, parser.compilationUnit())

        #TODO: extract feature
