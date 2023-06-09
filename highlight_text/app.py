import io
import sys
import json
import math
import uuid
import urllib.parse
import boto3
from pathlib import PurePath
from PIL import Image, ImageFont, ImageDraw

print('Loading function')

s3 = boto3.client('s3')
Image.MAX_IMAGE_PIXELS = 1000000000


def load_json(bucket, key):
    content_object = s3.get_object(Bucket=bucket, Key=key)
    file_content = content_object['Body'].read().decode('utf-8')
    return json.loads(file_content)


def isolate_term_hit(term, line_words):
    # Make sure we are latching on to the full term match, not an incidental word that makes it up
    term_split = term.strip().split(' ')
    term_parts_found = []
    words_to_highlight = []

    for word in line_words:
        # print(f"Word: \"{word['Text'].lower()}\"")
        # This next line is meant to be "If this word is the next one you're looking for"
        if word['Text'].lower() == term_split[len(term_parts_found)]:
            # print(f"Found {word['Text'].lower()}")
            term_parts_found.append(word['Text'].lower())
            words_to_highlight.append(word)
            if len(term_parts_found) < len(term_split):
                # Go to next word
                pass
            elif len(term_parts_found) >= len(term_split):
                if term_parts_found == term_split:
                    return words_to_highlight
                else:
                    # Nope, wrong next word, reset and move to next word
                    term_parts_found = []
                    words_to_highlight = []
    return False

def add_highlights(bucket, in_path, out_path, word_objs):
    response = s3.get_object(Bucket=bucket, Key=in_path)
    print("CONTENT TYPE: " + response['ContentType'])
    try:
        im = Image.open(in_tiff_body)
    except Image.UnidentifiedImageError as err:
        raise
        return None


        # return response['ContentType']
        #
        # # print(key, key.replace('.tif', '.jpg'))
        #
        # out_jpg_buffer = save_jpeg_to_target_size(
        #     key, response['Body'], 1000000, True, True)
    return False

def lambda_handler(event, context):
    '''
    General idea...
    1. Using incoming hit data, determine if bool_hit is true or not (possibly make this a conditional of step function)
    2. Use ocr JSON to determine location of terms
    2. Retrieve web-optimized image using uuid
    3. Highlight by proportional resizing
    4. Save out a copy of web image with same UUID, with something like foo_highlight_<uuid>
    '''

    if 'Records' in event:
        # Get the object from a more standard put event/test
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        public_uuid = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['uuid'], encoding='utf-8')
        bool_hit = True
    # elif 'detail' in event:
    #     # Get object from step function with this as first step
    #     bucket = event['detail']['bucket']['name']
    #     key = event['detail']['object']['key']
    #     public_uuid = None
    else:
        # Most common: Coming from previous step function lambda, which should be output from mp-term-search-basic
        bucket = event['body']['bucket']
        key = event['body']['json']
        public_uuid = event['body']['uuid']
        bool_hit = event['body']['bool_hit']

    # Get term search result json
    try:
        term_search_result = load_json(bucket, key)
    except Exception as e:
        print(e)
        print('Error getting term search object {} from bucket {}. Make sure it exists and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

    # Get OCR json data
    try:
        ocr_json_key = key.replace('ocr/hits', 'ocr/json')
        ocr_result = load_json(bucket, ocr_json_key)
        lines = [block for block in ocr_result['Blocks'] if block['BlockType'] == 'LINE']
        words  = [block for block in ocr_result['Blocks'] if block['BlockType'] == 'WORD']
    except Exception as e:
        print(e)
        print('Error getting ocr result json object {} from bucket {}. Make sure it exists and your bucket is in the same region as this function.'.format(ocr_json_key, bucket))
        raise e

    print(term_search_result)
    matched_terms = [key for key in term_search_result.keys() if key not in ['workflow', 'lookup', 'uuid']]
    print(matched_terms)

    # print(words)
    print("Scanning for term objects on page to highlight...")
    words_to_highlight = []

    for line_num, line in enumerate(lines):
        for term in matched_terms:
            if term in line['Text'].lower():
                # print(f'\nFound term {term} in line {line_num}\n')
                # print(line)
                word_children = [objs['Ids'] for objs in line['Relationships'] if objs['Type'] == 'CHILD']
                if len(word_children) > 0:
                    # print(f"Word children: {word_children}")
                    line_words = [word for word in words if word['Id'] in word_children[0]]

                    # Make sure we are latching on to the full term match, not an incidental word that makes it up
                    words_to_highlight += isolate_term_hit(term, line_words)

    print(words_to_highlight)

    if len(words_to_highlight) > 0:
        print(f"Found {len(words_to_highlight)} words to highlight.")

        # img_in_path = key.replace('ocr/hits', 'web').replace('.json', f"{uuid}.jpg")
        img_in_path = str(PurePath(key.replace('ocr/hits', 'web')).with_name(public_uuid + '.jpg'))
        img_out_path = str(PurePath(key.replace('ocr/hits', 'web')).with_name(public_uuid + '__highlight.jpg'))
        highlight_key = add_highlights(bucket, in_path, out_path, word_objs)

    return {
        "statusCode": 200,
        "body": {
            "message": "hello world",
            "bucket": bucket,
            "orig_img": key,
            "highlighted_img": highlight_key,
            "uuid": public_uuid
            # "location": ip.text.replace("\n", "")
        }
    }
