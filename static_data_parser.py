"""Parse declarative JS constants without eval, Node execution or network access."""
import copy
import json
import re

TOKEN=re.compile(r'''\s+|//[^\n]*|/\*[\s\S]*?\*/|(?:"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*')|\.\.\.|[A-Za-z_$][\w$]*|(?:\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|[\[\]{}=:;,\-+]''')


def js_string(token):
    result=[];i=1
    while i<len(token)-1:
        c=token[i];i+=1
        if c!='\\':result.append(c);continue
        if i>=len(token)-1:raise ValueError('Incomplete string escape')
        c=token[i];i+=1
        if c in ('u','x'):
            size=4 if c=='u' else 2;digits=token[i:i+size]
            if len(digits)!=size or not re.fullmatch('[0-9A-Fa-f]+',digits):raise ValueError('Invalid string escape')
            result.append(chr(int(digits,16)));i+=size
        elif c in '\n\r':
            if c=='\r' and token[i:i+1]=='\n':i+=1
        else:result.append({'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f','v':'\v','0':'\0'}.get(c,c))
    return ''.join(result)


def parse_constants(source):
    if not isinstance(source,str) or len(source)>8_000_000:raise ValueError('Invalid static source size')
    tokens=[];end=0
    for match in TOKEN.finditer(source):
        if match.start()!=end:raise ValueError('Unsupported executable or invalid source syntax')
        end=match.end();token=match.group()
        if token.isspace() or token.startswith(('//','/*')):continue
        tokens.append(token)
    if end!=len(source):raise ValueError('Incomplete or unsupported source')
    index=0;constants={}
    def take(expected=None):
        nonlocal index
        if index>=len(tokens):raise ValueError('Incomplete static source')
        token=tokens[index];index+=1
        if expected is not None and token!=expected:raise ValueError('Unsupported static syntax')
        return token
    def peek():return tokens[index] if index<len(tokens) else None
    def expression(depth=0):
        if depth>100:raise ValueError('Static data nesting too deep')
        token=take()
        if token in ('[','{'):
            array=token=='[';closing=']' if array else '}';result=[] if array else {}
            while peek()!=closing:
                if peek()=='...':
                    take();spread=expression(depth+1)
                    if not isinstance(spread,list if array else dict):raise ValueError('Invalid static spread')
                    if array:result.extend(spread)
                    else:
                        if set(spread)&set(result):raise ValueError('Duplicate static property')
                        result.update(spread)
                elif array:result.append(expression(depth+1))
                else:
                    key=take();key=js_string(key) if key.startswith(('"',"'")) else key
                    if key in ('__proto__','constructor','prototype') or key in result:raise ValueError('Unsafe or duplicate static property')
                    take(':');result[key]=expression(depth+1)
                if peek()==',':take()
                elif peek()!=closing:raise ValueError('Unsupported data expression')
            take(closing);return result
        if token.startswith(('"',"'")):return js_string(token)
        if token in ('true','false','null'):return {'true':True,'false':False,'null':None}[token]
        if token in ('-','+'):
            number=take()
            if not re.fullmatch(r'\d+(?:\.\d*)?(?:[eE][+-]?\d+)?',number):raise ValueError('Invalid numeric constant')
            return json.loads(('-' if token=='-' else '')+number)
        if token[0].isdigit():return json.loads(token)
        if token in constants:return copy.deepcopy(constants[token])
        raise ValueError('Unknown reference or executable expression')
    while peek() is not None:
        take('const');name=take()
        if not re.fullmatch(r'[A-Za-z_$][\w$]*',name) or name in constants:raise ValueError('Invalid static constant')
        take('=');constants[name]=expression();take(';')
    return constants
