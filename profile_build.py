import re
import argparse
import ipdb
import pandas


class DataFrameable:

    @staticmethod
    def create_dataframe(rows, columns):

        dict_of_rows = {key: [] for key in columns}

        for row in rows:
            row_columns = row.rows()
            for index in range(0, len(columns)):
                row_array = dict_of_rows.get(columns[index], [])
                row_array.append(row_columns[index])

        build_frame = pandas.DataFrame(dict_of_rows)

        return build_frame

class FileCompileInfo():

    def __init__(self, duration, filename):

        self.duration = float(duration)
        self.filename = filename
    
    @classmethod
    def columns(cls):
        return ["duration", "filename"]

    def rows(self):

        return [self.duration,
                self.filename]

class TimeInfo():

    def __init__(self):

        self.start_time = ""
        self.end_time = ""
        self.target = None
        self.project = None

    def duration_in_seconds(self):
        if len(self.start_time) > 0 and len(self.end_time) > 0:
            return long(self.end_time) - long(self.start_time)
        return -1

    @classmethod
    def columns(cls):
        return ['start_time', 
        'end_time',
        'duration',
        'target',
        'project']

    def rows(self):

        return [self.start_time, 
            self.end_time, 
            self.duration_in_seconds(), 
            self.target,
            self.project]

def main():
    parser = argparse.ArgumentParser(description="profile build output")
    parser.add_argument(dest="filename", help="filename of build output to profile")
    parser.add_argument("--output", required=True, dest="output_file", help="name of output file, in csv format")

    args = parser.parse_args()

    filename = args.filename
    output_file = open(args.filename, "r")

    target_build_profile = target_build_time_profile(output_file) 
    summarize_target_time_info(target_build_profile)

    swift_build_times = gather_swift_build_times_from_file(output_file)
    summarize_swift_build_times(swift_build_times)

def target_build_time_profile(build_output_fp):

    time_rx = re.compile("^([0-9]*):.*BUILD TARGET (.*) OF PROJECT (\w*) .*$")
    build_finished_rx = re.compile("^([0-9]*):.*(BUILD SUCCEEDED).*")

    time_infos = []

    for line in build_output_fp.readlines():

        match = time_rx.match(line)
        end_match = build_finished_rx.match(line)

        if match:

            match_groups = match.groups()
            time, target, project = match_groups

            time_info = TimeInfo()
            time_info.start_time = time
            time_info.target = target
            time_info.project = project

            if len(time_infos) > 0:
                last_time = time_infos[-1]
                last_time.end_time = time

            time_infos.append(time_info)

        if end_match:

            match_groups = end_match.groups()
            time, _ = match_groups
            if len(time_infos) > 0:
                last_time = time_infos[-1]
                last_time.end_time = time

    build_output_fp.seek(0)
    return time_infos 


def gather_swift_build_times_from_file(build_output_fp):

    file_rx = re.compile("^[0-9]*:\s*([\d*\.]*)ms\s[\w*\/\.-]*\/(\w*\.swift).*")

    compile_times = []

    for line in build_output_fp.readlines():

        match = file_rx.match(line)

        if match:

            time, filename = match.groups()

            info = FileCompileInfo(time, filename)
            compile_times.append(info)

    build_output_fp.seek(0)
    return compile_times

def summarize_swift_build_times(build_times):

    build_index = FileCompileInfo.columns()
    build_frame = DataFrameable.create_dataframe(build_times, build_index)

    grouped = build_frame.groupby("filename")
    total_swift_compile = build_frame["duration"].sum()
    a_sum = grouped["duration"].sum()
    a_sum.sort("duration")
    top_ten = a_sum[-10:]
    print """\n\nTotal swift compile time: {0}\nTop ten culprits taking total of {1} ms: {2}""".format(total_swift_compile, top_ten.sum(), top_ten)

def summarize_target_time_info(time_infos):

    index = TimeInfo.columns()
    data_frame = DataFrameable.create_dataframe(time_infos, index)

    grouped = data_frame.groupby("project")
    
    print "Total: {0}\n".format(data_frame["duration"].sum())
    print grouped["duration"].sum()


if __name__ == '__main__':
    main()

