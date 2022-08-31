from JavaParserListener import JavaParserListener
from JavaParser import JavaParser
from antlr4 import *

class JavaExtract(JavaParserListener):

    def __init__(self):
        super().__init__()

        # function-based code features
        self.functionNumber = 0
        self.functionList = []
        self.lambdaFunctionNumber = 0

        # variable
        self.classVariableName = []
        self.classVariableNumber = 0
        
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
        exceptionList = ctx.qualifiedName().getText()
        for exception in exceptionList:
            exceptionName = exception.getText()
            self.exceptionName.append(exceptionName)
            self.exceptionNumber += 1
        return super().enterCatchType(ctx)

    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        # capture exception name and number
        if ctx.THROWS() != None:
            qualifiedList = ctx.qualifiedNameList().qualifiedName()
            for qualified in qualifiedList:
                exceptionName = qualified.getText()
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
        self.functionNumber += 1
        return super().enterMethodDeclaration(ctx)

    def enterInterfaceCommonBodyDeclaration(self, ctx: JavaParser.InterfaceCommonBodyDeclarationContext):
        if ctx.THROWS() != None:
            qualifiedList = ctx.qualifiedNameList().qualifiedName()
            for qualified in qualifiedList:
                exceptionName = qualified.getText()
                self.exceptionName.append(exceptionName)
                self.exceptionNumber += 1
        return super().enterInterfaceCommonBodyDeclaration(ctx)

    def enterConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        if ctx.THROWS() != None:
            qualifiedList = ctx.qualifiedNameList().qualifiedName()
            for qualified in qualifiedList:
                exceptionName = qualified.getText()
                self.exceptionName.append(exceptionName)
                self.exceptionNumber += 1
        return super().enterConstructorDeclaration(ctx)


    def enterFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
        contextList = ctx.variableDeclarators().variableDeclarator()
        for context in contextList:
            variableName = context.variableDeclaratorId().getText()
            self.classVariableName.append(variableName)
            self.classVariableNumber += 1
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

    def enterLambdaExpression(self, ctx: JavaParser.LambdaExpressionContext):
        self.lambdaFunctionNumber += 1
        return super().enterLambdaExpression(ctx)