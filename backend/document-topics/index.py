import json
import os
import google.generativeai as genai

def handler(event: dict, context) -> dict:
    '''Генерирует структуру документа (темы разделов) с помощью Gemini 2.5 Flash'''
    
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
        additional_info = body.get('additionalInfo', '')
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана тема документа'})
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
        
        prompt = f"""Создай структуру для документа типа "{doc_type}" на тему: {subject}

Документ должен быть объемом примерно {pages} страниц А4.

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Верни ТОЛЬКО валидный JSON массив объектов с такой структурой:
[
  {{
    "title": "Название раздела",
    "description": "Краткое описание содержания раздела"
  }}
]

Создай {max(3, pages // 3)} разделов для полного раскрытия темы. Без введения/заключения - только основные разделы.
Названия делай лаконичными и конкретными. Описания должны быть информативными (2-3 предложения).

ВАЖНО: Верни ТОЛЬКО JSON, без дополнительного текста, markdown или комментариев!"""

        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith('```'):
            lines = result_text.split('\n')
            result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        topics = json.loads(result_text)
        
        if not isinstance(topics, list):
            raise ValueError('Неверный формат ответа от AI')
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'topics': topics}, ensure_ascii=False)
        }
        
    except json.JSONDecodeError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка парсинга JSON: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка генерации: {str(e)}'})
        }
