import json
import math
import os
import re
import numpy as np
import chardet
from collections import Counter

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


    def extractComment(self, tokenStream: CommonTokenStream):
        commentList = []

        for token in tokenStream.tokens:
            if token.channel == 4:
                commentList.append(token.text)

        return commentList


    def judgeCommentType(self, comment):
        if comment.startswith('//'):
            return 'SingleLine'
        elif comment.startswith('/**'):
            return 'Documentation'
        elif comment.startswith('//'):
            return 'MultiLine'
        return 'None'


    def calculateCommentRateAndTypeTermFrequency(self, commentList, text):
        if len(commentList) == 0:
            return 0, None

        commentLength = 0
        commentTypeCount = {
            'SingleLine': 0,
            'MultiLine': 0,
            'Documentation': 0,
            'None': 0
        }
        for comment in commentList:
            commentLength += len(comment)
            commentType = self.judgeCommentType(comment)
            commentTypeCount[commentType] += 1

        commentTypeCount.pop('None')
        commentTypeTotalCount = sum(commentTypeCount.values())

        if commentTypeTotalCount == 0:
            return math.log(commentLength / len(text)), None

        commentTypeTermFrequency = {}
        for commentType in commentTypeCount.keys():
            commentTypeTermFrequency[commentType] = commentTypeCount[commentType] / commentTypeTotalCount
        return math.log(commentLength / len(text)), commentTypeTermFrequency


    def calculateFunctionAvgLength(self):
        if self.listener.functionNumber == 0:
            return None
        
        functionLength = []
        for function in self.listener.functionList:
            functionLength.append(function['functionEndLine'] - function['functionStartLine'] + 1)

        return np.average(functionLength)


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


    def IsAWord(self, identifier):
        aWord = re.compile('[a-z0-9]+')
        if aWord.match(identifier):
            return True
        else:
            return False


    def extractWordAccordingToCammel(self, identifier):
        cammelPattern = re.compile('([a-z0-9]+|[A-Z][a-z0-9]+)((?:[A-Z0-9][a-z0-9]*)*)')
        result = cammelPattern.match(identifier)
        if result:
            wordList = []
            wordList.append(result.group(1))
            for word in re.findall('[A-Z0-9][a-z0-9]*', result.group(2)):
                wordList.append(word)
            return wordList, True

        return None, False


    def extractWordAccordingToUnderScore(self, identifier):
        underScorePattern = re.compile('[a-z0-9]+(_[a-z0-9]+)')
        if underScorePattern.match(identifier):
            wordList = identifier.split('_')
            return wordList, True
        
        return None, False


    def extractAllIdentifier(self, tokenStream: CommonTokenStream):
        identifierList = []
        for token in tokenStream.tokens:
            if token.type == 129:
                identifierList.append(token.text)
        
        return identifierList


    def calculateEnglishLevelAndNormalNamingRate(self, tokenStream):
        identifierList = self.extractAllIdentifier(tokenStream)

        if len(identifierList) == 0:
            return None, None, None

        wordList = []
        
        if len(wordList) == 0:
            return None, None, None

        cammelIdentifierNumber = 0
        underScoreIdentifierNumber = 0
        for identifier in identifierList:
            # filter out the identifier which consists of one word
            if self.IsAWord(identifier):
                continue

            wordFromIdentifier, isNormal = self.extractWordAccordingToCammel(identifier)
            if isNormal:
                wordList.extend(wordFromIdentifier)
                cammelIdentifierNumber += 1
                continue

            wordFromIdentifier, isNormal = self.extractWordAccordingToUnderScore(identifier)
            if isNormal:
                wordList.extend(wordFromIdentifier)
                underScoreIdentifierNumber += 1
                continue

        englishLevel = self.analyseEnglishLevel(wordList)

        return englishLevel, cammelIdentifierNumber / len(wordList), underScoreIdentifierNumber / len(wordList)


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


    def calWordTermFrequencyAndCountOfLine(self, fileData):
        word = []
        wordCountOfLine = []
        
        for line in fileData:
            wordOfLine = re.split('\s+', line)
            word.extend(wordOfLine)
            wordCountOfLine.append(len(wordOfLine))
        
        if len(word) == 0:
            return None, None

        wordFrequency = Counter(word)
        wordTotalCount = len(word)
        wordTermFrequency = {}
        for word, frequency in wordFrequency.items():
            wordTermFrequency[word] = frequency / wordTotalCount

        wordCountOfLineFrequency = Counter(wordCountOfLine)

        return wordTermFrequency, wordCountOfLineFrequency


    def calTernaryOperatorRate(self, text):
        ternaryOperatorRate = self.listener.ternaryOperatorNumber / len(text)
        if ternaryOperatorRate == 0:
            return None
        else:
            return math.log(ternaryOperatorRate)


    def calTokenRate(self, text):
        token = re.split('[*;\\{\\}\\[\\]()+=\\-&/|%!?:,<>~`\\s\"]', text)
        tokenRate = len(token) / len(text)
        if tokenRate == 0:
            return None
        else:
            return math.log(tokenRate)


    def calControlStructureRate(self, text):
        controlStructureNumberRate = self.listener.controlStructureNumber / len(text)
        if controlStructureNumberRate == 0:
            return None
        else:
            return math.log(controlStructureNumberRate)
        

    def calLiteralRate(self, text):
        literalNumberRate = self.listener.literalNumber / len(text)
        if literalNumberRate == 0:
            return None
        else:
            return math.log(literalNumberRate)


    def calKeywordRate(self, tokenStream: CommonTokenStream, text):
        tokenNumber = 0
        for token in tokenStream.tokens:
            if token.type >= 1 and token.type <= 66:
                tokenNumber += 1
        tokenNumberRate = tokenNumber / len(text)
        if tokenNumberRate == 0:
            return None
        else:
            return math.log(tokenNumberRate)


    def calFunctionRate(self, text):
        functionNumberTermRate = self.listener.functionNumber / len(text)
        functionNumberRate = math.log(functionNumberTermRate) if functionNumberTermRate != 0 else None
        return functionNumberRate


    def calParamsAvgAndStandardDev(self):
        paramNumeber = []
        for function in self.listener.functionList:
            paramNumeber.append(len(function['functionParams']))
        
        if len(paramNumeber) == 0:
            return 0.0, 0.0

        return sum(paramNumeber) / len(paramNumeber), np.std(paramNumeber)


    def calLineLengthAvgAndStandardDev(self, fileData):
        lineLength = [len(line) for line in fileData]
        lineLengthCount = Counter(lineLength)
        
        return sum(lineLength) / len(lineLength), np.std(lineLength), lineLengthCount


    def calBlanklineRate(self, fileData):
        blankCount = 0
        bufferCount = 0
        leadingFlag = False
        for line in fileData:
            if re.fullmatch('[\s]*', line):
                if leadingFlag:
                    bufferCount += 1
            else:
                blankCount += bufferCount
                bufferCount = 1
                leadingFlag = True

        return math.log(blankCount / len(fileData))


    # return tabRate, spaceRate, and whiteSpaceRate
    def calWhiteSpacesRate(self, text):
        tabTermCount = len(re.findall('\\t', text)) / len(text)
        spaceTermCount = len(re.findall(' ', text)) / len(text)
        newLineTermCount = len(re.findall('\\n', text)) / len(text)

        tabCountRate = math.log(tabTermCount) if tabTermCount != 0 else None
        spaceCountRate = math.log(spaceTermCount) if spaceTermCount != 0 else None
        newLineCountRate = math.log(newLineTermCount) if newLineTermCount != 0 else None

        return tabCountRate, spaceCountRate, newLineCountRate


    # return > 0 : tabIndent majority   
    # return < 0 : spaceIndent majority
    def isTabOrSpaceIndent(self, fileData):
        tabIndent = 0
        spaceIndent = 0
        for line in fileData:
            if line.startswith('\\t'):
                tabIndent += 1
            elif line.startswith(' '):
                spaceIndent += 1

        return tabIndent > spaceIndent


    # return > 0 : newLine majority Before Open Brace
    # return < 0 : OnLine majority Before Open Brace
    def isNewLineOrOnLineBeforeOpenBrance(self, tokenStream: CommonTokenStream):
        newLineCount = 0
        onLineCount = 0
        for token in tokenStream.tokens:
            if token.text != '{':
                continue
            previousLetterIndex = tokenStream.previousTokenOnChannel(token.tokenIndex, 0)
            previousNewLineIndex = tokenStream.previousTokenOnChannel(token.tokenIndex, 2)
            if previousNewLineIndex > previousLetterIndex:
                newLineCount += 1
            elif previousNewLineIndex < previousLetterIndex:
                onLineCount += 1

        return newLineCount > onLineCount


    # Return AST Leaves TF And Keyword TF
    # AST Leaves consist of 130 types
    # java has 65 kinds of keyword
    def calASTLeavesAndKeywordTermFrequency(self, tokenStream: CommonTokenStream):
        ASTLeavesTypeCount = []
        for token in tokenStream.tokens:
            ASTLeavesTypeCount.append(token.type)

        # ASTLeavesCount:
        # index 0 : Unknown
        # index 1-65: keyword
        # index 66-129: operator identifier comment
        ASTLeavesCount = Counter(ASTLeavesTypeCount)

        keywordTotalCount = 0
        for index in ASTLeavesCount.keys():
            if index >= 1 and index <= 65:
                keywordTotalCount += ASTLeavesCount[index]

        keywordTermFrequency = dict()
        for index in ASTLeavesCount.keys():
            if index >= 1 and index <= 65:
                keywordTermFrequency[index] = ASTLeavesCount[index] / keywordTotalCount

        ASTLeavesTotalCount = len(ASTLeavesTypeCount)
        ASTLeavesTermFrequency = dict()
        for index in ASTLeavesCount.keys():
            ASTLeavesTermFrequency[index] = ASTLeavesCount[index] / ASTLeavesTotalCount

        return keywordTermFrequency, ASTLeavesTermFrequency


    def calIndentifierLengthFrequency(self, tokenStream: CommonTokenStream):
        identifierLength = []
        for token in tokenStream.tokens:
            if token.type == 129:
                identifierLength.append(len(token.text))
        
        identifierLengthCount = Counter(identifierLength)

        return identifierLengthCount


    def calAccessControlTermFrequency(self):
        accessControlTF = {}
        accessControlTotalCount = sum(self.listener.accessControlCount.values())

        if accessControlTotalCount == 0:
            return None

        for accessControl in self.listener.accessControlCount.keys():
            accessControlTF[accessControl] = self.listener.accessControlCount[accessControl] / accessControlTotalCount
        
        return accessControlTF


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

    def extractCodeFeatures(self, file, fileData, tokenStream):
        codeFeatures = dict()
        codeFeatures['NewUsageNumberRate'], codeFeatures['SafetyUsageNumberRate'] = self.calaulateUsage(fileData)
        codeFeatures['CommentNumberRate'], codeFeatures['CommentTypeTF']= self.calculateCommentRateAndTypeTermFrequency(self.extractComment(tokenStream), file)
        codeFeatures['FunctionAvgLength'] = self.calculateFunctionAvgLength()
        codeFeatures['LocalVariableLocationVarience'] = self.calculateVariableLocationVariance()
        codeFeatures['EnglishLevel'], codeFeatures['CammelConventionNumberRate'], codeFeatures['UnderScoreConventionNumberRate'] = self.calculateEnglishLevelAndNormalNamingRate(tokenStream)
        codeFeatures['LambdaFunctionNumberRate'] = self.calculateLambdaFunctionCallMethod()
        codeFeatures['roughExceptionNumberRate'] = self.calculateRoughExceptionRate()
        codeFeatures['WordNumberTF'], codeFeatures['WordNumberOfLineFrequency']  = self.calWordTermFrequencyAndCountOfLine(fileData)
        codeFeatures['TernaryOperatorNumberRate'] = self.calTernaryOperatorRate(file)
        codeFeatures['ControlStructNumberRate'] = self.calControlStructureRate(file)
        codeFeatures['LiteralNumberRate'] = self.calLiteralRate(file)
        codeFeatures['KeywordNumberRate'] = self.calKeywordRate(tokenStream, file)
        codeFeatures['FunctionNumberRate'] = self.calFunctionRate(file)
        codeFeatures['ParamsAvgNumber'], codeFeatures['ParamsNumberStandardDev'] = self.calParamsAvgAndStandardDev()
        codeFeatures['LineAvgLength'], codeFeatures['LineLengthStandardDev'], codeFeatures['LineLengthFrequency'] = self.calLineLengthAvgAndStandardDev(fileData)
        codeFeatures['BlankLineNumberRate'] = self.calBlanklineRate(fileData)
        codeFeatures['TabNumberRate'], codeFeatures['SpaceNumberRate'], codeFeatures['NewLineNumberRate'] = self.calWhiteSpacesRate(file)
        codeFeatures['IsTabOrSpaceIndent'] = self.isTabOrSpaceIndent(fileData)
        codeFeatures['IsNewLineOrOnLineBeforeOpenBrance'] = self.isNewLineOrOnLineBeforeOpenBrance(tokenStream)
        codeFeatures['keywordTF'], codeFeatures['ASTLeavesTF'] = self.calASTLeavesAndKeywordTermFrequency(tokenStream)
        codeFeatures['IndentifierLengthFrequency'] = self.calIndentifierLengthFrequency(tokenStream)
        codeFeatures['AccessControlTF'] = self.calAccessControlTermFrequency()
        return codeFeatures


    def extractPsychologicalFeatures(self, codefeatures):
        psychologicalFeatures = dict()
        psychologicalFeatures['Openness'] = self.calculateOpenness(codefeatures['NewUsageNumberRate'])
        psychologicalFeatures['Conscientiousness'] = self.calculateConscientiousness(codefeatures['SafetyUsageNumberRate'],
                                                                                     codefeatures['CammelConventionNumberRate'],
                                                                                     codefeatures['FunctionNumberRate'],
                                                                                     codefeatures['CommentNumberRate'],
                                                                                     codefeatures['roughExceptionNumberRate'])
        psychologicalFeatures['Extroversion'] = self.calculateExtroversion(codefeatures['CommentNumberRate'])
        psychologicalFeatures['Agreeableness'] = self.calculateAgreeableness(codefeatures['NewUsageNumberRate'],
                                                                             codefeatures['FunctionNumberRate'],
                                                                             codefeatures['LambdaFunctionNumberRate'],
                                                                             codefeatures['roughExceptionNumberRate'])
        psychologicalFeatures['Neuroticism'] = self.calculateNeuroticism(codefeatures['CammelConventionNumberRate'],
                                                                         codefeatures['LocalVariableLocationVarience'])
        return psychologicalFeatures


    def parseFile(self, filePath):
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

        codeFeatures = self.extractCodeFeatures(file, fileData, tokenStream)
        fileFeatures = {
            'FileName': filePath.split('/')[-1],
            'FilePath': filePath,
            'CodeFeatures': codeFeatures,
            'PsychologicalFeatures': self.extractPsychologicalFeatures(codeFeatures)
        }

        return fileFeatures

    
    def outputFileFeatureToJson(self, filePath, outDir):
        fileFeature = self.parseFile(filePath)
        outFileName = fileFeature['FileName']
        outFilePath = os.path.join(outDir, outFileName)

        if os.path.exists(outFilePath):
            return

        with open(outFilePath, 'w') as wp:
            json.dump(fileFeature, wp, indent=4)
