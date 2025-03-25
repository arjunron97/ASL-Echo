import json

# Load the JSON files
with open('MSASL_classes.json', 'r') as file:
    classes = json.load(file)[0:10]  # Only take the first 10 classes

with open('MSASL_val.json', 'r') as file:
    data = json.load(file)

# Create a dictionary to group entries by their YouTube link
grouped_data = {}

# Process each entry in the input data
for entry in data:
    if entry["clean_text"] in classes:  # Only process entries that match the classes
        url = entry["url"]
        link_id = url.split("v=")[-1]  # Extract the video ID from the URL

        # Initialize the group if it doesn't exist
        if url not in grouped_data:
            grouped_data[url] = {
                "link": url,
                "link_id": link_id,
                "classes": {}
            }

        # Add the class data under the corresponding link
        class_name = entry["clean_text"]
        if class_name not in grouped_data[url]["classes"]:
            grouped_data[url]["classes"][class_name] = {
                "name": class_name,
                "org_text": entry["org_text"],
                "start_time": entry["start_time"],
                "start": entry["start"],
                "end": entry["end"],
                "file": entry["file"],
                "label": entry["label"],
                "height": entry["height"],
                "fps": entry["fps"],
                "end_time": entry["end_time"],
                "text": entry["text"],
                "box": entry["box"],
                "width": entry["width"]
            }

# Convert the grouped data into the desired output format
output = []
for url, details in grouped_data.items():
    entry = {
        "link": details["link"],
        "link_id": details["link_id"],
    }

    # Add each class as a separate key (class1, class2, etc.)
    for i, (class_name, class_data) in enumerate(details["classes"].items(), start=1):
        entry[f"class{i}"] = class_data

    output.append(entry)

# Save the output to a new JSON file
with open('MSASL_val_transformed.json', 'w') as file:
    json.dump(output, file, indent=4)

print("Transformation complete! Output saved to 'MSASL_transformed.json'.")