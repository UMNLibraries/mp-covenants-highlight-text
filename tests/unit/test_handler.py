import io
import json
import toml
import boto3
import pytest
from PIL import Image

from highlight_text import app

with open('samconfig.toml', 'r') as f:
    config = toml.load(f)
    s3_bucket = config['default']['deploy']['parameters']['s3_bucket']
    s3_region = config['default']['deploy']['parameters']['region']

s3 = boto3.client('s3')


def open_s3_image(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    im = Image.open(response['Body'])
    return im


def build_lambda_input(bucket, infile_json, orig, uuid):

    return {
        "statusCode": 200,
        "body": {
            "message": "hit test",
            "bool_hit": True,
            "bucket": bucket,
            "match_file": infile_json,
            "uuid": uuid,
            "orig": orig
        }
    }


@pytest.fixture()
def mn_wash_hit_death_cert():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits/mn-washington-county/1900 A DEEDS B121-160/1900/1900_01_01_A_NONE_DEED_121_111_2478363_SPLITPAGE_1.json",
        "raw/mn-washington-county/1900 A DEEDS B121-160/1900/1900_01_01_A_NONE_DEED_121_111_2478363_SPLITPAGE_1.tif",
        "e7a996f2d7cc484abeaf51eaa07dd096"
    )


@pytest.fixture()
def mn_anoka_hit_negro_splitpage():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits/mn-anoka-county/1/26362914_SPLITPAGE_1.json",
        "raw/mn-anoka-county/1/26362914_SPLITPAGE_1.tif",
        "0e2b9d2dea9d414e97d9c9a5ef8c70a3"
    )

@pytest.fixture()
def mn_anoka_hit_multi_term_splitpage():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits/mn-anoka-county/9/30680019.json",
        "raw/mn-anoka-county/9/30680019.tif",
        "280ebcf644c94506a65248ce70ddf9bf"
    )

@pytest.fixture()
def wi_milw_hit_handwritten():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits/wi-milwaukee-county/30000101/00997952_NOTINDEX_0001.json",
        "raw/wi-milwaukee-county/30000101/00997952_NOTINDEX_0001.tif",
        "f2b69676d7e24ae6ae451139cf913c44"
    )

@pytest.fixture()
def wi_milw_hit_handwritten_2():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits/wi-milwaukee-county/30000101/01004708_NOTINDEX_0001.json",
        "raw/wi-milwaukee-county/30000101/01004708_NOTINDEX_0001.tif",
        "bc56325e45934755973e50a92ca9929c"
    )


@pytest.fixture()
def wi_milw_hit_fuzzy_but_exact_1():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits_fuzzy/wi-milwaukee-county/17760704/DV0560_DEED_0375.json",
        "raw/wi-milwaukee-county/17760704/DV0560_DEED_0375.tif",
        "ffba76108095409e900be6682d78cc1b"
    )


@pytest.fixture()
def mn_ramsey_hit_fuzzy_but_exact_2():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits_fuzzy/mn-ramsey-county/Batch8/8424793_SPLITPAGE_2.json",
        "raw/mn-ramsey-county/Batch8/8424793_SPLITPAGE_2.tif",
        "adc149cffe2a459f9988b7a406a04fc7"
    )


@pytest.fixture()
def wi_milw_hit_fuzzy_true_fuzzy_1():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits_fuzzy/wi-milwaukee-county/30000102/01847518_NOTINDEX_0001.json",
        "raw/wi-milwaukee-county/30000102/01847518_NOTINDEX_0001.tif",
        "446fc261af534bcd9f46bfff00b5d56e"
    )


@pytest.fixture()
def mn_ramsey_hit_fuzzy_true_fuzzy_2():
    """ Generates API GW Event"""
    return build_lambda_input(
        s3_bucket,
        "ocr/hits_fuzzy/mn-ramsey-county/Batch25/19048869.json",
        "raw/mn-ramsey-county/Batch25/19048869.tif",
        "98484315261a4d8fa6177ebbb278c17e"
    )



def test_match_death_cert(mn_wash_hit_death_cert):

    ret = app.lambda_handler(mn_wash_hit_death_cert, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"
    
    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_negro_splitpage(mn_anoka_hit_negro_splitpage):

    ret = app.lambda_handler(mn_anoka_hit_negro_splitpage, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_multi_term_split(mn_anoka_hit_multi_term_splitpage):

    ret = app.lambda_handler(mn_anoka_hit_multi_term_splitpage, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_handwritten(wi_milw_hit_handwritten):

    ret = app.lambda_handler(wi_milw_hit_handwritten, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_handwritten_2(wi_milw_hit_handwritten_2):

    ret = app.lambda_handler(wi_milw_hit_handwritten_2, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_fuzzy_but_exact_1(wi_milw_hit_fuzzy_but_exact_1):

    ret = app.lambda_handler(wi_milw_hit_fuzzy_but_exact_1, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_fuzzy_but_exact_2(mn_ramsey_hit_fuzzy_but_exact_2):

    ret = app.lambda_handler(mn_ramsey_hit_fuzzy_but_exact_2, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_true_fuzzy_1(wi_milw_hit_fuzzy_true_fuzzy_1):

    ret = app.lambda_handler(wi_milw_hit_fuzzy_true_fuzzy_1, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'


def test_match_true_fuzzy_2(mn_ramsey_hit_fuzzy_true_fuzzy_2):

    ret = app.lambda_handler(mn_ramsey_hit_fuzzy_true_fuzzy_2, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert data["message"] == "highlight test success"

    # Check if image in correct mode
    im = open_s3_image(data['bucket'], data['highlighted_img'])
    assert im.mode == 'RGB'
