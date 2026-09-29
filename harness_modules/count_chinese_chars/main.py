import re

def count_chinese_chars(text):
    if text is None:
        text = ''
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def run(params):
    text = params.get('text', '') if isinstance(params, dict) else str(params)
    return {'text': text, 'count': count_chinese_chars(text)}

if __name__ == '__main__':
    import sys, json
    print(json.dumps(run({'text': sys.argv[1]}), ensure_ascii=False))
