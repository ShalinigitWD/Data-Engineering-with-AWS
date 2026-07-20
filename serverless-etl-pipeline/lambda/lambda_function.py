import urllib.request
import boto3
import json
from decimal import Decimal
from datetime import datetime, UTC


def lambda_handler(event, context):

    # USGS Earthquake API (Last 7 Days)
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"

    # Create S3 client
    s3 = boto3.client("s3", region_name="ap-south-1")

    # Connect to DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
    table = dynamodb.Table("EarthquakeEvents")

    # Fetch data from API
    response = urllib.request.urlopen(url)

    if response.status == 200:

        # Convert response to JSON
        data = json.loads(response.read().decode("utf-8"))

        # Upload raw JSON to S3
        s3.put_object(
            Bucket="shalini-earthquake-etl-data",
            Key="raw_data/earthquakes.json",
            Body=json.dumps(data, indent=4),
            ContentType="application/json"
        )

        print("Raw JSON uploaded to S3 successfully!")

        processed_records = []

        # Process each earthquake
        for earthquake in data["features"]:

            earthquake_id = earthquake["id"]
            magnitude = earthquake["properties"]["mag"]

            # Skip earthquakes below magnitude 4.0
            if magnitude is None or magnitude < 4.0:
                continue

            place = earthquake["properties"]["place"]
            time = earthquake["properties"]["time"]

            readable_time = datetime.fromtimestamp(time / 1000, UTC)

            longitude = earthquake["geometry"]["coordinates"][0]
            latitude = earthquake["geometry"]["coordinates"][1]
            depth = earthquake["geometry"]["coordinates"][2]

            record = {
                "event_id": earthquake_id,
                "magnitude": Decimal(str(magnitude)),
                "place": place,
                "time": str(readable_time),
                "longitude": Decimal(str(longitude)),
                "latitude": Decimal(str(latitude)),
                "depth": Decimal(str(depth))
            }

            processed_records.append(record)

            table.put_item(Item=record)

        print(f"Successfully processed {len(processed_records)} earthquake records.")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "ETL completed successfully",
                    "records_processed": len(processed_records),
                }
            ),
        }

    else:
        return {
            "statusCode": response.status,
            "body": json.dumps("Failed to fetch earthquake data")
        }