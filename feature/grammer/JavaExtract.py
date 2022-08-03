from JavaParserListener import JavaParserListener
from JavaParser import JavaParser
from JavaLexer import JavaLexer
from antlr4 import *

import json

class JavaExtract(JavaParserListener):

    def __init__(self, tokens) -> None:
        super().__init__()

        # tokens
        self.tokens = tokens

        # function-based code features
        self.newCallNumber = 0
        self.oldCallNumber = 0
        self.safetyCallNumber = 0
        self.lambdaCallNumber = 0
        self.allCallNumber = 0

        self.normalizedFunctionNumber = 0
        self.longFunctionNumber = 0
        
        self.functionList = []

        # variable
        self.classVariableName = []


        # comment
        self.commentLines = 0
        self.codeLines = 0

        # quote
        self.importNumber = 0
        self.importName = []

        # code style
        self.exceptionNumber = 0
        self.exceptionName = []
        self.packageNumber = 0
        self.packageName = []

    def enterPackageDeclaration(self, ctx: JavaParser.PackageDeclarationContext):
        packageName = ctx.qualifiedName().getText()
        self.packageName.append(packageName)
        self.packageNumber += 1
        return super().enterPackageDeclaration(ctx)

    def enterImportDeclaration(self, ctx: JavaParser.ImportDeclarationContext):
        importName = ctx.qualifiedName().getText()
        self.importName.append(importName)
        self.importNumber += 1
        return super().enterImportDeclaration(ctx)

    def enterCatchType(self, ctx: JavaParser.CatchTypeContext):
        exceptionName = ctx.qualifiedName().getText()
        self.exceptionName.append(exceptionName)
        self.exceptionNumber += 1
        return super().enterCatchType(ctx)

    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        # capture exception name and number
        if ctx.THROWS() != None:
            exceptionName = ctx.qualifiedNameList().getText()
            self.exceptionName.append(exceptionName)
            self.exceptionNumber += 1

        # capture function information
        functionName = ctx.identifier().getText()
        functionBody = ctx.getText()
        functionStartLine = ctx.start.line
        functionEndLine = ctx.stop.line
        self.functionList.append(
            {
                'functionName': functionName,
                'functionBody': functionBody,
                'functionStartLine': functionStartLine,
                'functionEndLine': functionEndLine,
                'localVariableList': [],
                'functionCallList': []
            }
        )
        return super().enterMethodDeclaration(ctx)

    def enterInterfaceCommonBodyDeclaration(self, ctx: JavaParser.InterfaceCommonBodyDeclarationContext):
        if ctx.THROWS() != None:
            context = ctx.qualifiedNameList().getText()
            self.exceptionName.append(context)
            self.exceptionNumber += 1
        return super().enterInterfaceCommonBodyDeclaration(ctx)

    def enterConstDeclaration(self, ctx: JavaParser.ConstDeclarationContext):
        if ctx.THROWS() != None:
            context = ctx.qualifiedNameList().getText()
            self.exceptionName.append(context)
            self.exceptionNumber += 1
        return super().enterConstDeclaration(ctx)

    def enterFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
        contextList = ctx.variableDeclarators().variableDeclarator()
        for context in contextList:
            variableName = context.variableDeclaratorId().getText()
            self.classVariableName.append(variableName)
        return super().enterFieldDeclaration(ctx)

    def enterLocalVariableDeclaration(self, ctx: JavaParser.LocalVariableDeclarationContext):
        variableList = ctx.variableDeclarators().variableDeclarator()
        for variable in variableList:
            variableName = variable.variableDeclaratorId().getText()
            variableLine = variable.start.line
            variableColumn = variable.start.column
            self.functionList[-1]['localVariableList'].append(
                {
                    'variableName': variableName,
                    'Line': variableLine,
                    'Column': variableColumn
                }
            )
        return super().enterLocalVariableDeclaration(ctx)

    def enterMethodCall(self, ctx: JavaParser.MethodCallContext):
        functionCallName = ctx.identifier().getText()
        functionCallLine = ctx.start.line
        functionCallColumn = ctx.start.column

        if len(self.functionList) != 0 :
            if functionCallLine >= self.functionList[-1]['functionStartLine'] \
                and functionCallLine <= self.functionList[-1]['functionEndLine']:
                self.functionList[-1]['functionCallList'].append(
                    {
                        'functionCallName': functionCallName,
                        'line': functionCallLine,
                        'column': functionCallColumn
                    }
                )
        return super().enterMethodCall(ctx)
