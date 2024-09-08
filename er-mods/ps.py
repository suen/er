
class process:
  def __init__(self, er):
      self.er = er
  
  def prefix(self):
      return "ps"
  
  def alias(self):
      return ["nasl"]
  
  def description(self):
      return "show top process"
  
  def arguments(self):
      return {
          "flag-argument": {"alias": "a", "flag": True, "description": "New flag argument"},
          "value-argument": {"alias": "a", "description": "New flag argument", "default": "DEFAULT_VALUE"},
      }

  def run(self, argsValue={}):
      flagArgument = argsValue["flag-argument"]
      valueArgument = argsValue["value-argument"]
      
      self.er.log("New module")
      self.er.log("Launched with --flag-argument=%s --value-argument=%s"%(flagArgument, valueArgument))


def __module__(er):
  return process(er)
