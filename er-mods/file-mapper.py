import csv
import datetime

DATE_OPERATION = "DATE_OP"
DATE_VALUATION="DATE_VAL"
DESCRIPTION="DESCRIPTION"
CATEGORY_1="CATEGORY_1"
CATEGORY_2="CATEGORY_2"
AMOUNT="AMOUNT"
COMMENT="COMMENT"
ACCOUNT_NUMBER="ACCOUNT_NUM"
ACCOUNT_LABEL="ACCOUNT_LABEL"
ACCOUNT_BALANCE="ACCOUNT_BAL"
OPERATION_ID="OPERATION_ID"
CURRENCY="CURRENCY"
PAYMENT_REFERENCE="PAYMENT_REFERENCE"
EXCHANGE_FROM="EXCHANGE_FROM"
EXCHANGE_TO="EXCHANGE_TO"

class FormatMapper:
    def __init__(self, er):
        self.er = er

    def prefix(self):
        return "format-mapper"

    def alias(self):
        return ["recon", "fmap"]

    def description(self):
        return "Transform csv into ledger format"

    def formats(self):
        return {
            "boursorama" : {
                "delimiter": ";", 
                "quotechar": '"', 
                "header": 1,
                "columns": [DATE_OPERATION, DATE_VALUATION, DESCRIPTION, CATEGORY_1, CATEGORY_2, AMOUNT, COMMENT, ACCOUNT_NUMBER, ACCOUNT_LABEL, ACCOUNT_BALANCE],
                "date-format": "%Y-%m-%d",
                "decimal-separator": ",",
                "default-debit-account": "bourso",
                },
            "bourso" : {
                "delimiter": "\t", 
                "quotechar": '"', 
                "header": 1,
                "columns": [DATE_OPERATION, DATE_VALUATION, DESCRIPTION, AMOUNT, CURRENCY],
                "date-format": "%d/%m/%Y",
                "decimal-separator": ".",
                "default-debit-account": "bourso",
                },
            "wise" : {
                "delimiter": ",", 
                "quotechar": '"', 
                "header": 1,
                "columns": [OPERATION_ID, DATE_OPERATION, AMOUNT, CURRENCY, DESCRIPTION, PAYMENT_REFERENCE],
                "date-format": "%d-%m-%Y",
                "decimal-separator": ".",
                "default-debit-account": "wise_current",
                },
            "bnp" : {
                "delimiter": ",", 
                "quotechar": '"', 
                "header": 1,
                "columns": [DATE_OPERATION, CATEGORY_1, CATEGORY_2, DESCRIPTION, AMOUNT],
                "date-format": "%d-%m-%Y",
                "decimal-separator": ".",
                "default-debit-account": "current",
                },

        }

    def arguments(self):
        return {
            "file": {"alias": "f", "description": "Path to file"},
            "format": {"alias": "o", "description": "One of the known formats. Available formats : " + ", ".join(self.formats())}
        }


    def tokenize(self, file, format):
        columns = format["columns"]
        nbHeaders = format["header"] or 0
        delimiter = format["delimiter"]
        quotechar = format["quotechar"]
        debitAccount = format["default-debit-account"]
        creditAccount = format["default-credit-account"] if ("default-credit-account" in format) else "misc"
        payee = format["default-payee"] if ("default-payee" in format) else "Payee"

        templateRow = {"default-debit-account": debitAccount, "default-credit-account": creditAccount, "payee": payee}
        for col in columns:
            templateRow[col] = ""

        rows = []
        with open(file) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
            headerCount = 0
            for line in reader:
                if headerCount < nbHeaders :
                    headerCount += 1
                    continue    

                row = templateRow.copy()

                for colnum in range(0, len(columns)):
                    value = line[colnum]
                    row[columns[colnum]] = value
                rows.append(row)

        document = {"format": format, "rows": rows}
        return document

    def parse(self, document):
        format = document['format']
        columns = format["columns"]
        dateFormat = format["date-format"]
        decimalSeparator = format["decimal-separator"]

        dateColumns = list(filter(lambda x: "DATE" in x, columns))
        amountColumns = list(filter(lambda x: "AMOUNT" in x, columns))
        
        for row in document['rows']:
            for colName in row.keys():
                if colName in dateColumns:
                    row[colName] = self.parseDate(row[colName], dateFormat)
                elif colName in amountColumns:
                    row[colName] = self.parseAmount(row[colName], decimalSeparator)

        return document

    def parseAmount(self, amountString, decimalSeparator):
        ast = amountString.replace(decimalSeparator, ".").replace(" ", "")
        return float(ast)

    def parseDate(self, dateString, format):
        if not dateString:
            return dateString
        return datetime.datetime.strptime(dateString.strip(), format)

    def print(self, rows):
        sortedrows = sorted(rows, key=lambda row : row[DATE_OPERATION])
        for row in sortedrows:
            date = row[DATE_OPERATION]
            if date is None:
                self.er.log("skipping " + row)
                continue
            date = date.strftime("%m/%d")
            amountValue = row[AMOUNT]
            amount = "€{:.2f}".format(abs(amountValue))
            payee = row["payee"]
            creditAccount = row["default-credit-account"] if amountValue < 0 else row["default-debit-account"]
            debitAccount = row["default-debit-account"] if amountValue < 0 else row["default-credit-account"]
            description = row[DESCRIPTION]
            #print("%s\t%s\n\t;%s\n\t%s\n\t%s\n\t%s\n"(date, payee, description, creditAccount, amount, debitAccount))
            print(date+ "\t" + payee + "\n\t;"+ description + "\n\t"+ creditAccount + "\t" + amount + "\n\t" + debitAccount + "\n")
            
                
    def run(self, argsValue={}):
        
        file = argsValue["file"]
        formatName = argsValue["format"]
        print(formatName)
        format = self.formats()[formatName]
        document = self.tokenize(file, format)
        document = self.parse(document)

        self.print(document["rows"])

    def findPayee(self, payee):
        pass

def __module__(er):
  return FormatMapper(er)
