import re
import argparse
import ipdb
import pandas


class FileCompileInfo:

    def __init__(self, duration, filename):

        self.duration = float(duration)
        self.filename = filename
    
    @classmethod
    def csv_columns(cls):
        return ",".join(["duration", "filename"])

    def csv_summary(self):

        return ",".join([
            str(self.duration),
            self.filename
        ])

class TimeInfo:

    def __init__(self):

        self.start_time = ""
        self.end_time = ""
        self.target = None
        self.project = None

    def duration_in_seconds(self):
        if len(self.start_time) > 0 and len(self.end_time) > 0:
            return long(self.end_time) - long(self.start_time)
        return -1

    def csv_summary(self):

        return ",".join([self.start_time, 
            self.end_time, 
            str(self.duration_in_seconds()), 
            self.target,
            self.project])

def main():

    parser = argparse.ArgumentParser(description="profile build output")
    parser.add_argument(dest="filename", help="filename of build output to profile")
    parser.add_argument("--output", required=True, dest="output_file", help="name of output file, in csv format")

    args = parser.parse_args()

    filename = args.filename
    output_file = args.output_file


    time_rx = re.compile("^([0-9]*):.*BUILD TARGET (.*) OF PROJECT (\w*) .*$")
    build_finished_rx = re.compile("^([0-9]*):.*(BUILD SUCCEEDED).*")

    build_output = open(filename, "r")

    time_infos = []

    for line in build_output.readlines():

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



    build_output.close()

    output = file(args.output_file, "w")

    output.write(",".join(["start_time", "end_time", "duration_in_seconds", "target", "project"]) + "\n")
    for time in time_infos:
        output.write(time.csv_summary() + "\n")
    output.close()

    summarize_output(output_file)

def summarize_output(filename):

    pda = pandas.read_csv(filename)

    grouped = pda.groupby("project")
    
    print "Total: {0}\n".format(pda["duration_in_seconds"].sum())
    print grouped["duration_in_seconds"].sum()

def gather_build_times_from_file(build_output_filename, matching_data):


    file_rx = re.compile("^[0-9]*:\s*([\d*\.]*)ms\s[\w*\/\.-]*\/(\w*\.swift).*")

    build_output = open(build_output_filename, "r")

    comp_times = []

    for line in build_output.readlines():

        match = file_rx.match(line)

        if match:

            time, filename = match.groups()

            info = FileCompileInfo(time, filename)
            comp_times.append(info)

    matching_file = open(matching_data, "w")

    matching_file.write(FileCompileInfo.csv_columns()+"\n")

    for comp_info in comp_times:

        matching_file.write(comp_info.csv_summary()+"\n")

    matching_file.close()

def summarize_build_times(matching_data):

    pda = pandas.read_csv(matching_data)

    grouped = pda.groupby("filename")
    total_swift_compile = pda["duration"].sum()
    a_sum = grouped["duration"].sum()
    a_sum.sort("duration")
    top_ten = a_sum[-10:]
    print """\n\nTotal swift compile time: {0}\nTop ten culprits taking total of {1} ms: {2}""".format(total_swift_compile, top_ten.sum(), top_ten)

if __name__ == '__main__':
    summary = "compile_summary.csv"
    gather_build_times_from_file("build_output.txt", summary)
    summarize_build_times(summary)
    #main()




