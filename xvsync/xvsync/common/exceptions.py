
class XvException(Exception):
    def __init__(self, prompt=None, msg=None):
        self.prompt = prompt
        self.msg = msg

    def __str__(self):
        return '%s: %s' % (self.prompt, self.msg)

class FieldMissError(XvException):
    def __init__(self, msg=None):
        XvException.__init__(self, self.__class__.__name__, msg)

class UrlNotMatchError(XvException):
    def __init__(self, msg=None):
        XvException.__init__(self, self.__class__.__name__, msg)

class FieldTypeError(XvException):
    def __init__(self, msg=None):
        XvException.__init__(self, self.__class__.__name__, msg)

if __name__ == '__main__':
    import json
    try:
        item = {'k': 'v'}
        #raise FieldMissError(json.dumps(item))
        #raise UrlNotMatchError(json.dumps(item))
        raise FieldTypeError(json.dumps(item))
        #raise KeyError(0)
    except (FieldMissError, UrlNotMatchError, FieldTypeError) as e:
        print str(e)
    except Exception  as e:
        print str(e)
