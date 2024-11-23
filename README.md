This script can convert the sleep data from your Apple Watch to the format of the Dreem headband.
This enables software like OSCAR to import it.

One should provide input files from the Apple Watch using the Auto Export iOS app: 
https://apps.apple.com/nl/app/health-auto-export-json-csv/id1115567069

App Settings: 
Select only Sleep Metrics (Sleep Analysis) for export
Export Format: JSON
Aggregate Data: False

AppleWatch2Dreem Script
Description
The AppleWatch2Dreem.py script is designed to convert sleep data exported from Apple Health (specifically from the Apple Watch) into a format compatible with Dreem, a sleep analysis platform. The script processes JSON files containing sleep metrics and generates CSV files with sleep segments and statistics.

Features
Parses Apple Health sleep data exported in JSON format.
Groups sleep data by night, considering sleep sessions from 19:00 to 11:00 the next day.
Handles time zones and time shifts, ensuring accurate time representation.
Generates CSV files containing detailed sleep analysis compatible with Dreem.
Automatically renames processed files to prevent reprocessing.
Prerequisites
Python 3.6 or higher
Required Python libraries:
python-dateutil
Installation
Clone or download the script to your local machine.
Install the required libraries using pip:
pip install python-dateutil
Usage
The script can be run from the command line with various options. Below is the syntax and explanation of each option.

Command Line Syntax
python Apple2Dreem.py [options]
Options
-i, --input
Description: Specify the input folder containing the JSON files.
Default: Current directory (.)
Usage:

python Apple2Dreem.py -i path/to/input_folder
-o, --output
Description: Specify the output folder where CSV files will be saved.
Default: Same as input folder
Usage:

python Apple2Dreem.py -o path/to/output_folder
-f, --from
Description: Specify the start date and time for processing data.
Format: yyyy-MM-dd or yyyy-MM-dd-HH:mm
Default: Yesterday at 19:00
Usage:

python Apple2Dreem.py -f 2024-11-22
python Apple2Dreem.py -f 2024-11-22-19:00
-t, --to
Description: Specify the end date and time for processing data.
Format: yyyy-MM-dd or yyyy-MM-dd-HH:mm
Default: Today at 11:00
Usage:

python Apple2Dreem.py -t 2024-11-23
python Apple2Dreem.py -t 2024-11-23-11:00
-l, --filter
Description: Specify the input file filter (supports wildcards).
Default: HealthAutoExport-*.json
Usage:

python Apple2Dreem.py -l "MyHealthData-*.json"
-s, --shift
Description: Specify a time shift in seconds to adjust the timestamps in the data.
Default: 0 seconds
Usage:

python Apple2Dreem.py -s 3600  # Shift time by 1 hour forward
python Apple2Dreem.py -s -1800 # Shift time by 30 minutes backward
-h, --help
Description: Display the help message and exit.
Usage:

python Apple2Dreem.py -h
Examples
Process all default JSON files in the current directory with default dates and no time shift:

python Apple2Dreem.py
Process files in a specific input folder and output to a different folder:

python Apple2Dreem.py -i ./input_folder -o ./output_folder
Process data from a specific date range with a time shift of 1 hour forward:

python Apple2Dreem.py -f 2024-11-22 -t 2024-11-23 -s 3600
Use a custom file filter to process specific files:

python Apple2Dreem.py -l "MySleepData-2024-*.json"
Default Values
If no options are specified, the script uses the following default values:

Input folder: Current directory (.)
Output folder: Same as input folder
File filter: HealthAutoExport-*.json
From date: Yesterday at 19:00 (7:00 PM)
To date: Today at 11:00 (11:00 AM)
Time shift: 0 seconds (no shift)
How the Script Works
File Selection: The script searches for JSON files in the input folder that match the specified file filter.

Data Parsing:

Reads each JSON file.
Parses sleep data entries, converting date strings into datetime objects.
Ensures all datetime objects are timezone-aware.
Grouping Sleep Data:

Groups sleep data entries by night, considering sessions from 19:00 to 11:00 the next day.
Applies the specified date range (from_date and to_date).
Processing Sleep Segments:

Creates 30-second segments between the start and end times.
Maps sleep stages from the data to standard stages (Light, Deep, REM, etc.).
Updates segments with sleep stage information.
Calculating Sleep Statistics:

Calculates total sleep duration, sleep onset duration, durations of different sleep stages, wake after sleep onset, and number of awakenings.
Generates a hypnogram representing sleep stages over time.
Generating Output:

Writes the processed data to a CSV file in the output folder.
The CSV file contains headers and a row with the calculated sleep statistics.
File Management:

Renames the processed JSON files by prefixing them with an underscore (_) to prevent reprocessing.
Notes
Time Zones: The script handles time zones by ensuring all datetime objects are timezone-aware. If the time zone information is missing, it assumes the local time zone.
Date Formats: The script is flexible with date formats, using dateutil.parser.parse to handle various date and time representations.
Error Handling: The script includes warnings and error messages to help identify and troubleshoot issues with data parsing or file processing.
Troubleshooting
Invalid Date Formats: If you receive warnings about invalid date formats, ensure that your JSON files contain date strings in a recognizable format.
No Files Found: If the script reports that no files were found, verify that the file filter matches the filenames in the input folder.
Permission Issues: If the script cannot read or write files, check the permissions of the input and output directories.
Contributing
If you wish to contribute to the script or report issues, please feel free to submit pull requests or open issues on the repository where this script is hosted.

License
This script is provided as-is without any warranty. Use it at your own risk. The author is not responsible for any damage or data loss resulting from its use.
