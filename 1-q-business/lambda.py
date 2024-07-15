import json

def lambda_handler(event, context):
    http_method = event["requestContext"]["http"]["method"]
    
    if http_method == "GET":
        print('GET param is ', event["requestContext"]["http"]['path'])

        return {
            "statusCode": 200,
            "body": json.dumps("GET request received")
        }
    
    elif http_method == "POST":
        body = json.loads(event["body"])
        print('POST body is ', body)

        return {
            "statusCode": 200,
            "body": json.dumps(f"POST request received with data: {body}")
        }
    else:
        return {
            "statusCode": 405,
            "body": json.dumps("Method not allowed")
        }
