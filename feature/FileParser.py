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


    def calUsage(self, fileData):
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
        
        return newUsageNumber, oldUsageNumber, safetyUsageNumber


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


    def calCommentRateAndTypeFrequency(self, commentList):
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

        return commentLength, commentTypeCount


    def extractFunctionInfo(self):
        if self.listener.functionNumber == 0:
            return None

        FunctionInfo = self.listener.functionList

        return FunctionInfo


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

        return englishScore, englishUsageTime


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
            return None, None, None, None, None

        wordList = []
        
        if len(wordList) == 0:
            return None, None, None, None, None

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

        return englishLevel, cammelIdentifierNumber, underScoreIdentifierNumber, len(wordList)


    def calLambdaFunctionCallCount(self):
        return self.listener.lambdaFunctionNumber


    def calRoughExceptionCount(self):
        if self.listener.exceptionNumber == 0 :
            return None

        roughExceptNumber = 0
        for exceptName in self.listener.exceptionNameList:
            if exceptName == 'Exception':
                roughExceptNumber += 1

        return roughExceptNumber


    def calWordFrequencyAndCountOfLine(self, fileData):
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

        wordCountOfLineFrequency = Counter(wordCountOfLine)

        return wordFrequency, wordCountOfLineFrequency, wordTotalCount


    def calTernaryOperatorCount(self):
        return self.listener.ternaryOperatorNumber


    def calTokenCount(self, text):
        token = re.split('[*;\\{\\}\\[\\]()+=\\-&/|%!?:,<>~`\\s\"]', text)
        return len(token)


    def calControlStructureCount(self):
        return self.listener.controlStructureNumber
        

    def calLiteralCount(self):
        return self.listener.literalNumber


    def calKeywordCount(self, tokenStream: CommonTokenStream):
        tokenNumber = 0
        for token in tokenStream.tokens:
            if token.type >= 1 and token.type <= 66:
                tokenNumber += 1

        return tokenNumber


    def calLineLengthFrequency(self, fileData):
        lineLength = [len(line) for line in fileData]
        lineLengthCount = Counter(lineLength)
        
        return lineLengthCount


    def calBlanklineCount(self, fileData):
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

        return blankCount


    # return tabRate, spaceRate, and whiteSpaceRate
    def calWhiteSpacesCount(self, text):
        tabTermCount = len(re.findall('\\t', text)) / len(text)
        spaceTermCount = len(re.findall(' ', text)) / len(text)
        newLineTermCount = len(re.findall('\\n', text)) / len(text)

        return tabTermCount, spaceTermCount, newLineTermCount


    def calTabAndSpaceIndentCount(self, fileData):
        tabIndentCount = 0
        spaceIndentCount = 0
        for line in fileData:
            if line.startswith('\\t'):
                tabIndentCount += 1
            elif line.startswith(' '):
                spaceIndentCount += 1

        return tabIndentCount, spaceIndentCount


    def CalNewLineAndOnLineBeforeOpenBranceCount(self, tokenStream: CommonTokenStream):
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

        return newLineCount, onLineCount


    # Return AST Leaves TF And Keyword TF
    # AST Leaves consist of 130 types
    # java has 66 kinds of keyword
    def calASTLeavesAndKeywordFrequency(self, tokenStream: CommonTokenStream):
        
        symbolicNames = [ "<INVALID>", "ABSTRACT", "ASSERT", "BOOLEAN", "BREAK", 
                      "BYTE", "CASE", "CATCH", "CHAR", "CLASS", "CONST", 
                      "CONTINUE", "DEFAULT", "DO", "DOUBLE", "ELSE", "ENUM", 
                      "EXTENDS", "FINAL", "FINALLY", "FLOAT", "FOR", "IF", 
                      "GOTO", "IMPLEMENTS", "IMPORT", "INSTANCEOF", "INT", 
                      "INTERFACE", "LONG", "NATIVE", "NEW", "PACKAGE", "PRIVATE", 
                      "PROTECTED", "PUBLIC", "RETURN", "SHORT", "STATIC", 
                      "STRICTFP", "SUPER", "SWITCH", "SYNCHRONIZED", "THIS", 
                      "THROW", "THROWS", "TRANSIENT", "TRY", "VOID", "VOLATILE", 
                      "WHILE", "MODULE", "OPEN", "REQUIRES", "EXPORTS", 
                      "OPENS", "TO", "USES", "PROVIDES", "WITH", "TRANSITIVE", 
                      "VAR", "YIELD", "RECORD", "SEALED", "PERMITS", "NON_SEALED", 
                      "DECIMAL_LITERAL", "HEX_LITERAL", "OCT_LITERAL", "BINARY_LITERAL", 
                      "FLOAT_LITERAL", "HEX_FLOAT_LITERAL", "BOOL_LITERAL", 
                      "CHAR_LITERAL", "STRING_LITERAL", "TEXT_BLOCK", "NULL_LITERAL", 
                      "LPAREN", "RPAREN", "LBRACE", "RBRACE", "LBRACK", 
                      "RBRACK", "SEMI", "COMMA", "DOT", "ASSIGN", "GT", 
                      "LT", "BANG", "TILDE", "QUESTION", "COLON", "EQUAL", 
                      "LE", "GE", "NOTEQUAL", "AND", "OR", "INC", "DEC", 
                      "ADD", "SUB", "MUL", "DIV", "BITAND", "BITOR", "CARET", 
                      "MOD", "ADD_ASSIGN", "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", 
                      "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", "MOD_ASSIGN", 
                      "LSHIFT_ASSIGN", "RSHIFT_ASSIGN", "URSHIFT_ASSIGN", 
                      "ARROW", "COLONCOLON", "AT", "ELLIPSIS", "WS", "ENTER", 
                      "COMMENT", "LINE_COMMENT", "IDENTIFIER" ]
        
        ASTLeavesTypeCount = []
        for token in tokenStream.tokens:
            ASTLeavesTypeCount.append(token.type)

        # ASTLeavesCount:
        # index 0 : Unknown
        # index 1-66: keyword
        # index 67-129: operator identifier comment
        ASTLeavesCount = Counter(ASTLeavesTypeCount)

        normKeywordFrequency = dict()
        for index in ASTLeavesCount.keys():
            if index >= 1 and index <= 66:
                normKeywordFrequency[symbolicNames[index]] = ASTLeavesCount[index]

        normASTLeavesFrequency = dict()
        for index in ASTLeavesCount.keys():
            normASTLeavesFrequency[symbolicNames[index]] = ASTLeavesCount[index]

        return normKeywordFrequency, normASTLeavesFrequency


    def calIndentifierLengthFrequency(self, tokenStream: CommonTokenStream):
        identifierLength = []
        for token in tokenStream.tokens:
            if token.type == 129:
                identifierLength.append(len(token.text))
        
        identifierLengthCount = Counter(identifierLength)

        return identifierLengthCount


    def calAccessControlFrequency(self):
        return self.listener.accessControlCount


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


    def extractCodeOriginFeatures(self, file, fileData, tokenStream):
        codeFeatures = dict()
        codeFeatures['NewUsageNumber'], codeFeatures['OldUseageNumber'], codeFeatures['SafetyUsageNumber'] = self.calUsage(fileData)
        codeFeatures['CommentNumber'], codeFeatures['CommentTypeFrequency']= self.calCommentRateAndTypeFrequency(self.extractComment(tokenStream))
        codeFeatures['FunctionInfo'] = self.extractFunctionInfo()
        codeFeatures['EnglishScore'], codeFeatures['EnglishUsageNumber'], codeFeatures['CammelConventionNumber'],
        codeFeatures['UnderScoreConventionNumber'], codeFeatures['NormalIdentifierNumber']= self.calculateEnglishLevelAndNormalNamingRate(tokenStream)
        
        codeFeatures['LambdaFunctionNumber'] = self.calLambdaFunctionCallCount()
        codeFeatures['roughExceptionNumber'] = self.calRoughExceptionCount()
        codeFeatures['wordFrequency'], codeFeatures['WordNumberOfLineFrequency'], codeFeatures['WordNumber'] = self.calWordFrequencyAndCountOfLine(fileData)
        codeFeatures['TernaryOperatorNumber'] = self.calTernaryOperatorCount()
        codeFeatures['ControlStructNumber'] = self.calControlStructureCount()
        codeFeatures['LiteralNumber'] = self.calLiteralCount()
        codeFeatures['LineLengthFrequency'] = self.calLineLengthFrequency(fileData)
        codeFeatures['BlankLineNumberNumber'] = self.calBlanklineCount(fileData)
        codeFeatures['TabNumberNumber'], codeFeatures['SpaceNumberNumber'], codeFeatures['NewLineNumberNumber'] = self.calWhiteSpacesCount(file)
        codeFeatures['TabIndentNumber'], codeFeatures['TabIndentNumber'] = self.calTabAndSpaceIndentCount(fileData)
        codeFeatures['NewLineBeforeOpenBranceNumber'], codeFeatures['OnLineBeforeOpenBranceNumber'] = self.CalNewLineAndOnLineBeforeOpenBranceCount(tokenStream)
        codeFeatures['keywordFrequency'], codeFeatures['ASTLeavesFrequency'] = self.calASTLeavesAndKeywordFrequency(tokenStream)
        codeFeatures['IndentifierLengthFrequency'] = self.calIndentifierLengthFrequency(tokenStream)
        codeFeatures['AccessControlFrequency'] = self.calAccessControlFrequency()
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

        codeFeatures = self.extractCodeOriginFeatures(file, fileData, tokenStream)
        fileFeatures = {
            'FileName': filePath.split('/')[-1],
            'FilePath': filePath,
            'FileLength': len(file),
            'FileLineNumber': len(fileData),
            'CodeFeatures': codeFeatures
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
