import requests
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
    table = dynamodb.Table("EarthquakeData")

    # Fetch data from API
    response = requests.get(url)

    if response.status_code == 200:

        # Convert response to JSON
        data = response.json()

        # Upload raw JSON to S3
        s3.put_object(
            Bucket="shalini-earthquake-etl-2026",
            Key="raw_data/earthquakes.json",
            Body=json.dumps(data, indent=4),
            ContentType="application/json"
        )

        print("Raw JSON uploaded to S3 successfully!")

        # List to store processed records
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

            # Convert timestamp to readable UTC time
            readable_time = datetime.fromtimestamp(time / 1000, UTC)

            longitude = earthquake["geometry"]["coordinates"][0]
            latitude = earthquake["geometry"]["coordinates"][1]
            depth = earthquake["geometry"]["coordinates"][2]

            # Create cleaned record
            record = {
                "id": earthquake_id,
                "magnitude": Decimal(str(magnitude)),
                "place": place,
                "time": str(readable_time),
                "longitude": Decimal(str(longitude)),
                "latitude": Decimal(str(latitude)),
                "depth": Decimal(str(depth))
            }

            # Save in list
            processed_records.append(record)

            # Store in DynamoDB
            table.put_item(Item=record)

        print("All processed earthquake records stored in DynamoDB successfully!")
        print(f"Total Processed Records: {len(processed_records)}")

        print("\nFirst 3 Records:")
        for record in processed_records[:3]:
            print(record)

    else:
        print("Error:", response.status_code)


if __name__ == "__main__":
    lambda_handler(None, None)