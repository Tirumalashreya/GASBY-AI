import boto3

s3 = boto3.client("s3")
buckets = s3.list_buckets()

print("Buckets found:")
for b in buckets["Buckets"]:
    print("-", b["Name"])


