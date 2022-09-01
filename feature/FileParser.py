import re

from grammer.JavaParser import JavaParser
from grammer.JavaLexer import JavaLexer
from antlr4 import *
from grammer.JavaExtract import JavaExtract


class FileParser():

    def __init__(self):
        self.listener = JavaExtract()
        self.walker = ParseTreeWalker()

    def analyzeUsage(self, code):
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

    def extractComment(self, tokenStream):
        comment = []

        for token in tokenStream.tokens:
            if token.channel == 4:
                comment.append(token.text)

        return comment

    def calculateFunctionLengthAndVariableLocation(self, listener):
        functionLength = []
        variableLocation = []

        for function in listener.functionList:
            # calculate function length
            functionLength.append(function['functionEndLine'] - function['functionStartLine'] + 1)

            # calculate variable location
            functionStartLine = function['functionStartLine']
            variableRelativeLocation = []
            for variable in function['localVariableList']:
                variableRelativeLocation.append(variable['Line'] - functionStartLine + 1)

            variableLocation.append({
                'functionLength': functionLength[-1],
                'variableRelativeLocation': variableRelativeLocation
            })

        return functionLength, variableLocation

    def parse(self, file):
        # parse ast
        tokenStream = CommonTokenStream(JavaLexer(InputStream(file)))
        parser = JavaParser(tokenStream)
        self.walker.walk(self.listener, parser.compilationUnit())

        #TODO: extract feature