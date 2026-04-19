import csv
import datetime

DATE_OPERATION = "DATE_OP"
DATE_VALUATION="DATE_VAL"
DESCRIPTION="DESCRIPTION"
CATEGORY_1="CATEGORY_1"
CATEGORY_2="CATEGORY_2"
AMOUNT="AMOUNT"
COMMENT="COMMENT"
SUPPLIER_FOUND="SUPPLIER_FOUND"
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
            "bourso" : {
                "delimiter": ";", 
                "quotechar": '"', 
                "header": 1,
                "columns": [DATE_OPERATION, DATE_VALUATION, DESCRIPTION, CATEGORY_1, CATEGORY_2, SUPPLIER_FOUND, AMOUNT, COMMENT, ACCOUNT_NUMBER, ACCOUNT_LABEL, ACCOUNT_BALANCE],
                "date-format": "%Y-%m-%d",
                "decimal-separator": ",",
                "default-debit-account": "bourso",
                },
            "fortuneo" : {
                "delimiter": ";", 
                "quotechar": '', 
                "header": 1,
                "columns": [DATE_OPERATION, DATE_VALUATION, DESCRIPTION, AMOUNT, ACCOUNT_BALANCE],
                "date-format": "%d/%m/%Y",
                "decimal-separator": ",",
                "default-debit-account": "fortuneo",
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
            "amex" : {
                "delimiter": ",", 
                "quotechar": '"', 
                "header": 1,
                "columns": [DATE_OPERATION, DESCRIPTION, AMOUNT],
                "date-format": "%m/%d/%Y",
                "decimal-separator": ",",
                "default-debit-account": "amex",
                "debit-flow" : "+",
                },

        }

    def arguments(self):
        return {
            "file": {"alias": "f", "description": "Path to file"},
            "format": {"alias": "o", "description": "One of the known formats. Available formats : " + ", ".join(self.formats())},
            "last-date": {"alias": "d", "description": "Last date in yyyy-mm-dd"}
        }


    def tokenize(self, file, format):
        columns = format["columns"]
        nbHeaders = format["header"] or 0
        delimiter = format["delimiter"]
        quotechar = format["quotechar"]
        debitAccount = format["default-debit-account"]
        creditAccount = format["default-credit-account"] if ("default-credit-account" in format) else "misc"
        payee = format["default-payee"] if ("default-payee" in format) else "Payee"
        debitFlowSign = int(format.get("debit-flow", "-") + "1")

        templateRow = {"default-debit-account": debitAccount, "default-credit-account": creditAccount, "payee": payee, "debit-flow-sign": debitFlowSign}
        for col in columns:
            templateRow[col] = ""

        rows = []
        with open(file) as csvfile:
            quotechar = None if quotechar == "" else quotechar
            reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
            headerCount = 0
            for line in reader:
                if len(columns) != len(line):
                    print("Number of columns expected=%d, found=%d"%(len(columns), len(line)))
                    raise Exception("Column : " + str(columns) + "\nline: " + str(line))
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
                    try:
                        row[colName] = self.parseAmount(row[colName], decimalSeparator)
                    except:
                        raise Exception("Could not parse ", row)

        return document

    def parseAmount(self, amountString, decimalSeparator):
        ast = amountString.replace(decimalSeparator, ".").replace(" ", "")
        return float(ast)

    def parseDate(self, dateString, format):
        if not dateString:
            return dateString
        return datetime.datetime.strptime(dateString.strip(), format)

    def print(self, rows, lastDate=None):
        sortedrows = sorted(rows, key=lambda row : row[DATE_OPERATION])
        for row in sortedrows:
            date = row[DATE_OPERATION]
            if date is None:
                self.er.log("skipping " + row)
                continue

            formattedDate = date.strftime("%m/%d")
            amountValue = row[AMOUNT]
            amount = "€{:.2f}".format(abs(amountValue))
            payee = row["payee"]
            description = row[DESCRIPTION]

            if lastDate is not None and lastDate >= date:
                self.er.log("skipped because of date : Line [%s] [%s] [%s]"%(formattedDate, description, amount))
                continue        

            if (amountValue < 0):
                creditAccount = row["default-credit-account"]
                debitAccount = row["default-debit-account"]
            else:
                creditAccount = row["default-debit-account"]
                debitAccount = row["default-credit-account"]

            if (row["debit-flow-sign"] > 0):
                tmp = creditAccount
                creditAccount = debitAccount
                debitAccount = tmp
            print(formattedDate+ "\t" + payee + "\n\t;"+ description + "\n\t"+ creditAccount + "\t" + amount + "\n\t" + debitAccount + "\n")
            
                
    def run(self, argsValue={}):
        
        file = argsValue["file"]
        formatName = argsValue["format"]
        lastDateParam = argsValue.get("last-date", None)
        lastDate = None
        if (lastDateParam is not None):
            lastDate = self.parseDate(lastDateParam, "%Y-%m-%d")
        print(formatName)
        format = self.formats()[formatName]
        document = self.tokenize(file, format)
        document = self.parse(document)

        self.print(document["rows"], lastDate)

    def findPayee(self, payee):
        pass

def __module__(er):
  return FormatMapper(er)
