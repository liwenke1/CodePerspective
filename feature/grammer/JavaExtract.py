from .JavaParserListener import JavaParserListener
from .JavaParser import JavaParser
from antlr4 import *

class JavaExtract(JavaParserListener):

    def __init__(self):
        super().__init__()

        # function-based
        self.functionNumber = 0
        self.functionList = []
        self.lambdaFunctionNumber = 0

        # class-based 
        self.classNameList = []
        self.classNumber = 0
        self.classVariableNameList = []
        self.classVariableNumber = 0
        
        # quote
        self.importNumber = 0
        self.importNameList = []

        # code style
        self.exceptionNumber = 0
        self.exceptionNameList = []
        self.packageNumber = 0
        self.packageNameList = []
        self.ternaryOperatorNumber = 0
        self.controlStructureNumber = 0
        self.literalNumber = 0

        # access control
        self.accessControlCount = {
            'Default': 0,
            'Public': 0,
            'Protected': 0,
            'Private': 0
        }


    def enterPackageDeclaration(self, ctx: JavaParser.PackageDeclarationContext):
        packageName = ctx.qualifiedName().getText()
        self.packageNameList.append(packageName)
        self.packageNumber += 1
        return super().enterPackageDeclaration(ctx)


    def enterImportDeclaration(self, ctx: JavaParser.ImportDeclarationContext):
        importName = ctx.qualifiedName().getText()
        self.importNameList.append(importName)
        self.importNumber += 1
        return super().enterImportDeclaration(ctx)


    def enterClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        self.classNameList.append(ctx.identifier().getText())
        self.classNumber += 1
        return super().enterClassDeclaration(ctx)


    def enterCatchType(self, ctx: JavaParser.CatchTypeContext):
        exceptionList = ctx.qualifiedName()
        for exception in exceptionList:
            exceptionName = exception.getText()
            self.exceptionNameList.append(exceptionName)
            self.exceptionNumber += 1
        return super().enterCatchType(ctx)


    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        # capture exception name and number
        if ctx.THROWS() != None:
            qualifiedList = ctx.qualifiedNameList().qualifiedName()
            for qualified in qualifiedList:
                exceptionName = qualified.getText()
            self.exceptionNameList.append(exceptionName)
            self.exceptionNumber += 1

        # capture function information
        functionName = ctx.identifier().getText()
        functionBody = ctx.getText()
        functionStartLine = ctx.start.line
        functionEndLine = ctx.stop.line

        # capture params
        functionParams = []
        # capture params   --- receiver parameter
        if ctx.formalParameters().receiverParameter():
            params = ctx.formalParameters().receiverParameter()
            typeName = params.typeType().getText()
            identifiers = params.identifier().getText()
            if isinstance(identifiers, list):
                for identifier in identifiers:
                    functionParams.append({
                        'type': typeName,
                        'identifier': identifier
                    })
            else:
                functionParams.append({
                    'type': typeName,
                    'identifier': identifiers
                })

        # capture params   --- formal parameter
        if ctx.formalParameters().formalParameterList():
            params = ctx.formalParameters().formalParameterList()
            if params.lastFormalParameter():
                lastParam = params.lastFormalParameter()
                functionParams.append({
                    'type': lastParam.typeType().getText(),
                    'identifier': lastParam.variableDeclaratorId().getText()
                })
            if params.formalParameter():
                formalParams = params.formalParameter()
                if isinstance(formalParams, list):
                    for formalParam in formalParams:
                        functionParams.append({
                            'type': formalParam.typeType().getText(),
                            'identifier': formalParam.variableDeclaratorId().getText()
                        })
                else:
                    functionParams.append({
                        'type': formalParams.typeType().getText(),
                        'identifier': formalParams.variableDeclaratorId().getText()
                    })

        # summarize unction information
        self.functionList.append(
            {
                'functionName': functionName,
                'functionBody': functionBody,
                'functionStartLine': functionStartLine,
                'functionEndLine': functionEndLine,
                'functionParams': functionParams,
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
                self.exceptionNameList.append(exceptionName)
                self.exceptionNumber += 1
        return super().enterInterfaceCommonBodyDeclaration(ctx)


    def enterConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        if ctx.THROWS() != None:
            qualifiedList = ctx.qualifiedNameList().qualifiedName()
            for qualified in qualifiedList:
                exceptionName = qualified.getText()
                self.exceptionNameList.append(exceptionName)
                self.exceptionNumber += 1
        return super().enterConstructorDeclaration(ctx)


    def enterFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
        contextList = ctx.variableDeclarators().variableDeclarator()
        for context in contextList:
            variableName = context.variableDeclaratorId().getText()
            self.classVariableNameList.append(variableName)
            self.classVariableNumber += 1
        return super().enterFieldDeclaration(ctx)


    def enterLocalVariableDeclaration(self, ctx: JavaParser.LocalVariableDeclarationContext):
        variableList = ctx.variableDeclarators().variableDeclarator()
        for variable in variableList:
            variableName = variable.variableDeclaratorId().getText()
            variableLine = variable.start.line
            variableColumn = variable.start.column
            
            # bug: unhandle "static {int a = 4;}"
            if len(self.functionList) == 0:
                break
            
            self.functionList[-1]['localVariableList'].append(
                {
                    'variableName': variableName,
                    'Line': variableLine,
                    'Column': variableColumn
                }
            )
        return super().enterLocalVariableDeclaration(ctx)


    def enterMethodCall(self, ctx: JavaParser.MethodCallContext):
        if ctx.identifier():
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


    def enterExpression(self, ctx: JavaParser.ExpressionContext):
        # ternary operator  ->  ? :
        if ctx.bop and ctx.bop.text == '?':
            self.ternaryOperatorNumber += 1
        return super().enterExpression(ctx)


    def enterStatement(self, ctx: JavaParser.StatementContext):
        if ctx.IF():
            self.controlStructureNumber += 1
        elif ctx.ELSE():
            self.controlStructureNumber += 1
        elif ctx.DO():
            self.controlStructureNumber += 1
        elif ctx.WHILE():
            self.controlStructureNumber += 1
        elif ctx.FOR():
            self.controlStructureNumber += 1
        elif ctx.SWITCH():
            self.controlStructureNumber += 1
        return super().enterStatement(ctx)

    
    def enterLiteral(self, ctx: JavaParser.LiteralContext):
        self.literalNumber += 1
        return super().enterLiteral(ctx)

    
    def enterClassOrInterfaceModifier(self, ctx: JavaParser.ClassOrInterfaceModifierContext):
        if ctx.PUBLIC():
            self.accessControlCount['Public'] += 1
        elif ctx.PROTECTED():
            self.accessControlCount['Protected'] += 1
        elif ctx.PRIVATE():
            self.accessControlCount['Private'] += 1
        else:
            self.accessControlCount['Default'] += 1
        return super().enterClassOrInterfaceModifier(ctx)