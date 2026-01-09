import json
import os
import google.generativeai as genai

def handler(event: dict, context) -> dict:
    '''Генерирует структуру или полный документ с помощью Gemini 2.5 Flash'''
    
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
            'body': '',
            'isBase64Encoded': False
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        mode = body.get('mode', 'document')
        doc_type = body.get('docType', 'реферат')
        subject = body.get('subject', '')
        pages = body.get('pages', 10)
        topics = body.get('topics', [])
        additional_info = body.get('additionalInfo', '')
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана тема документа'}),
                'isBase64Encoded': False
            }
        
        if mode == 'document' and (not topics or len(topics) == 0):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана структура документа'}),
                'isBase64Encoded': False
            }
        
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'API ключ не настроен'}),
                'isBase64Encoded': False
            }
        
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        if mode == 'topics':
            sections_count = max(3, pages // 3)
            prompt = f"""Создай структуру для документа типа "{doc_type}" на тему: {subject}

Документ должен быть объемом примерно {pages} страниц А4.

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Верни ТОЛЬКО валидный JSON массив из {sections_count} объектов:
[
  {{
    "title": "Название раздела",
    "description": "Краткое описание содержания раздела"
  }}
]

Без введения/заключения - только основные разделы.
Названия лаконичные. Описания информативные (2-3 предложения).

ВАЖНО: Верни ТОЛЬКО JSON, без markdown или комментариев!"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            topics_result = json.loads(result_text)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'topics': topics_result}, ensure_ascii=False),
                'isBase64Encoded': False
            }
        else:
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
                'body': json.dumps({'document': document}, ensure_ascii=False),
                'isBase64Encoded': False
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка генерации: {str(e)}'}),
            'isBase64Encoded': False
        }