from JavaParserListener import JavaParserListener
from JavaParser import JavaParser
from JavaLexer import JavaLexer
from antlr4 import *


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
        
        self.functionInfo = []

        # variable
        self.variableName = []

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
        context = ctx.qualifiedName().getText()
        self.packageName.append(context)
        self.packageNumber += 1
        return super().enterPackageDeclaration(ctx)

    def enterImportDeclaration(self, ctx: JavaParser.ImportDeclarationContext):
        context = ctx.qualifiedName().getText()
        self.importName.append(context)
        self.importNumber += 1
        return super().enterImportDeclaration(ctx)

    def enterCatchType(self, ctx: JavaParser.CatchTypeContext):
        context = ctx.qualifiedName().getText()
        self.exceptionName.append(context)
        self.exceptionNumber += 1
        return super().enterCatchType(ctx)

    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        if(ctx.THROWS() != None):
            context = ctx.qualifiedNameList().getText()
            self.exceptionName.append(context)
            self.exceptionNumber += 1
        return super().enterMethodDeclaration(ctx)

    def enterInterfaceCommonBodyDeclaration(self, ctx: JavaParser.InterfaceCommonBodyDeclarationContext):
        if(ctx.THROWS() != None):
            context = ctx.qualifiedNameList().getText()
            self.exceptionName.append(context)
            self.exceptionNumber += 1
        return super().enterInterfaceCommonBodyDeclaration(ctx)

    def enterConstDeclaration(self, ctx: JavaParser.ConstDeclarationContext):
        if(ctx.THROWS() != None):
            context = ctx.qualifiedNameList().getText()
            self.exceptionName.append(context)
            self.exceptionNumber += 1
        return super().enterConstDeclaration(ctx)