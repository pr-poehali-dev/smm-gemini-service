import json
import os
import google.generativeai as genai

def handler(event: dict, context) -> dict:
    '''Генерирует полный документ на основе утвержденной структуры с помощью Gemini 2.5 Flash'''
    
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        doc_type = body.get('docType', 'реферат')
        subject = body.get('subject', '')
        pages = body.get('pages', 10)
        topics = body.get('topics', [])
        additional_info = body.get('additionalInfo', '')
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана тема документа'})
            }
        
        if not topics or len(topics) == 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана структура документа'})
            }
        
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'API ключ не настроен'})
            }
        
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        topics_structure = '\n'.join([
            f"{i+1}. {topic['title']}\n   {topic['description']}"
            for i, topic in enumerate(topics)
        ])
        
        chars_per_page = 1800
        target_chars = pages * chars_per_page
        chars_per_section = target_chars // len(topics)
        
        prompt = f"""Напиши академический {doc_type} на тему: {subject}

СТРУКТУРА ДОКУМЕНТА:
{topics_structure}

ТРЕБОВАНИЯ:
- Общий объем: примерно {pages} страниц А4 (~{target_chars} символов)
- На каждый раздел: ~{chars_per_section} символов
- Академический стиль, научная терминология
- Логичное изложение с примерами
- Между разделами должна быть связь
- НЕ нужно оглавление, список литературы или титульный лист
- Начинай сразу с введения и основных разделов

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Формат ответа:
ВВЕДЕНИЕ
[текст введения]

1. [Название первого раздела]
[полный текст раздела]

2. [Название второго раздела]
[полный текст раздела]

...

ЗАКЛЮЧЕНИЕ
[текст заключения]

Пиши подробно, раскрывай каждую тему полностью. Используй абзацы для структуры."""

        response = model.generate_content(prompt)
        document = response.text.strip()
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'document': document}, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка генерации: {str(e)}'})
        }
