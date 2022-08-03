from grammer import JavaParserListener


class JavaExtract():
    def __init__(self, s) -> None:
        super().__init__()
        
        # function-based code features 
        self.newCallNumber = 0
        self.oldCallNumber = 0
        self.safetyCallNumber = 0
        self.lambdaCallNumber = 0
        self.allCallNumber = 0

        self.normalizedFunctionNumber = 0
        self.longFunctionNumber = 0
        self.functionNumber = 0

        self.functionName = []

        # variable

        # comment
        self.commentLines = 0
        self.codeLines = 0

        # quote
        self.validImportNumber = 0
        self.importNumber = 0

        # code style
        self.validExceptionNumber = 0
        self.exceptionNumber = 0

