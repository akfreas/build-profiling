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

class MatchableTimeInfo():

    @classmethod
    def build_from_line(cls, line):

        match = cls.regex.match(line)

        if match:
            groups = match.groups()
            return cls(*groups)

        else:
            return None

class ClangCompileInfo(MatchableTimeInfo):

    regex = re.compile("^([0-9]*):.*CompileC.*\/([\w]*\.build).*\/([\+\w\_]*\.m)")
    columns = ["duration", "filename", "product"]

    def __init__(self, start_time, product, filename, end_time=None):

        self.start_time = start_time
        self.product = product
        self.filename = filename
        self.end_time = end_time

    def duration_in_seconds(self):
        if len(self.start_time) > 0 and len(self.end_time) > 0:
            return long(self.end_time) - long(self.start_time)
        return None

    def rows(self):
        return [self.duration_in_seconds(), self.filename, self.product]


class SwiftCompileInfo(MatchableTimeInfo):

    regex = re.compile("^[0-9]*:\s*([\d*\.]*)ms\s[\w*\/\.-]*\/(\w*\.swift).*")
    columns = ["duration", "filename"]

    def __init__(self, duration, filename):

        self.duration = float(duration)
        self.filename = filename

    def rows(self):

        return [self.duration,
                self.filename]

class TargetTimeInfo():

    regex = re.compile("^[0-9]*:\s*([\d*\.]*)ms\s[\w*\/\.-]*\/(\w*\.swift).*")

    def __init__(self):

        self.start_time = ""
        self.end_time = ""
        self.target = None
        self.project = None

    def duration_in_seconds(self):
        if len(self.start_time) > 0 and len(self.end_time) > 0:
            return long(self.end_time) - long(self.start_time)
        return None

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

    swift_build_times = extract_swift_build_times_from_file(output_file)
    summarize_swift_build_times(swift_build_times)

    clang_build_times = extract_clang_build_times(output_file)
    summarize_clang_build_times(clang_build_times)

def target_build_time_profile(build_output_fp):

    build_output_fp.seek(0)
    time_rx = re.compile("^([0-9]*):.*BUILD TARGET (.*) OF PROJECT (\w*) .*$")
    build_finished_rx = re.compile("^([0-9]*):.*(BUILD SUCCEEDED).*")

    time_infos = []

    for line in build_output_fp.readlines():

        match = time_rx.match(line)
        end_match = build_finished_rx.match(line)

        if match:

            match_groups = match.groups()
            time, target, project = match_groups

            time_info = TargetTimeInfo()
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

    return time_infos 


def extract_swift_build_times_from_file(build_output_fp):

    build_output_fp.seek(0)
    compile_times = []

    for line in build_output_fp.readlines():

        info = SwiftCompileInfo.build_from_line(line)
        if info:
            compile_times.append(info)

    return compile_times

def summarize_swift_build_times(build_times):

    build_index = SwiftCompileInfo.columns
    build_frame = DataFrameable.create_dataframe(build_times, build_index)

    grouped = build_frame.groupby("filename")
    build_frame.duration = pandas.to_timedelta(build_frame.duration, unit='ms')
    a_sum = build_frame.duration.sum()
    sorted_group = grouped.sum().sort_values(by="duration")
    top_ten = sorted_group[-10:]
    top_ten_sum = top_ten.sum()
    print """\n\nTotal swift compile time: {0}\nTop ten culprits taking total of {1}: {2}""".format(a_sum, top_ten_sum, top_ten)

def summarize_target_time_info(time_infos):

    index = TargetTimeInfo.columns()
    data_frame = DataFrameable.create_dataframe(time_infos, index)

    data_frame['duration'] = pandas.to_timedelta(data_frame['duration'], unit='s')
    grouped = data_frame.groupby("project")

    seconds = data_frame["duration"].sum()


    print "Total: {0}\n".format(seconds)
    print grouped["duration"].sum()


def extract_clang_build_times(build_output_fp):

    build_output_fp.seek(0)
    compile_times = []
    last_time = None
    for line in build_output_fp.readlines():

        info = ClangCompileInfo.build_from_line(line)
        
        if info:
            compile_times.append(info)
            if last_time:
                last_time.end_time = info.start_time
            last_time = info

    last_time.end_time = last_time.start_time
    
    return compile_times

def summarize_clang_build_times(build_times):

    df = DataFrameable.create_dataframe(build_times, ClangCompileInfo.columns) 
    slow_files = df[(df.duration > 0)]
    slow_files.sort_values(by='duration')

    top_slow_products = slow_files.groupby('product').sum().sort_values(by='duration', ascending=False)
     
    print top_slow_products
    ipdb.set_trace()


   


if __name__ == '__main__':
    main()

