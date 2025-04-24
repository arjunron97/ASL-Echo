# main.py
import os
import csv
import io
from google.cloud import storage
import logging  # Using logging module for better practice

# --- Configuration (Use Environment Variables) ---
# Set these in your function's deployment configuration
BUCKET_NAME = os.environ.get("BUCKET_NAME",
                             "your-gcs-bucket-name")  # Replace with your actual bucket name or set via env var
INPUT_CSV_PATH = os.environ.get("INPUT_CSV_PATH", "Texas_Flood_Data_Results.csv")
OUTPUT_CSV_PATH = os.environ.get("OUTPUT_CSV_PATH", "test_save_file.csv")  # Your temporary output file name
LAT_COLUMN = os.environ.get("LAT_COLUMN", "BEGIN_LAT")
LON_COLUMN = os.environ.get("LON_COLUMN", "BEGIN_LON")
# --------------------------------------------------

# Configure basic logging
logging.basicConfig(level=logging.INFO)  # Logs INFO level and above (INFO, WARNING, ERROR, CRITICAL)

# Initialize GCS Client globally (recommended practice)
try:
    storage_client = storage.Client()
except Exception as e:
    logging.critical(f"Failed to initialize Google Cloud Storage client: {e}")
    # Depending on function trigger, might want to raise or handle differently
    storage_client = None


# === PLACEHOLDER: Your Processing Function ===
def get_weather_and_elevation(lat, lon, date='today'):
    """
    Fetches weather and elevation data for given coordinates.
    Note: Date parameter is currently not used (defaults to current weather).
    """
    result = {
        # Weather data
        'rain_1h': 0,
        'rain_3h': 0,
        'snow_1h': 0,
        'snow_3h': 0,
        'temp': None,
        'feels_like': None,
        'temp_min': None,
        'temp_max': None,
        'humidity': None,
        'wind_speed': None,
        'wind_deg': None,
        'wind_gust': None,
        'clouds_all': None,
        'pressure': None,

        # Elevation data
        'elevation': None,
        'latitude': lat,
        'longitude': lon,
        'timestamp': int(time.time()),

        # Error handling
        'errors': []
    }

    # OpenWeatherMap API call
    API_KEY = "2aec98fb1055e00ebb5e277d74ff175b"
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"

    try:
        weather_response = requests.get(weather_url)
        if weather_response.status_code == 200:
            weather_data = weather_response.json()

            # Extract precipitation data
            rain = weather_data.get('rain', {})
            result['rain_1h'] = rain.get('1h', 0)
            result['rain_3h'] = rain.get('3h', 0)

            snow = weather_data.get('snow', {})
            result['snow_1h'] = snow.get('1h', 0)
            result['snow_3h'] = snow.get('3h', 0)

            # Extract main weather data
            main = weather_data.get('main', {})
            result['temp'] = main.get('temp')
            result['feels_like'] = main.get('feels_like')
            result['temp_min'] = main.get('temp_min')
            result['temp_max'] = main.get('temp_max')
            result['humidity'] = main.get('humidity')
            result['pressure'] = main.get('pressure')

            # Extract wind data
            wind = weather_data.get('wind', {})
            result['wind_speed'] = wind.get('speed')
            result['wind_deg'] = wind.get('deg')
            result['wind_gust'] = wind.get('gust')

            # Extract cloud data
            clouds = weather_data.get('clouds', {})
            result['clouds_all'] = clouds.get('all')
        else:
            try:
                error_data = weather_response.json()
                error_msg = error_data.get('message', 'Unknown error')
            except:
                error_msg = 'Unknown error'
            result['errors'].append(f"Weather API Error: {error_msg}")
    except Exception as e:
        result['errors'].append(f"Weather API Exception: {str(e)}")

    # Open-Elevation API call
    elevation_url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"

    try:
        elevation_response = requests.get(elevation_url)
        if elevation_response.status_code == 200:
            elevation_data = elevation_response.json()
            result['elevation'] = elevation_data.get('results', [{}])[0].get('elevation')
        else:
            try:
                error_data = elevation_response.json()
                error_msg = error_data.get('error', 'Unknown error')
            except:
                error_msg = 'Unknown error'
            result['errors'].append(f"Elevation API Error: {error_msg}")
    except Exception as e:
        result['errors'].append(f"Elevation API Exception: {str(e)}")

    return result


# ============================================

def read_csv_from_gcs(bucket_name, file_path):
    """Downloads CSV from GCS and yields rows as dictionaries."""
    if not storage_client:
        raise ConnectionError("GCS client not initialized.")
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        if not blob.exists():
            logging.error(f"Input file not found in GCS: gs://{bucket_name}/{file_path}")
            raise FileNotFoundError(f"gs://{bucket_name}/{file_path} not found.")

        logging.info(f"Reading input CSV: gs://{bucket_name}/{file_path}")
        # Download content as string and use StringIO for csv reader
        blob_content = blob.download_as_text()
        csv_file = io.StringIO(blob_content)
        reader = csv.DictReader(csv_file)
        yield from reader  # Yield rows one by one (memory efficient for reading)

    except FileNotFoundError:
        raise  # Re-raise specific error
    except Exception as e:
        logging.error(f"Error reading CSV from GCS (gs://{bucket_name}/{file_path}): {e}")
        raise RuntimeError(f"Failed to read GCS CSV: {e}")


# def write_dicts_to_csv_in_gcs(bucket_name, file_path, data_dicts):
#     """Writes list of dictionaries to a CSV file in GCS, overwriting if exists."""
#     if not storage_client:
#         raise ConnectionError("GCS client not initialized.")
#     if not data_dicts:
#         logging.warning("No data provided to write to CSV. Output file will not be created/updated.")
#         return

#     try:
#         bucket = storage_client.bucket(bucket_name)
#         blob = bucket.blob(file_path)

#         # Get fieldnames from the keys of the first dictionary
#         # Assumes all dictionaries in the list have the same keys
#         fieldnames = list(data_dicts[0].keys())

#         logging.info(f"Writing {len(data_dicts)} records to output CSV: gs://{bucket_name}/{file_path}")

#         # Use StringIO to build CSV in memory
#         output_stream = io.StringIO()
#         writer = csv.DictWriter(output_stream, fieldnames=fieldnames, lineterminator='\n')

#         writer.writeheader() # Write the header row
#         writer.writerows(data_dicts) # Write all data rows

#         # Upload the stream content to GCS (overwrites existing blob)
#         blob.upload_from_string(output_stream.getvalue(), content_type='text/csv')
#         logging.info(f"Successfully wrote output CSV: gs://{bucket_name}/{file_path}")

#     except Exception as e:
#         logging.error(f"Error writing CSV to GCS (gs://{bucket_name}/{file_path}): {e}")
#         raise RuntimeError(f"Failed to write GCS CSV: {e}")
#     finally:
#         if 'output_stream' in locals() and not output_stream.closed:
#             output_stream.close()


def write_dicts_to_csv_in_gcs(bucket_name, file_path, new_data_dicts):
    """
    Reads existing CSV from GCS (if any), finds max 'id', assigns auto-incrementing
    IDs to new data, and writes the combined data back, overwriting the file.
    """
    if not storage_client:
        # Ensure client is available before proceeding
        logging.critical("GCS client not initialized in write_dicts_to_csv_in_gcs.")
        raise ConnectionError("GCS client not initialized.")

    # If there's no new data, there's nothing to add or update.
    if not new_data_dicts:
        logging.warning("No new data provided to write to CSV. File remains unchanged.")
        return

    max_existing_id = 0
    existing_rows = []  # To store rows read from existing file
    # Define the columns for the output file based on the new data, adding 'id' first.
    # Assumes all dictionaries in new_data_dicts have the same keys.
    output_fieldnames = ['id'] + list(new_data_dicts[0].keys())
    logging.info(f"Output CSV columns structure: {output_fieldnames}")

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        # --- Step 1 & 2: Read existing file and find max ID ---
        if blob.exists():
            logging.info(f"Reading existing file to find last ID: gs://{bucket_name}/{file_path}")
            try:
                existing_content = blob.download_as_text()
                # Proceed only if file has content beyond whitespace
                if existing_content and existing_content.strip():
                    existing_file = io.StringIO(existing_content)
                    reader = csv.DictReader(existing_file)

                    # Check if existing headers are compatible (optional check)
                    if reader.fieldnames:
                        logging.debug(f"Existing file headers found: {reader.fieldnames}")
                        if 'id' not in reader.fieldnames:
                            # Log a warning if 'id' column is missing in existing file
                            logging.warning(
                                f"Existing file gs://{bucket_name}/{file_path} is missing the 'id' column. Assuming starting ID is 0.")

                    # Read rows and find the maximum 'id'
                    for i, row in enumerate(reader):
                        existing_rows.append(row)  # Store existing data to write back later
                        try:
                            # Safely get 'id', default to '0' if key missing or value is None/empty
                            current_id_str = row.get('id', '0')
                            current_id_str = current_id_str.strip() if current_id_str else '0'

                            if current_id_str:  # Attempt conversion if not empty
                                current_id = int(current_id_str)
                                if current_id > max_existing_id:
                                    max_existing_id = current_id
                            # If current_id_str is empty after strip, it defaults to 0 logic

                        except ValueError:
                            # Log if 'id' value is not a valid integer
                            logging.warning(
                                f"Row {i + 1} in existing file has non-integer 'id': '{row.get('id', '')}'. Ignoring for max ID calculation.")
                        except Exception as e_inner:
                            # Catch any other unexpected errors processing the row's ID
                            logging.warning(
                                f"Error processing 'id' in existing file row {i + 1}: {e_inner}. Ignoring for max ID calculation.")
                else:
                    # File exists but is empty or contains only whitespace
                    logging.info(f"Existing file gs://{bucket_name}/{file_path} is empty. Starting IDs from 1.")

            except Exception as e_read:
                # Handle errors during reading (e.g., network issues, corrupted data)
                logging.error(
                    f"Error reading existing CSV from GCS (gs://{bucket_name}/{file_path}): {e_read}. Proceeding as if file didn't exist (max_id=0).")
                existing_rows = []  # Discard any partially read data
                max_existing_id = 0  # Reset max_id
        else:
            # File does not exist
            logging.info(
                f"Output file gs://{bucket_name}/{file_path} does not exist. Will create new file starting IDs from 1.")
            # max_existing_id remains 0

        # --- Step 3: Assign IDs to new data ---
        logging.info(f"Max existing ID determined as {max_existing_id}. Starting new IDs from {max_existing_id + 1}.")
        new_rows_with_ids = []
        # Iterate through the new data provided to the function
        for i, new_item_dict in enumerate(new_data_dicts):
            # Calculate the next ID
            current_id = max_existing_id + i + 1
            # Create the new row dictionary: put 'id' first, then merge the rest
            row_to_add = {'id': current_id, **new_item_dict}
            new_rows_with_ids.append(row_to_add)

        # --- Step 4 & 5: Combine and write back ---
        logging.info(
            f"Preparing to write {len(existing_rows)} existing + {len(new_rows_with_ids)} new records to: gs://{bucket_name}/{file_path}")

        output_stream = io.StringIO()
        # Use fieldnames derived from the NEW data structure (plus 'id')
        # This ensures the output file conforms to the latest expected format.
        writer = csv.DictWriter(output_stream, fieldnames=output_fieldnames, lineterminator='\n')

        writer.writeheader()  # Write the header row based on output_fieldnames

        # Write the original rows first (if any)
        if existing_rows:
            try:
                # DictWriter will only write columns specified in output_fieldnames.
                # If existing rows have extra columns, they are ignored.
                # If existing rows are MISSING columns from output_fieldnames, it writes empty values for those.
                writer.writerows(existing_rows)
            except ValueError as ve:
                # This error typically happens if a row dict contains a key NOT in fieldnames AND extrasaction='raise' (default)
                # Since our fieldnames are based on the NEW data, this shouldn't happen unless existing data is malformed unexpectedly.
                logging.error(
                    f"Error writing existing rows - possible column mismatch: {ve}. Check if existing data keys are valid.")
                # Depending on desired behavior, you might re-raise or log and continue
                raise RuntimeError(f"Error writing existing rows due to column mismatch: {ve}")

        # Write the new rows with their generated IDs
        writer.writerows(new_rows_with_ids)

        # Upload the complete CSV content, overwriting the blob
        blob.upload_from_string(output_stream.getvalue(), content_type='text/csv')
        logging.info(f"Successfully wrote/updated CSV: gs://{bucket_name}/{file_path}")

    except ConnectionError:  # Re-raise specific known errors
        logging.critical("GCS Connection Error during write operation.")
        raise
    except Exception as e:
        # Catch any other unexpected errors during the write process
        logging.exception(
            f"An unexpected error occurred while writing CSV to GCS (gs://{bucket_name}/{file_path}): {e}")  # Use .exception to log traceback
        raise RuntimeError(f"Failed to write GCS CSV: {e}")
    finally:
        # Ensure the in-memory stream is always closed
        if 'output_stream' in locals() and not output_stream.closed:
            output_stream.close()


# --- Cloud Function Entry Point ---
# Triggered by HTTP request (adapt if using Pub/Sub, etc.)
def process_flood_data_coordinates(request):
    """
    Main Cloud Function logic.
    Reads input CSV, finds unique lat/lon, processes them, writes output CSV.
    """
    logging.info("Cloud Function execution started.")

    if not storage_client:
        logging.critical("GCS client failed to initialize. Aborting function.")
        return "Internal Server Error: GCS Client unavailable", 500

    unique_coords = set()
    results_list = []

    try:
        # 1. Read input CSV and extract unique coordinates
        logging.info(f"Attempting to read {LAT_COLUMN} and {LON_COLUMN} columns.")
        row_count = 0
        for row in read_csv_from_gcs(BUCKET_NAME, INPUT_CSV_PATH):
            row_count += 1
            try:
                # Get lat/lon, convert to float for potential numeric processing later
                # Handle potential empty strings or invalid values gracefully
                lat_str = row.get(LAT_COLUMN, '').strip()
                lon_str = row.get(LON_COLUMN, '').strip()

                if lat_str and lon_str:  # Only process if both values are present
                    lat = float(lat_str)
                    lon = float(lon_str)
                    unique_coords.add((lat, lon))
                else:
                    logging.warning(
                        f"Skipping row {row_count}: Missing or empty lat/lon ({LAT_COLUMN}={lat_str}, {LON_COLUMN}={lon_str})")

            except KeyError as e:
                # Log if expected column name is missing entirely
                logging.error(
                    f"Missing expected column in input CSV: {e}. Check LAT_COLUMN/LON_COLUMN env vars and CSV headers.")
                # Depending on requirements, you might want to stop execution here
                return f"Input CSV Column Error: {e}", 400  # Bad Request
            except ValueError as e:
                logging.warning(
                    f"Skipping row {row_count}: Invalid numeric value for lat/lon ({LAT_COLUMN}={lat_str}, {LON_COLUMN}={lon_str}) - {e}")
            except Exception as e:
                # Catch other potential errors during row processing
                logging.error(f"Error processing row {row_count}: {e}")
                # Decide whether to skip row or halt execution

        logging.info(f"Found {len(unique_coords)} unique coordinate pairs from {row_count} rows.")

        # 2. Process unique coordinates
        if not unique_coords:
            logging.warning("No unique coordinates found or extracted. No processing needed.")
        else:
            processed_count = 0
            for lat, lon in unique_coords:
                try:
                    result_dict = get_weather_and_elevation(lat=lat, lon=lon)
                    if result_dict and isinstance(result_dict, dict):  # Basic check
                        results_list.append(result_dict)
                        processed_count += 1
                    else:
                        logging.warning(
                            f"Processing function did not return a valid dictionary for ({lat}, {lon}). Skipping.")
                except Exception as e:
                    # Catch errors from within your process_lat_lon function
                    logging.error(f"Error processing coordinates ({lat}, {lon}): {e}")
                    # Decide if you want to skip this pair or halt execution
            logging.info(f"Successfully processed {processed_count} coordinate pairs.")

        # 3. Write results to output CSV (only if there are results)
        if results_list:
            write_dicts_to_csv_in_gcs(BUCKET_NAME, OUTPUT_CSV_PATH, results_list)
        else:
            logging.info("No results generated, output CSV file was not written.")

        logging.info("Cloud Function execution finished successfully.")
        return "Processing complete.", 200

    except FileNotFoundError as e:
        logging.error(f"Function failed: Input file not found - {e}")
        return f"Error: Input file missing - {e}", 404  # Not Found
    except ConnectionError as e:
        logging.critical(f"Function failed: GCS connection error - {e}")
        return "Internal Server Error: GCS Connection", 500
    except RuntimeError as e:
        logging.error(f"Function failed: Runtime error during GCS I/O - {e}")
        return f"Internal Server Error: {e}", 500
    except Exception as e:
        # Catch any other unexpected errors during the main flow
        logging.exception(f"An unexpected error occurred: {e}")  # Use logging.exception to include traceback
        return f"Internal Server Error: {e}", 500