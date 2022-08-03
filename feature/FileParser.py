class FileParser():
    def __init__(self, file) -> None:
        self.file = file

        # function-based code features 
        self.newUsageNumber = 0
        self.oldUsageNumber = 0
        self.safetyUsageNumber = 0
        
        self.lambdaCallNumber = 0
        self.allCallNumber = 0

        self.normalizedFunctionNumber = 0
        self.longFunctionNumber = 0

        # variable
        self.normalizedVariableNumber = 0
        self.variableNumber = 0

        # comment
        self.commentLines = 0
        self.codeLines = 0

        # quote
        self.validImportNumber = 0
        self.importNumber = 0

        # code style
        self.validExceptionNumber = 0
        self.exceptionNumber = 0
    
    