#!/usr/bin/python3
import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# TODO: verify these paths exist, print nice error if they don't
CTYPESGEN_PATH = os.path.join(SCRIPT_DIR, "deps", "ctypesgen")

sys.path.insert(0, CTYPESGEN_PATH)

import ctypesgen

def parseHeader(header_filename):
    print("{}".format(header_filename))
    header = CppHeaderParser.CppHeader(header_filename)
    print("  {} includes:".format(len(header.includes)))
    for incl in header.includes:
        print("   {}".format(incl))
    print("  {} #defines:".format(len(header.defines)))
    for define in header.defines:
        print("   {}".format(define))
    print("  {} functions:".format(len(header.functions)))
    for func in header.functions:
        print("   {}".format(func["name"]))

def parseHeadersIn(dir, exclude):
    for entry_basename in os.listdir(dir):
        if entry_basename.endswith(".idl") or entry_basename.endswith(".mof"):
            continue
        if entry_basename in exclude:
            print("skipping '{}'".format(exclude))
            continue
        entry = os.path.join(dir, entry_basename)
        if os.path.isdir(entry):
            parseHeadersIn(entry, exclude)
        else:
            try:
                parseHeader(entry)
            except CppHeaderParser.CppParseError as e:
                print("PARSEERROR: {}".format(entry_basename))
            except RecursionError as re:
                print("PARSEERROR: {}".format(entry_basename))

class JsonGenerator:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.include_dirs = []
        self.include_map = {}

    def findInclude(self, include):
        # TODO: instead of just accepting the first match, should we support an option to
        #       find all matches and error if there are multiple matches?
        for dir in self.include_dirs:
            filename = os.path.join(dir, include)
            if os.path.exists(filename):
                return filename
                return filename

        print("Error: failed to find include '{}' in the following dirs:".format(include))
        for dir in self.include_dirs:
            print("  {}".format(dir))
        sys.exit(1)

    def generate(self, include):
        if include in self.include_map:
            # already generated
            return False

        filename = self.findInclude(include)
        self.include_map = filename

        with open(filename, "r") as file:
            preprocessor = CustomPreprocessor()
            for dir in self.include_dirs:
                preprocessor.add_path(dir)
            preprocessor.parse(file)
        preprocessed_file = os.path.join(self.out_dir, include + ".preprocessed")
        #with open(preprocessed_file, "w") as file:
        #    preprocessor.write(file)

        use_python_preprocessor = True
        if use_python_preprocessor:
            ast = pycparser.parse_file(preprocessed_file)
        else:
            ast = pycparser.parse_file(preprocessed_file, use_cpp=True, cpp_path="clang", cpp_args=["-E"])

        with open(os.path.join(self.out_dir, include + ".json"), "w") as out_file:
            out_file.write("{}\n".format(ast))
            #out_file.write("{}\n".format(vars(ast)))
        #    #out_file.write('{\n')
        #    #out_file.write('  "includes": [')
        #    #prefix = ""
        #    #for incl in header.includes:
        #    #    out_file.write('{}\n    "{}"'.format(prefix, incl))
        #    #    prefix = ","
        #    #out_file.write(']\n')
        #    #out_file.write("{}\n".format(vars(header)))
        #    #for define in header.defines:
        #    #    out_file.write("   {}\n".format(define))
        #    #for func in header.functions:
        #    #    out_file.write("   {}\n".format(func["name"]))
        #    out_file.write('}\n')
        return True


def main():

    # just hardcode path to get started
    windows_include_path = "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.17763.0"
    if not os.path.exists(windows_include_path):
        sys.exit("Error: windows sdk include path does not exist: {}".format(windows_include_path))

    #
    # Header Directories
    #
    # shared - seems to mostly be headers shared between user mode and kernel mode
    # um - user mode? the standard user mode windows headers (like windows.h)
    # km - kernel mode?
    # winrt - windows rt api (windows store)
    process_shared_headers = False
    process_user_mode_headers = False

    shared_path = os.path.join(windows_include_path, "shared")
    user_mode_path = os.path.join(windows_include_path, "um")

    if process_shared_headers:
        if not os.path.exists(shared_path):
            sys.exit("Error: windows include dir is missing the 'shared' subdirectory: {}".format(shared_path))
        parseHeadersIn(shared_path, ["apdevpkey.h", "clfs.h", "devpkey.h", "devpropdef.h", "hidclass.h", "ifdef.h",
            "ksmedia.h", "ksproxy.h", "ktmtypes.h", "kxarm.h", "kxarmunw.h", "kxarm64.h", "kxarm64unw.h",
            "mstcpip.h", "netiodef.h", "nfpdev.h", "ntdddisk.h","ntddndis.h","ntddser.h","ntddstor.h", "ntddcdvd.h",
            "pciprop.h","poclass.h", "rpcdce.h", "scsi.h", "sensorsdef.h", "specstrings.h", "srb.h", "tdi.h", "TraceLoggingProvider.h",
            "winbio_types.h", "windot11.h", "winbio_ioct.h", "winsmcrd.h", "ws2def.h",
        ])

    if process_user_mode_headers:
        if not os.path.exists(user_mode_path):
            sys.exit("Error: windows include dir is missing the 'um' subdirectory: {}".format(user_mode_path))
        parseHeadersIn(user_mode_path, ["advpub.h", "anchorsyncdeviceservice.h", "atlthunk.h",
            "Audioclient.h", "audioenginebaseapo.h","AudioEngineEndpoint.h","aviriff.h",
            "bridgedeviceservice.h","bthledef.h","calendardeviceservice.h","CallConv.Inc",
            "coguid.h","commdlg.h","contactdeviceservice.h","cper.h","cryptxml.h",
            "d2d1.h","d2d1_1.h","d3dcsx.h","dbdaoid.h","ddraw.h","devfiltertypes.h",
            "deviceservices.h","devquerydef.h","DirectXCollision.h","DirectXPackedVector.h",
            "DsGetDC.h","EapAuthenticatorActionDefine.h","eaptypes.h","ehstorextensions.h",
            "eventman.xsd","fullenumsyncdeviceservice.h","functiondiscoverykeys.h",
            "functiondiscoverykeys_devpkey.h","GLU.h","http.h",
            "icu.h","icucommon.h","icui18n.h","LMaccess.h","LMDFS.h","LMServer.h","lmstats.h",
            "medparam.h","memoryapi.h","messagedeviceservice.h","metadatadeviceservice.h",
            "mmdeviceapi.h","mmiscapi.h", "MspAddr.h",
        ])

    out_dir = os.path.join(SCRIPT_DIR, "out")
    #if os.path.exists(out_dir):
    #    print("rmtree {}".format(out_dir))
    #    shutil.rmtree(out_dir)
    #print("mkdir {}".format(out_dir))
    #os.mkdir(out_dir)
    generator = JsonGenerator(out_dir)
    generator.include_dirs.append(shared_path)
    generator.include_dirs.append(user_mode_path)

    generator.generate("windows.h")

main()
