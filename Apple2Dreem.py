import sys
import os
import argparse
import json
import math
from datetime import datetime, timedelta, time
from typing import List
from dateutil import parser as date_parser
from dateutil import tz
import glob

class SleepSegment:
    def __init__(self, start: datetime, stage: str):
        self.Start = start
        self.Stage = stage

class SleepEntry:
    def __init__(self, source: str, qty: float, start_date: datetime, value: str, end_date: datetime):
        self.Source = source
        self.Qty = qty
        self.StartDate = start_date
        self.Value = value
        self.EndDate = end_date

class OutputData:
    def __init__(self):
        self.Type = ''
        self.StartTime = ''
        self.StopTime = ''
        self.SleepDuration = ''
        self.SleepOnsetDuration = ''
        self.LightSleepDuration = ''
        self.DeepSleepDuration = ''
        self.REMDuration = ''
        self.WakeAfterSleepOnsetDuration = ''
        self.NumberOfAwakenings = 0
        self.PositionChanges = 0
        self.MeanHeartRate = 0
        self.MeanRespirationCPM = 0
        self.NumberOfStimulations = 0
        self.SleepEfficiency = 0
        self.Hypnogram = ''

def parse_iso8601(date_string: str) -> datetime:
    try:
        return date_parser.parse(date_string)
    except (ValueError, TypeError):
        print(f"Warning: Invalid date format '{date_string}'. Using current date and time.")
        return datetime.now(tz=tz.tzlocal())

def create_30s_segments(start_time: datetime, end_time: datetime) -> List[SleepSegment]:
    segments = []
    current_time = start_time
    while current_time < end_time:
        segments.append(SleepSegment(start=current_time, stage='WAKE'))
        current_time += timedelta(seconds=30)
    return segments

def map_sleep_stage(stage: str) -> str:
    mapping = {
        "Core": "Light",
        "Asleep": "Asleep",
        "Deep": "Deep",
        "REM": "REM",
        "Awake": "WAKE",
        "InBed": "WAKE"
    }
    return mapping.get(stage, "WAKE")

def update_segments_with_sleep_data(segments: List[SleepSegment], sleep_data: List[SleepEntry]):
    for entry in sleep_data:
        start = entry.StartDate
        end = entry.EndDate
        stage = map_sleep_stage(entry.Value)

        for segment in segments:
            if start <= segment.Start <= end and segment.Stage == "WAKE":
                segment.Stage = stage

def calculate_duration(start: datetime, end: datetime) -> str:
    duration = end - start
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"

def parse_duration_string(duration_str: str) -> timedelta:
    hours, minutes, seconds = map(int, duration_str.split(':'))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"

def apply_time_shift(date_time: datetime, shift_seconds: int) -> datetime:
    return date_time + timedelta(seconds=shift_seconds)

def process_health_data(sleep_data: List[SleepEntry], output_file: str, from_date: datetime, to_date: datetime, time_shift_seconds: int):
    sleep_data = sorted(sleep_data, key=lambda entry: entry.StartDate)
    # Apply time shift
    for entry in sleep_data:
        entry.StartDate = apply_time_shift(entry.StartDate, time_shift_seconds)
        entry.EndDate = apply_time_shift(entry.EndDate, time_shift_seconds)

    start_time = sleep_data[0].StartDate
    end_time = max(entry.EndDate for entry in sleep_data)

    print(f"Start Time: {start_time}")  # Debug output
    print(f"End Time: {end_time}")      # Debug output

    segments = create_30s_segments(start_time, end_time)
    update_segments_with_sleep_data(segments, sleep_data)

    total_duration = calculate_duration(start_time, end_time)

    sleep_onset_segment = next((segment for segment in segments if segment.Stage != "WAKE"), segments[0])
    sleep_onset_duration = calculate_duration(start_time, sleep_onset_segment.Start)

    stage_durations = {
        "Asleep": timedelta(0),
        "Light": timedelta(0),
        "Deep": timedelta(0),
        "REM": timedelta(0),
        "WAKE": timedelta(0)
    }

    for segment in segments:
        stage_durations[segment.Stage] += timedelta(seconds=30)

    wake_after_sleep_onset = stage_durations["WAKE"] - parse_duration_string(sleep_onset_duration)

    num_awakenings = sum(
        1 for a, b in zip(segments, segments[1:])
        if a.Stage != "WAKE" and b.Stage == "WAKE"
    )

    hypnogram = ",".join(segment.Stage for segment in segments)

    output_data = OutputData()
    output_data.Type = "night"
    output_data.StartTime = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    output_data.StopTime = end_time.strftime("%Y-%m-%dT%H:%M:%S")
    output_data.SleepDuration = total_duration
    output_data.SleepOnsetDuration = sleep_onset_duration
    output_data.LightSleepDuration = format_timedelta(stage_durations["Light"])
    output_data.DeepSleepDuration = format_timedelta(stage_durations["Deep"])
    output_data.REMDuration = format_timedelta(stage_durations["REM"])
    output_data.WakeAfterSleepOnsetDuration = format_timedelta(wake_after_sleep_onset)
    output_data.NumberOfAwakenings = num_awakenings
    output_data.PositionChanges = 0
    output_data.MeanHeartRate = 0
    output_data.MeanRespirationCPM = 0
    output_data.NumberOfStimulations = 0
    output_data.SleepEfficiency = 0
    output_data.Hypnogram = f"[{hypnogram}]"

    header = "Type;Start Time;Stop Time;Sleep Duration;Sleep Onset Duration;Light Sleep Duration;Deep Sleep Duration;REM Duration;Wake After Sleep Onset Duration;Number of awakenings;Position Changes;Mean Heart Rate;Mean Respiration CPM;Number of Stimulations;Sleep efficiency;Hypnogram"

    data_row = f"{output_data.Type};{output_data.StartTime};{output_data.StopTime};{output_data.SleepDuration};{output_data.SleepOnsetDuration};{output_data.LightSleepDuration};{output_data.DeepSleepDuration};{output_data.REMDuration};{output_data.WakeAfterSleepOnsetDuration};{output_data.NumberOfAwakenings};{output_data.PositionChanges};{output_data.MeanHeartRate};{output_data.MeanRespirationCPM};{output_data.NumberOfStimulations};{output_data.SleepEfficiency};{output_data.Hypnogram}"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        f.write(data_row)

def validate_sleep_data(sleep_data: List[SleepEntry], file_name: str) -> bool:
    if not sleep_data:
        print(f"Warning: No sleep entries found in file {file_name}.")
        return False

    is_valid = True
    for entry in sleep_data:
        if not entry.StartDate or not entry.EndDate:
            print(f"Warning: Invalid sleep entry found in file {file_name}. Start or end date is missing.")
            is_valid = False

        if not entry.Value:
            print(f"Warning: Invalid sleep entry found in file {file_name}. Sleep stage value is missing.")
            is_valid = False

        if not isinstance(entry.Qty, (int, float)) or math.isnan(entry.Qty) or math.isinf(entry.Qty):
            print(f"Warning: Invalid sleep entry found in file {file_name}. Invalid quantity value.")
            is_valid = False

        if not entry.Source:
            print(f"Warning: Invalid sleep entry found in file {file_name}. Source is missing.")
            is_valid = False

    return is_valid

def get_unique_file_name(file_name: str) -> str:
    if not os.path.exists(file_name):
        return file_name

    file_name_only, extension = os.path.splitext(os.path.basename(file_name))
    path = os.path.dirname(file_name)
    count = 1
    new_full_path = file_name

    while os.path.exists(new_full_path):
        temp_file_name = f"{file_name_only}_{count}"
        new_full_path = os.path.join(path, temp_file_name + extension)
        count += 1

    return new_full_path

def parse_datetime(input_str: str) -> datetime:
    if not input_str:
        return None
    try:
        dt = date_parser.parse(input_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.tzlocal())
        return dt
    except ValueError:
        print(f"Invalid date format: {input_str}.")
        return None

def process_file(input_file: str, output_folder: str, from_date: datetime, to_date: datetime, time_shift_seconds: int):
    print(f"Processing file: {input_file}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            json_string = f.read()
    except Exception as ex:
        print(f"Warning: Unable to read file {input_file}. Error: {ex}")
        return

    try:
        health_data_dict = json.loads(json_string)
    except json.JSONDecodeError as ex:
        print(f"Warning: Invalid JSON in file {input_file}. Error: {ex}")
        return

    if 'data' not in health_data_dict or 'metrics' not in health_data_dict['data']:
        print(f"Warning: The file {input_file} does not contain valid health data.")
        return

    metrics_list = health_data_dict['data']['metrics']
    if not metrics_list or 'data' not in metrics_list[0]:
        print(f"Warning: No sleep data found in file {input_file}.")
        return

    sleep_data_list = metrics_list[0]['data']

    sleep_entries = []
    for entry in sleep_data_list:
        sleep_entry = SleepEntry(
            source=entry.get('source', ''),
            qty=entry.get('qty', 0),
            start_date=parse_iso8601(entry.get('startDate', '')),
            value=entry.get('value', ''),
            end_date=parse_iso8601(entry.get('endDate', ''))
        )
        sleep_entries.append(sleep_entry)

    if not validate_sleep_data(sleep_entries, input_file):
        return

    all_sleep_data = sorted(sleep_entries, key=lambda x: x.StartDate)

    # Define start_time and end_time as datetime.time objects
    start_time = time(hour=19, minute=0, second=0)
    end_time = time(hour=11, minute=0, second=0)

    grouped_sleep_data = []
    current_night_start = None
    current_night_entries = []

    for entry in all_sleep_data:
        start_dt = entry.StartDate
        end_dt = entry.EndDate

        # Determine the night date
        if start_dt.time() >= start_time:
            night_date = start_dt.date()
        else:
            night_date = (start_dt - timedelta(days=1)).date()

        # Calculate night_start_dt and night_end_dt
        night_start_dt = datetime.combine(night_date, start_time, tzinfo=start_dt.tzinfo)
        night_end_dt = datetime.combine(night_date + timedelta(days=1), end_time, tzinfo=start_dt.tzinfo)

        # Filter entries within the night and date range
        if (start_dt >= night_start_dt and end_dt <= night_end_dt and
            start_dt >= from_date and end_dt <= to_date):
            if current_night_start != night_date:
                if current_night_entries:
                    grouped_sleep_data.append((current_night_start, current_night_entries))
                current_night_start = night_date
                current_night_entries = []
            current_night_entries.append(entry)

    if current_night_entries:
        grouped_sleep_data.append((current_night_start, current_night_entries))

    for night_date, entries in grouped_sleep_data:
        segment_start_date = min(entry.StartDate for entry in entries)
        segment_end_date = max(entry.EndDate for entry in entries)

        output_file = os.path.join(output_folder,
            f"Apple2Dreem_{night_date.strftime('%Y-%m-%d')}_{segment_start_date.strftime('%H-%M')}_{segment_end_date.strftime('%H-%M')}.csv")
        process_health_data(entries, output_file, segment_start_date, segment_end_date, time_shift_seconds)
        print(f"Processed data for night of {night_date.strftime('%Y-%m-%d')} from {segment_start_date.strftime('%H:%M')} to {segment_end_date.strftime('%H:%M')}. Output saved to {output_file}")

    try:
        new_file_name = get_unique_file_name(os.path.join(os.path.dirname(input_file), "_" + os.path.basename(input_file)))
        os.rename(input_file, new_file_name)
        print(f"Renamed {input_file} to {new_file_name}")
    except Exception as ex:
        print(f"Warning: Unable to rename processed file {input_file}. Error: {ex}")

def main():
    parser = argparse.ArgumentParser(description='AppleWatch2Dreem')

    parser.add_argument('-i', '--input', help='Specify input folder (default: current directory)', default='.')
    parser.add_argument('-o', '--output', help='Specify output folder (default: same as input folder)')
    parser.add_argument('-f', '--from', dest='from_date', help='Specify start date (format: yyyy-MM-dd or yyyy-MM-dd-HH:mm)')
    parser.add_argument('-t', '--to', dest='to_date', help='Specify end date (format: yyyy-MM-dd or yyyy-MM-dd-HH:mm)')
    parser.add_argument('-l', '--filter', help='Specify input file filter (default: HealthAutoExport-*.json)', default='HealthAutoExport-*.json')
    parser.add_argument('-s', '--shift', type=int, help='Specify time shift in seconds (positive or negative)', default=0)

    args = parser.parse_args()

    input_folder = args.input
    output_folder = args.output
    file_filter = args.filter
    from_date = parse_datetime(args.from_date)
    to_date = parse_datetime(args.to_date)
    time_shift_seconds = args.shift

    if not output_folder:
        output_folder = input_folder

    # Set default from_date and to_date with timezone
    if not from_date:
        from_date = datetime.now(tz=tz.tzlocal()).replace(hour=19, minute=0, second=0, microsecond=0) - timedelta(days=1)
    elif from_date.time() == time(0, 0, 0):
        from_date = from_date.replace(hour=19, minute=0, second=0, microsecond=0)
    if from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=tz.tzlocal())

    if not to_date:
        to_date = datetime.now(tz=tz.tzlocal()).replace(hour=11, minute=0, second=0, microsecond=0)
    elif to_date.time() == time(0, 0, 0):
        to_date = to_date.replace(hour=11, minute=0, second=0, microsecond=0)
    if to_date.tzinfo is None:
        to_date = to_date.replace(tzinfo=tz.tzlocal())

    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"File filter: {file_filter}")
    print(f"From date: {from_date}")
    print(f"To date: {to_date}")
    print(f"Time shift: {time_shift_seconds} seconds")

    if not os.path.exists(input_folder):
        print(f"Error: Input folder '{input_folder}' does not exist.")
        return

    os.makedirs(output_folder, exist_ok=True)

    files = glob.glob(os.path.join(input_folder, file_filter))
    if len(files) == 0:
        print(f"No files found matching the filter '{file_filter}' in the input folder.")
        return

    processed_files = 0
    failed_files = 0

    for file in files:
        try:
            process_file(file, output_folder, from_date, to_date, time_shift_seconds)
            processed_files += 1
        except Exception as ex:
            print(f"Warning: Failed to process file {file}. Error: {ex}")
            failed_files += 1

    print(f"Processing complete. Processed files: {processed_files}, Failed files: {failed_files}")

if __name__ == "__main__":
    main()
