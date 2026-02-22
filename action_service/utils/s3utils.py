import boto3
import os
from dotenv import dotenv_values

env = dotenv_values('.env')
AWS_ACCESS_KEY = env['AWS_ACCESS_KEY_ID']   
AWS_SECRET_KEY = env['AWS_SECRET_ACCESS_KEY']
AWS_REGION = env['AWS_DEFAULT_REGION']
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)

def download_file(bucket_name, bucket_folder, folder, file):
    if not os.path.exists(folder):
        os.mkdir(folder)
    res = s3.download_file(bucket_name, bucket_folder + '/' + file, folder + '/' + file)
    return res

def upload_file(bucket_name, bucket_folder, file, uuid):
    res = s3.upload_file("outputs/" + uuid + "/" + file, bucket_name, bucket_folder + '/' + file)
    return res