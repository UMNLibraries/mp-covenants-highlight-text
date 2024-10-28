import io
import re
import regex
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


def test_term_search(next_part, haystack, fuzzy=False):
    '''used on both lines and word objects. If fuzzy, use regex (no re) fuzzy module. If not, use basic CNTL + F search'''
    # print(fuzzy)
    # test_word = haystack_word['Text'].lower()
    if fuzzy:
        tolerance = "{e<=3}"
        next_part_fuzzy = regex.compile(f"(?:\\b{next_part}){tolerance}")
        print(next_part_fuzzy, haystack)
        if regex.search(next_part_fuzzy, haystack):
            return True
    else:
        if next_part in haystack:
            return True
    return False


def isolate_term_hit(term, line_words, fuzzy=False):
    # Make sure we are latching on to the full term match, not an incidental word that makes it up
    # This will need some work for fuzzy search
    term_split = term.strip().split(' ')
    term_parts_found = []
    words_to_highlight = []

    print(term, line_words, fuzzy)

    for word in line_words:
        print(f"Word: \"{word['Text'].lower()}\"")
        # This next line is meant to be "If this word is the next one you're looking for"
        # if re.match(f"({term_split[len(term_parts_found)]})", word['Text'].lower()):

        # TODO: edit for fuzzy?
        next_part = term_split[len(term_parts_found)]

        if test_term_search(next_part, word['Text'].lower(), fuzzy):
        # tolerance = "{e<=3}"
        # next_part_fuzzy = regex.compile(f"(?:{next_part}){tolerance}")
        # if regex.search(next_part_fuzzy, word['Text'].lower()):
        # # if next_part in word['Text'].lower():
            print(f"Found {word['Text'].lower()}")
            term_parts_found.append(term_split[len(term_parts_found)])
            words_to_highlight.append(word)
            print(len(term_parts_found), len(term_split))
            if len(term_parts_found) < len(term_split):
                # Go to next word
                pass
            elif len(term_parts_found) >= len(term_split):
                print(term_parts_found, term_split)
                if term_parts_found == term_split:
                    return words_to_highlight
                else:
                    # Nope, wrong next word, reset and move to next word
                    term_parts_found = []
                    words_to_highlight = []
    return words_to_highlight

def make_highlight_box(overlay, img_width, img_height, word_obj):

    word_box = word_obj['Geometry']['BoundingBox']
    print(word_box)

    draw = ImageDraw.Draw(overlay)

    x1 = word_box['Left'] * img_width
    y1 = word_box['Top'] * img_height
    x2 = x1 + (word_box['Width'] * img_width)
    y2 = y1 + (word_box['Height'] * img_height)

    draw.rectangle(((x1, y1), (x2, y2)), fill=(255, 255, 0, 100))

    return overlay

def add_highlights(bucket, in_path, out_path, word_objs):
    # print(bucket, in_path, word_objs)
    response = s3.get_object(Bucket=bucket, Key=in_path)
    try:
        im = Image.open(response['Body']).convert('RGBA')
    except Image.UnidentifiedImageError as err:
        raise
        return None
    
    width, height = im.size

    overlay = Image.new('RGBA', im.size)

    for word_obj in word_objs:
        overlay = make_highlight_box(overlay, width, height, word_obj)

    im = Image.alpha_composite(im, overlay)
    im = im.convert("RGB") # Remove alpha for saving in jpg format.

    out_highlight_buffer = io.BytesIO()
    im.save(out_highlight_buffer, format="JPEG")
    out_highlight_buffer.seek(0)

    # Upload resized image to destination bucket
    s3.put_object(
        Body=out_highlight_buffer,
        Bucket=bucket,
        Key=out_path,
        StorageClass='GLACIER_IR',
        ContentType='image/jpeg',
        ACL='public-read'
    )

    return out_path


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
        orig_img = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['orig'], encoding='utf-8')
        public_uuid = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['uuid'], encoding='utf-8')
        bool_hit = True
    # elif 'detail' in event:
    #     # Get object from step function with this as first step
    #     bucket = event['detail']['bucket']['name']
    #     key = event['detail']['object']['key']
    #     orig_img = event['detail']['object']['orig']
    #     public_uuid = None
    else:
        # Most common: Coming from previous step function lambda, which should be output from mp-term-search-basic
        bucket = event['body']['bucket']
        key = event['body']['match_file']
        orig_img = event['body']['orig']
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
        # ocr_json_key = key.replace('ocr/hits', 'ocr/json')
        ocr_json_key = re.sub(r'ocr/hits(?:_fuzzy)?', 'ocr/json', key)
        ocr_result = load_json(bucket, ocr_json_key)
        lines = [block for block in ocr_result['Blocks'] if block['BlockType'] == 'LINE']
        words  = [block for block in ocr_result['Blocks'] if block['BlockType'] == 'WORD']
    except Exception as e:
        print(e)
        print('Error getting ocr result json object {} from bucket {}. Make sure it exists and your bucket is in the same region as this function.'.format(ocr_json_key, bucket))
        raise e

    print(term_search_result)
    matched_term_objs = [{'term': term_key, 'line_nums': line_nums} for term_key, line_nums in term_search_result.items() if term_key not in ['workflow', 'lookup', 'uuid']]
    print(matched_term_objs)

    # print(words)
    print("Scanning for term objects on page to highlight...")
    words_to_highlight = []

    # Check if this is a fuzzy result or traditional CNTRL + F
    if 'hits_fuzzy' in key:
        print('this is fuzzy')
        fuzzy = True
    else:
        fuzzy = False

    for line_num, line in enumerate(lines):
        for term_obj in matched_term_objs:
            if line_num in term_obj['line_nums']:
            # if test_term_search(term, line['Text'].lower(), fuzzy):
            # if term in line['Text'].lower():
                print(f"\nChecking for term {term_obj['term']} in line {line_num}\n")
                # print(line)
                word_children = [objs['Ids'] for objs in line['Relationships'] if objs['Type'] == 'CHILD']
                if len(word_children) > 0:
                    # print(f"Word children: {word_children}")
                    line_words = [word for word in words if word['Id'] in word_children[0]]

                    # Make sure we are latching on to the full term match, not an incidental word that makes it up
                    words_to_highlight += isolate_term_hit(term_obj['term'], line_words, fuzzy)

    print(words_to_highlight)

    if len(words_to_highlight) > 0:
        print(f"Found {len(words_to_highlight)} words to highlight.")

        img_in_path = str(PurePath(re.sub(r'ocr/hits(?:_fuzzy)?', 'web', key)).with_name(public_uuid + '.jpg'))
        img_out_path = str(PurePath(re.sub(r'ocr/hits(?:_fuzzy)?', 'web_highlighted', key)).with_name(public_uuid + '__highlight.jpg'))
        highlight_key = add_highlights(bucket, img_in_path, img_out_path, words_to_highlight)

        status = 200
        message = "highlight test success"

    else:
        status = 400
        message = 'Error: No highlightable text found'
        highlight_key = None

    return {
        "statusCode": status,
        "body": {
            "message": message,
            "bucket": bucket,
            "orig_img": orig_img,
            "highlighted_img": highlight_key,
            "uuid": public_uuid
        }
    }
